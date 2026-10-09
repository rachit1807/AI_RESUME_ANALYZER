import json
import re
from io import BytesIO

from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, send_file, url_for
from werkzeug.utils import secure_filename

from models import Analysis, Application, AuditEvent, CandidateProfile, CoverLetter, InterviewSession, Job, ResumeVersion, SavedJob, User, db
from recruitment_services import (SKILL_RESOURCES, analyze_text, evaluate_answer, interview_questions,
                                  learning_recommendations, make_cover_letter, rewrite_resume)
from reporting import make_pdf, send_email
from resume_parser import extract_text
from resume_suggestions import generate_resume_suggestions
from ats_score import calculate_ats_score
from .auth import login_required

candidate = Blueprint("candidate", __name__)


def latest_resume(user_id):
    return ResumeVersion.query.filter_by(user_id=user_id).order_by(ResumeVersion.created_at.desc()).first()


def safe_https(value):
    value = value.strip()
    return value if not value or value.startswith("https://") else ""


@candidate.post("/upload")
def upload_resume():
    resume_file = request.files.get("resume")
    job_description = request.form.get("job_description", "").strip()
    if not resume_file or not resume_file.filename:
        flash("Choose a PDF resume to analyze.", "error")
        return redirect(url_for("home"))
    if not resume_file.filename.lower().endswith(".pdf"):
        flash("Please upload a PDF file.", "error")
        return redirect(url_for("home"))
    if len(job_description) > 30000:
        flash("Job descriptions are limited to 30,000 characters.", "error")
        return redirect(url_for("home"))
    pdf_bytes = resume_file.read()
    if not pdf_bytes.startswith(b"%PDF-"):
        flash("The selected file is not a valid PDF.", "error")
        return redirect(url_for("home"))
    try:
        resume_text = extract_text(pdf_bytes)
    except Exception:
        current_app.logger.exception("Resume PDF parsing failed")
        flash("We couldn’t read that PDF. Please try another file.", "error")
        return redirect(url_for("home"))
    if not resume_text.strip():
        flash("No selectable text was found. Please upload a text-based PDF.", "error")
        return redirect(url_for("home"))

    analysis = analyze_text(resume_text, job_description)
    suggestions = generate_resume_suggestions(analysis["ats_score"], analysis["skills"], analysis["missing_skills"], resume_text)
    missing = [{"skill": skill,
                "why": f"{skill.title()} appears in the supplied job description but not in this resume.",
                "learn": SKILL_RESOURCES.get(skill, ("", "", ""))[0] or "Practice with a small project and document the result."}
               for skill in analysis["missing_skills"]]
    if g.user and g.user.role == "candidate":
        version = ResumeVersion(user_id=g.user.id, filename=secure_filename(resume_file.filename) or "resume.pdf",
                                extracted_text=resume_text, ats_score=analysis["ats_score"])
        db.session.add(version)
        db.session.flush()
        db.session.add(Analysis(user_id=g.user.id, resume_id=version.id, job_title="Target role",
                                job_description=job_description, ats_score=analysis["match_score"],
                                matched_skills=json.dumps(analysis["matched_skills"]),
                                missing_skills=json.dumps(analysis["missing_skills"])))
        db.session.add(AuditEvent(actor_id=g.user.id, action="resume.analyzed", target_type="resume", target_id=str(version.id)))
        db.session.commit()
    try:
        # Preserve the legacy optional analysis log for deployments already using its schema.
        from database import save_resume
        save_resume(secure_filename(resume_file.filename) or "resume.pdf", analysis["ats_score"])
    except Exception:
        current_app.logger.exception("Legacy analysis history logging failed")
    jobs = [{"job": "Your Job Description", "score": analysis["match_score"]}] if job_description else []
    return render_template("result.html", ats_score=analysis["ats_score"], skills=analysis["skills"],
                           jobs=jobs, missing_skills=missing, suggestions=suggestions, analysis=analysis)


