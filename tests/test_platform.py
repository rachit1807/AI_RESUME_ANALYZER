from io import BytesIO

from werkzeug.security import check_password_hash

from conftest import register
from models import (Analysis, Application, Company, Job, ResumeRankingBatch, ResumeVersion,
                    User, db)


def test_public_analyzer_pages_and_upload_validation(client, resume_pdf):
    home = client.get("/")
    assert home.status_code == 200
    assert b"Know where your resume stands" in home.data
    invalid = client.post("/upload", data={"resume": (BytesIO(b"not a pdf"), "bad.pdf"), "job_description": "Role description"}, follow_redirects=True)
    assert invalid.status_code == 200
    assert b"not a valid PDF" in invalid.data
    result = client.post("/upload", data={"resume": (BytesIO(resume_pdf), "resume.pdf"),
                    "job_description": "Python Flask SQL React API engineer role"}, follow_redirects=True)
    assert result.status_code == 200
    assert b"ATS-STYLE COMPLETENESS" in result.data
    assert b"react" in result.data
    assert client.get("/health").json["status"] == "ok"


def test_candidate_tools_and_resume_version_history(client, app, resume_pdf, monkeypatch):
    register(client, "candidate@example.com")
    response = client.post("/upload", data={"resume": (BytesIO(resume_pdf), "resume.pdf"),
                    "job_description": "Python Flask SQL React engineer"}, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        version = ResumeVersion.query.one()
        report = Analysis.query.one()
        version_id, report_id = version.id, report.id
    assert client.get("/dashboard").status_code == 200
    assert client.get(f"/resume/history/{version_id}").status_code == 200
    assert client.get(f"/analysis/{report_id}/pdf").data.startswith(b"%PDF-")
    builder = client.post("/builder", data={"name": "Casey Dev", "contact": "casey@example.com",
        "summary": "Backend developer", "skills": "Python SQL", "experience": "Built APIs",
        "projects": "Hiring tool", "education": "BSc Computing", "template": "modern"}, follow_redirects=True)
    assert builder.status_code == 200 and b"Casey Dev" in builder.data
    with app.app_context():
        builder_version = ResumeVersion.query.filter_by(filename="resume-builder.txt").one()
        builder_id = builder_version.id
    pdf = client.get(f"/builder/{builder_id}/pdf")
    assert pdf.status_code == 200 and pdf.data.startswith(b"%PDF-")
    rewritten = client.post("/rewrite", data={"resume_text": "worked on Python project"})
    assert b"Contributed to Python project" in rewritten.data
    letter = client.post("/cover-letter", data={"job_title": "Backend Engineer", "company": "Acme", "job_description": "Python SQL"}, follow_redirects=True)
    assert letter.status_code == 200 and b"Acme" in letter.data
    with app.app_context():
        from models import CoverLetter
        cover_id = CoverLetter.query.one().id
    assert client.get(f"/cover-letter/{cover_id}/pdf").data.startswith(b"%PDF-")
    assert client.post("/learning", data={"job_description": "Python React Docker"}).status_code == 200
    assert client.post("/roadmap", data={"role": "React engineer", "skills": "Python"}).status_code == 200
    assert client.post("/linkedin", data={"resume_text": "Python Flask"}).status_code == 200
    assert client.post("/compare", data={"job_descriptions": "Acme · Engineer\nPython SQL\n---\nOrbit · Developer\nReact Docker"}).status_code == 200
    assert client.post("/interview/questions", data={"role": "Engineer", "skills": "Python", "projects": "Hiring tool"}).status_code == 200
    mock = client.post("/interview/mock", data={"role": "Engineer", "answer": "I built a Python API with a team. The project improved the result for users."})
    assert mock.status_code == 200 and b"PRACTICE SCORE" in mock.data
    sent_messages = []
    class FakeSMTP:
        def __init__(self, *_args, **_kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *_args): pass
        def starttls(self): pass
        def login(self, *_args): pass
        def send_message(self, message): sent_messages.append(message)
    monkeypatch.setattr("reporting.smtplib.SMTP", FakeSMTP)
    app.config.update(MAIL_HOST="smtp.example.test", MAIL_FROM="reports@example.test",
                      MAIL_USERNAME="test-user", MAIL_PASSWORD="test-password")
    email = client.post(f"/analysis/{report_id}/email", data={"email": "candidate@example.com"}, follow_redirects=True)
    assert email.status_code == 200
    resume_email = client.post(f"/resume/{builder_id}/email", data={"email": "candidate@example.com"}, follow_redirects=True)
    assert resume_email.status_code == 200
    letter_email = client.post(f"/cover-letter/{cover_id}/email", data={"email": "candidate@example.com"}, follow_redirects=True)
    assert letter_email.status_code == 200 and len(sent_messages) == 3
    assert all(message.get_content_maintype() == "multipart" for message in sent_messages)
    delete = client.post(f"/resume/{version_id}/delete", follow_redirects=True)
    assert delete.status_code == 200
    with app.app_context():
        assert db.session.get(ResumeVersion, version_id) is None
        assert Analysis.query.filter_by(id=report_id).first() is None


def test_recruiter_company_jobs_applicants_and_resume_ranking(client, app, resume_pdf):
    register(client, "candidate2@example.com")
    client.post("/upload", data={"resume": (BytesIO(resume_pdf), "candidate.pdf"),
                 "job_description": "Python Flask SQL React role"}, follow_redirects=True)
    recruiter_client = app.test_client()
    response = register(recruiter_client, "recruiter@example.com", "recruiter", "Orbit Labs")
    assert b"COMPANY PORTAL" in response.data
    created = recruiter_client.post("/recruiter/jobs", data={"title": "Backend Engineer", "location": "Remote",
            "salary_range": "Set by employer", "description": "Build and maintain Python APIs and database services with our distributed engineering team."}, follow_redirects=True)
    assert created.status_code == 200 and b"Backend Engineer" in created.data
    with app.app_context():
        job = Job.query.one()
        job_id = job.id
    assert client.get("/jobs").status_code == 200
    assert client.post(f"/jobs/{job_id}/save", follow_redirects=True).status_code == 200
    assert client.post(f"/jobs/{job_id}/apply", follow_redirects=True).status_code == 200
    applicants = recruiter_client.get(f"/recruiter/jobs/{job_id}/applicants")
    assert applicants.status_code == 200 and b"candidate2@example.com" in applicants.data
    with app.app_context():
        application_id = Application.query.one().id
    assert recruiter_client.post(f"/recruiter/applications/{application_id}/status", data={"status": "shortlisted"}, follow_redirects=True).status_code == 200
    assert b"shortlisted" in recruiter_client.get(f"/recruiter/jobs/{job_id}/applicants").data
    assert recruiter_client.get(f"/recruiter/jobs/{job_id}/report.csv").data.startswith(b"\xef\xbb\xbf")
    ranking = recruiter_client.post("/recruiter/rank", data={"job_title": "API Developer", "job_description": "Python Flask SQL React",
        "resumes": [(BytesIO(resume_pdf), "batch.pdf", "application/pdf")]}, content_type="multipart/form-data", follow_redirects=True)
    assert ranking.status_code == 200 and b"Candidate comparison" in ranking.data
    with app.app_context():
        batch = ResumeRankingBatch.query.one()
        batch_id = batch.id
    assert recruiter_client.get(f"/recruiter/rank/{batch_id}.csv").data.startswith(b"\xef\xbb\xbf")
    assert recruiter_client.post(f"/recruiter/jobs/{job_id}/status", follow_redirects=True).status_code == 200
    # Another recruiter cannot inspect this company's applicants.
    other = app.test_client()
    register(other, "other@example.com", "recruiter", "Other Company")
    assert other.get(f"/recruiter/jobs/{job_id}/applicants").status_code == 404


def test_admin_management_and_reports(client, app):
    with app.app_context():
        user = User(name="Platform Admin", email="admin@example.com", password_hash="", role="admin")
        candidate = User(name="Candidate Account", email="managed@example.com", password_hash="", role="candidate")
        from werkzeug.security import generate_password_hash
        user.password_hash = generate_password_hash("VeryStrongPassword123")
        candidate.password_hash = generate_password_hash("VeryStrongPassword123")
        recruiter = User(name="Company Recruiter", email="remove-company@example.com",
                         password_hash=generate_password_hash("VeryStrongPassword123"), role="recruiter")
        db.session.add(user)
        db.session.add(candidate)
        db.session.add(recruiter)
        db.session.commit()
        candidate_id = candidate.id
        company = Company(name="Disposable Company", owner_id=recruiter.id)
        db.session.add(company)
        db.session.flush()
        job = Job(company_id=company.id, title="Disposable role", description="This is a sufficiently long job description used in this account deletion test.")
        db.session.add(job)
        recruiter_id = recruiter.id
        db.session.commit()
    admin_client = app.test_client()
    assert admin_client.post("/login", data={"email": "admin@example.com", "password": "VeryStrongPassword123"}, follow_redirects=True).status_code == 200
    page = admin_client.get("/admin")
    assert page.status_code == 200 and b"PLATFORM ADMINISTRATION" in page.data
    with app.app_context():
        user = User.query.filter_by(email="admin@example.com").one()
        user_id = user.id
        assert check_password_hash(user.password_hash, "VeryStrongPassword123")
    assert admin_client.post(f"/admin/users/{candidate_id}/update", data={"role": "candidate", "active": "false"}, follow_redirects=True).status_code == 200
    assert admin_client.post(f"/admin/users/{recruiter_id}/delete", follow_redirects=True).status_code == 200
    assert admin_client.get("/admin/reports.csv").data.startswith(b"\xef\xbb\xbf")
    with app.app_context():
        assert Company.query.filter_by(name="Disposable Company").first() is None
        assert Job.query.filter_by(title="Disposable role").first() is None


def test_registration_role_controls_and_session_security(app, client):
    assert client.get("/register").status_code == 200
    assert client.post("/register", data={"name": "Bad", "email": "bad@example.com", "password": "short", "role": "admin"}, follow_redirects=True).status_code == 200
    body = register(client, "secure@example.com")
    assert body.status_code == 200
    assert client.get("/admin").status_code == 403
    from app import create_app
    csrf_app = create_app({"TESTING": True, "SECRET_KEY": "csrf-test", "SQLALCHEMY_DATABASE_URI": app.config["SQLALCHEMY_DATABASE_URI"],
                           "SESSION_COOKIE_SECURE": False, "WTF_CSRF_ENABLED": True})
    csrf_client = csrf_app.test_client()
    assert csrf_client.post("/login", data={"email": "nobody@example.com", "password": "x"}).status_code == 400