@candidate.get("/dashboard")
@login_required("candidate")
def dashboard():
    versions = ResumeVersion.query.filter_by(user_id=g.user.id).order_by(ResumeVersion.created_at.desc()).all()
    analyses = Analysis.query.filter_by(user_id=g.user.id).order_by(Analysis.created_at.desc()).limit(12).all()
    applications = Application.query.filter_by(user_id=g.user.id).order_by(Application.created_at.desc()).all()
    saved = SavedJob.query.filter_by(user_id=g.user.id).order_by(SavedJob.created_at.desc()).all()
    recent_scores = [v.ats_score for v in reversed(versions[:10])]
    return render_template("candidate_dashboard.html", versions=versions, analyses=analyses,
                           applications=applications, saved_jobs=saved, recent_scores=recent_scores)


@candidate.route("/profile", methods=["GET", "POST"])
@login_required("candidate")
def profile():
    if request.method == "POST":
        g.user.name = request.form.get("name", "").strip()[:120] or g.user.name
        profile = g.user.profile or CandidateProfile(user_id=g.user.id)
        profile.headline = request.form.get("headline", "").strip()[:180]
        profile.location = request.form.get("location", "").strip()[:120]
        profile.phone = request.form.get("phone", "").strip()[:40]
        profile.skills = request.form.get("skills", "").strip()[:2000]
        profile.salary_expectation = request.form.get("salary_expectation", "").strip()[:80]
        profile.linkedin_url = safe_https(request.form.get("linkedin_url", "")[:300])
        profile.github_url = safe_https(request.form.get("github_url", "")[:300])
        if not g.user.profile:
            g.user.profile = profile
        db.session.commit()
        flash("Profile saved.", "success")
        return redirect(url_for("candidate.profile"))
    return render_template("profile.html")


@candidate.get("/resume/history/<int:resume_id>")
@login_required("candidate")
def resume_history_detail(resume_id):
    version = ResumeVersion.query.filter_by(id=resume_id, user_id=g.user.id).first_or_404()
    previous = (ResumeVersion.query.filter(ResumeVersion.user_id == g.user.id, ResumeVersion.created_at < version.created_at)
                .order_by(ResumeVersion.created_at.desc()).first())
    difference = version.ats_score - previous.ats_score if previous else None
    return render_template("resume_history.html", version=version, previous=previous, difference=difference)


@candidate.post("/resume/<int:resume_id>/delete")
@login_required("candidate")
def delete_resume(resume_id):
    version = ResumeVersion.query.filter_by(id=resume_id, user_id=g.user.id).first_or_404()
    db.session.delete(version)
    db.session.commit()
    flash("Resume version and its analysis history were deleted.", "success")
    return redirect(url_for("candidate.dashboard"))


@candidate.route("/builder", methods=["GET", "POST"])
@login_required("candidate")
def builder():
    draft = None
    form_values = {key: "" for key in ("name", "contact", "summary", "skills", "experience", "projects", "education")}
    if request.method == "POST":
        fields = {key: request.form.get(key, "").strip()[:5000] for key in ("name", "contact", "summary", "skills", "experience", "projects", "education")}
        if not fields["name"]:
            flash("Add your name to create a resume.", "error")
        else:
            sections = [fields["name"], fields["contact"], fields["summary"], "SKILLS\n" + fields["skills"],
                        "EXPERIENCE\n" + fields["experience"], "PROJECTS\n" + fields["projects"], "EDUCATION\n" + fields["education"]]
            draft = "\n\n".join(section for section in sections if section.strip())
            ats, _skills = calculate_ats_score(draft)
            template_name = request.form.get("template", "classic")
            if template_name not in {"classic", "modern", "compact"}:
                template_name = "classic"
            version = ResumeVersion(user_id=g.user.id, filename="resume-builder.txt", extracted_text=draft,
                                    ats_score=ats, template_name=template_name, builder_data=json.dumps(fields))
            db.session.add(version)
            db.session.commit()
            draft_id = version.id
            flash("Resume draft saved to your version history.", "success")
            return redirect(url_for("candidate.builder", preview=draft_id, template=request.form.get("template", "classic")))
    preview_id = request.args.get("preview", type=int)
    if preview_id:
        version = ResumeVersion.query.filter_by(id=preview_id, user_id=g.user.id).first_or_404()
        draft = version.extracted_text
        draft_id = version.id
        try:
            form_values.update(json.loads(version.builder_data or "{}"))
        except (ValueError, TypeError):
            pass
    else:
        draft_id = None
    return render_template("builder.html", draft=draft, draft_id=draft_id, form_values=form_values,
                           selected_template=request.args.get("template", "classic"))


@candidate.get("/builder/<int:resume_id>/pdf")
@login_required("candidate")
def builder_pdf(resume_id):
    version = ResumeVersion.query.filter_by(id=resume_id, user_id=g.user.id).first_or_404()
    return send_file(BytesIO(make_pdf("Resume", version.extracted_text, version.template_name)), as_attachment=True,
                     download_name="resume.pdf", mimetype="application/pdf")


@candidate.route("/rewrite", methods=["GET", "POST"])
def rewrite():
    original = request.form.get("resume_text", "")[:20000] if request.method == "POST" else ""
    rewritten = rewrite_resume(original) if original else ""
    return render_template("rewrite.html", original=original, rewritten=rewritten)


@candidate.route("/cover-letter", methods=["GET", "POST"])
@login_required("candidate")
def cover_letter():
    letter = None
    if request.method == "POST":
        job_title = request.form.get("job_title", "").strip()[:180] or "Target position"
        company = request.form.get("company", "").strip()[:180]
        description = request.form.get("job_description", "").strip()[:12000]
        resume = latest_resume(g.user.id)
        body = make_cover_letter(g.user.name, resume.extracted_text if resume else "", job_title, company, description)
        letter = CoverLetter(user_id=g.user.id, job_title=job_title, body=body)
        db.session.add(letter)
        db.session.commit()
        return redirect(url_for("candidate.cover_letter", letter=letter.id))
    letter_id = request.args.get("letter", type=int)
    if letter_id:
        letter = CoverLetter.query.filter_by(id=letter_id, user_id=g.user.id).first_or_404()
    return render_template("cover_letter.html", letter=letter)


@candidate.get("/cover-letter/<int:letter_id>/pdf")
@login_required("candidate")
def cover_letter_pdf(letter_id):
    letter = CoverLetter.query.filter_by(id=letter_id, user_id=g.user.id).first_or_404()
    return send_file(BytesIO(make_pdf("Cover Letter — " + letter.job_title, letter.body)), as_attachment=True,
                     download_name="cover-letter.pdf", mimetype="application/pdf")


@candidate.route("/learning", methods=["GET", "POST"])
@login_required("candidate")
def learning():
    resume = latest_resume(g.user.id)
    role_description = request.form.get("job_description", "")[:12000] if request.method == "POST" else ""
    if request.method == "POST":
        present = resume.extracted_text if resume else (g.user.profile.skills if g.user.profile else "")
        missing = [skill for skill in SKILL_RESOURCES if skill in role_description.casefold() and skill not in present.casefold()]
        items = learning_recommendations(missing)
    else:
        items = []
    return render_template("learning.html", items=items, role_description=role_description)


@candidate.route("/roadmap", methods=["GET", "POST"])
@login_required("candidate")
def roadmap():
    role = request.form.get("role", "").strip()[:180] if request.method == "POST" else ""
    skills = request.form.get("skills", "").strip()[:1200] if request.method == "POST" else (g.user.profile.skills if g.user.profile else "")
    missing = [skill for skill in SKILL_RESOURCES if request.method == "POST" and skill in role.casefold() and skill not in skills.casefold()]
    resources = learning_recommendations(missing)
    timeline = ["Weeks 1–2: build a focused foundation and complete one guided exercise.",
                "Weeks 3–4: build a small project that combines the target skills.",
                "Weeks 5–6: document, test, and present the project; review progress and update your resume."]
    return render_template("roadmap.html", role=role, skills=skills, resources=resources, timeline=timeline,
                           salary_expectation=g.user.profile.salary_expectation if g.user.profile else "")


@candidate.route("/linkedin", methods=["GET", "POST"])
@login_required("candidate")
def linkedin_optimizer():
    resume = latest_resume(g.user.id)
    source = request.form.get("resume_text", "")[:12000] if request.method == "POST" else (resume.extracted_text if resume else "")
    profile = g.user.profile
    skills = [s for s in SKILL_RESOURCES if s in source.casefold()]
    headline = f"{(profile.headline or 'Professional') if profile else 'Professional'} | " + (" · ".join(skills[:4]) or "Open to opportunities")
    about = (f"I am {g.user.name}, a professional focused on {', '.join(skills[:5]) or 'my field'} . "
             "I enjoy solving practical problems, learning from collaborative teams, and building work I can explain and stand behind. "
             "I am open to conversations about roles where I can contribute and keep growing.") if source else ""
    return render_template("linkedin.html", source=source, headline=headline if source else "", about=about, skills=skills)


@candidate.route("/compare", methods=["GET", "POST"])
@login_required("candidate")
def compare_companies():
    results = []
    resume = latest_resume(g.user.id)
    if request.method == "POST":
        descriptions = [d.strip() for d in re.split(r"\n\s*---\s*\n", request.form.get("job_descriptions", "")[:30000]) if d.strip()]
        if not resume:
            flash("Upload a resume before comparing roles.", "warning")
        elif not descriptions:
            flash("Separate job descriptions with a line containing ---.", "warning")
        else:
            for index, description in enumerate(descriptions[:10], 1):
                name, _, body = description.partition("\n")
                report = analyze_text(resume.extracted_text, body or description)
                results.append({"company": name[:180] or f"Company {index}", **report})
            results.sort(key=lambda item: item["match_score"], reverse=True)
    return render_template("compare.html", results=results)


@candidate.route("/interview/questions", methods=["GET", "POST"])
@login_required("candidate")
def question_generator():
    questions = None
    if request.method == "POST":
        questions = interview_questions(request.form.get("role", "")[:180], request.form.get("skills", "")[:1000],
                                        request.form.get("projects", "")[:1000], request.form.get("job_description", "")[:10000])
    return render_template("questions.html", questions=questions)


@candidate.route("/interview/mock", methods=["GET", "POST"])
@login_required("candidate")
def mock_interview():
    score = None
    feedback = None
    if request.method == "POST":
        role = request.form.get("role", "Interview practice").strip()[:180]
        answer = request.form.get("answer", "").strip()[:10000]
        if answer:
            score, feedback = evaluate_answer(answer)
            db.session.add(InterviewSession(user_id=g.user.id, role_title=role, score=score, feedback=feedback))
            db.session.commit()
    questions = interview_questions(request.args.get("role", "Target role"),
                                    g.user.profile.skills if g.user.profile else "", "", "")
    return render_template("mock_interview.html", questions=questions["Technical"], score=score, feedback=feedback)


@candidate.get("/jobs")
def jobs():
    listings = Job.query.filter_by(active=True).order_by(Job.created_at.desc()).limit(100).all()
    return render_template("jobs.html", listings=listings)


@candidate.post("/jobs/<int:job_id>/save")
@login_required("candidate")
def save_job(job_id):
    job = Job.query.filter_by(id=job_id, active=True).first_or_404()
    try:
        db.session.add(SavedJob(user_id=g.user.id, title=f"{job.title} — {job.company.name}", description=job.description))
        db.session.commit()
        flash("Job bookmarked.", "success")
    except Exception:
        db.session.rollback()
        flash("This job is already bookmarked.", "warning")
    return redirect(url_for("candidate.jobs"))


@candidate.post("/jobs/<int:job_id>/apply")
@login_required("candidate")
def apply_job(job_id):
    job = Job.query.filter_by(id=job_id, active=True).first_or_404()
    resume = latest_resume(g.user.id)
    if not resume:
        flash("Add a resume version before applying.", "warning")
        return redirect(url_for("candidate.dashboard"))
    try:
        report = analyze_text(resume.extracted_text, job.description)
        application = Application(job_id=job.id, user_id=g.user.id, resume_id=resume.id, ats_score=report["match_score"])
        db.session.add(application)
        db.session.commit()
        flash("Your application was submitted.", "success")
    except Exception:
        db.session.rollback()
        flash("You have already applied for this job.", "warning")
    return redirect(url_for("candidate.dashboard"))


@candidate.post("/jobs/saved/<int:saved_id>/delete")
@login_required("candidate")
def delete_saved_job(saved_id):
    saved = SavedJob.query.filter_by(id=saved_id, user_id=g.user.id).first_or_404()
    db.session.delete(saved)
    db.session.commit()
    return redirect(url_for("candidate.dashboard"))


@candidate.get("/analysis/<int:analysis_id>/pdf")
@login_required("candidate")
def analysis_pdf(analysis_id):
    report = Analysis.query.filter_by(id=analysis_id, user_id=g.user.id).first_or_404()
    content = (f"Role: {report.job_title}\nATS match score: {report.ats_score}%\n\n"
               f"Matched skills: {', '.join(json.loads(report.matched_skills)) or 'Not detected'}\n"
               f"Missing skills: {', '.join(json.loads(report.missing_skills)) or 'Not detected'}\n\n"
               f"Job description:\n{report.job_description[:8000]}")
    return send_file(BytesIO(make_pdf("Resume analysis report", content)), as_attachment=True,
                     download_name="resume-analysis.pdf", mimetype="application/pdf")


@candidate.post("/analysis/<int:analysis_id>/email")
@login_required("candidate")
def email_analysis(analysis_id):
    report = Analysis.query.filter_by(id=analysis_id, user_id=g.user.id).first_or_404()
    recipient = request.form.get("email", "").strip()[:254]
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", recipient):
        flash("Enter a valid email address.", "error")
        return redirect(url_for("candidate.dashboard"))
    matched = json.loads(report.matched_skills)
    missing = json.loads(report.missing_skills)
    body = (f"Resume: {report.resume.filename}\nATS completeness: {report.resume.ats_score}%\n"
            f"Role match estimate for {report.job_title}: {report.ats_score}%\n"
            f"Matched skills: {', '.join(matched) or 'Not detected'}\n"
            f"Skills to review: {', '.join(missing) or 'No catalogue gaps detected'}\n\n"
            "Scores are informational heuristics, not hiring decisions. The skill catalogue is limited.")
    try:
        send_email(recipient, "Your resume analysis report", body, "resume-analysis.pdf", make_pdf("Resume analysis report", body))
        from models import EmailReport
        db.session.add(EmailReport(user_id=g.user.id, report_type="analysis", recipient=recipient))
        db.session.commit()
        flash("Report emailed.", "success")
    except Exception as error:
        db.session.rollback()
        current_app.logger.exception("Report email failed")
        flash(str(error)[:220], "error")
    return redirect(url_for("candidate.dashboard"))


@candidate.post("/resume/<int:resume_id>/email")
@login_required("candidate")
def email_resume(resume_id):
    version = ResumeVersion.query.filter_by(id=resume_id, user_id=g.user.id).first_or_404()
    recipient = request.form.get("email", "").strip()[:254]
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", recipient):
        flash("Enter a valid email address.", "error")
        return redirect(url_for("candidate.dashboard"))
    try:
        body = f"Attached is the resume report for {version.filename}. Its ATS-style completeness estimate is {version.ats_score}%."
        send_email(recipient, "Your resume report", body, "resume.pdf",
                   make_pdf("Resume report", f"Resume: {version.filename}\nATS-style completeness: {version.ats_score}%\n\n{version.extracted_text}"))
        from models import EmailReport
        db.session.add(EmailReport(user_id=g.user.id, report_type="resume", recipient=recipient))
        db.session.commit()
        flash("Resume report emailed.", "success")
    except Exception as error:
        db.session.rollback()
        current_app.logger.exception("Resume email failed")
        flash(str(error)[:220], "error")
    return redirect(url_for("candidate.dashboard"))


@candidate.post("/cover-letter/<int:letter_id>/email")
@login_required("candidate")
def email_cover_letter(letter_id):
    letter = CoverLetter.query.filter_by(id=letter_id, user_id=g.user.id).first_or_404()
    recipient = request.form.get("email", "").strip()[:254]
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", recipient):
        flash("Enter a valid email address.", "error")
        return redirect(url_for("candidate.cover_letter", letter=letter.id))
    try:
        send_email(recipient, f"Cover letter: {letter.job_title}", "Attached is your cover letter draft. Review it before sending.",
                   "cover-letter.pdf", make_pdf("Cover Letter — " + letter.job_title, letter.body))
        from models import EmailReport
        db.session.add(EmailReport(user_id=g.user.id, report_type="cover_letter", recipient=recipient))
        db.session.commit()
        flash("Cover letter emailed.", "success")
    except Exception as error:
        db.session.rollback()
        current_app.logger.exception("Cover letter email failed")
        flash(str(error)[:220], "error")
    return redirect(url_for("candidate.cover_letter", letter=letter.id))
