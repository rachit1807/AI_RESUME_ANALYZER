import csv
from io import BytesIO, StringIO

from flask import Blueprint, abort, current_app, flash, g, make_response, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from models import Application, AuditEvent, Company, Job, ResumeRankingBatch, ResumeRankingItem, db
from recruitment_services import analyze_text
from resume_parser import extract_text
from .auth import login_required

recruiter = Blueprint("recruiter", __name__)


def owned_company():
    return Company.query.filter_by(owner_id=g.user.id).first()


@recruiter.get("/recruiter")
@login_required("recruiter")
def portal():
    return redirect(url_for("recruiter.jobs_dashboard"))


@recruiter.route("/recruiter/jobs", methods=["GET", "POST"])
@login_required("recruiter")
def jobs_dashboard():
    company = owned_company()
    if company is None:
        flash("Your company profile needs attention. Please contact an administrator.", "error")
        return render_template("recruiter_dashboard.html", company=None, jobs=[], total_applications=0)
    if request.method == "POST":
        title = request.form.get("title", "").strip()[:180]
        description = request.form.get("description", "").strip()[:30000]
        location = request.form.get("location", "").strip()[:120]
        salary_range = request.form.get("salary_range", "").strip()[:100]
        if not title or len(description) < 40:
            flash("Add a title and a job description with at least 40 characters.", "error")
        else:
            job = Job(company_id=company.id, title=title, description=description, location=location, salary_range=salary_range)
            db.session.add(job)
            db.session.flush()
            db.session.add(AuditEvent(actor_id=g.user.id, action="job.created", target_type="job", target_id=str(job.id)))
            db.session.commit()
            flash("Job published.", "success")
            return redirect(url_for("recruiter.jobs_dashboard"))
    jobs = Job.query.filter_by(company_id=company.id).order_by(Job.created_at.desc()).all()
    total_applications = sum(len(job.applications) for job in jobs)
    return render_template("recruiter_dashboard.html", company=company, jobs=jobs, total_applications=total_applications)


@recruiter.post("/recruiter/jobs/<int:job_id>/status")
@login_required("recruiter")
def job_status(job_id):
    company = owned_company()
    job = Job.query.filter_by(id=job_id, company_id=company.id if company else -1).first_or_404()
    job.active = not job.active
    db.session.add(AuditEvent(actor_id=g.user.id, action="job.status_changed", target_type="job", target_id=str(job.id)))
    db.session.commit()
    return redirect(url_for("recruiter.jobs_dashboard"))


@recruiter.get("/recruiter/jobs/<int:job_id>/applicants")
@login_required("recruiter")
def applicants(job_id):
    company = owned_company()
    job = Job.query.filter_by(id=job_id, company_id=company.id if company else -1).first_or_404()
    status = request.args.get("status", "")[:24]
    query = request.args.get("q", "").strip()[:100].casefold()
    rows = Application.query.filter_by(job_id=job.id).all()
    if status in {"submitted", "shortlisted", "rejected"}:
        rows = [row for row in rows if row.status == status]
    if query:
        rows = [row for row in rows if query in row.candidate.name.casefold() or query in row.candidate.email.casefold()]
    rows.sort(key=lambda row: (row.ats_score, row.created_at), reverse=True)
    return render_template("applicants.html", job=job, applications=rows, selected_status=status, query=request.args.get("q", ""))


@recruiter.post("/recruiter/applications/<int:application_id>/status")
@login_required("recruiter")
def application_status(application_id):
    company = owned_company()
    application = (Application.query.join(Job).filter(Application.id == application_id,
                    Job.company_id == (company.id if company else -1)).first_or_404())
    status = request.form.get("status", "")
    if status not in {"shortlisted", "rejected", "submitted"}:
        abort(400)
    application.status = status
    db.session.add(AuditEvent(actor_id=g.user.id, action=f"application.{status}", target_type="application", target_id=str(application.id)))
    db.session.commit()
    flash(f"Candidate marked {status}.", "success")
    return redirect(url_for("recruiter.applicants", job_id=application.job_id))


@recruiter.get("/recruiter/jobs/<int:job_id>/report.csv")
@login_required("recruiter")
def applicants_csv(job_id):
    company = owned_company()
    job = Job.query.filter_by(id=job_id, company_id=company.id if company else -1).first_or_404()
    rows = Application.query.filter_by(job_id=job.id).order_by(Application.ats_score.desc()).all()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Candidate", "Email", "ATS Match", "Application Status", "Applied"])
    for row in rows:
        writer.writerow([row.candidate.name, row.candidate.email, row.ats_score, row.status, row.created_at.isoformat()])
    response = make_response("\ufeff" + output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = f'attachment; filename="job-{job.id}-applicants.csv"'
    return response


@recruiter.route("/recruiter/rank", methods=["GET", "POST"])
@login_required("recruiter")
def rank_resumes():
    batch = None
    min_score = request.args.get("min", default=0, type=int)
    query = request.args.get("q", "").strip()[:100].casefold()
    if request.method == "POST":
        job_description = request.form.get("job_description", "").strip()[:20000]
        files = request.files.getlist("resumes")
        files = [file for file in files if file and file.filename]
        if not job_description or not files:
            flash("Add a job description and at least one PDF resume.", "error")
        elif len(files) > 25:
            flash("Rank up to 25 resumes per batch.", "error")
        else:
            batch = ResumeRankingBatch(recruiter_id=g.user.id, job_title=request.form.get("job_title", "Role")[:180] or "Role")
            db.session.add(batch)
            db.session.flush()
            accepted = 0
            for file in files:
                filename = secure_filename(file.filename)[:255]
                if not filename.lower().endswith(".pdf"):
                    continue
                data = file.read()
                if len(data) > 3 * 1024 * 1024 or not data.startswith(b"%PDF-"):
                    continue
                try:
                    text = extract_text(data)
                    if not text.strip():
                        continue
                    report = analyze_text(text, job_description)
                    db.session.add(ResumeRankingItem(batch_id=batch.id, filename=filename,
                        ats_score=report["ats_score"], match_score=report["match_score"],
                        matched_skills=__import__("json").dumps(report["matched_skills"]),
                        missing_skills=__import__("json").dumps(report["missing_skills"])))
                    accepted += 1
                except Exception:
                    current_app.logger.exception("Batch resume parsing failed")
            if not accepted:
                db.session.rollback()
                flash("No readable text-based PDF resumes were found. Nothing was stored.", "error")
            else:
                db.session.add(AuditEvent(actor_id=g.user.id, action="resume.batch_ranked", target_type="ranking_batch", target_id=str(batch.id)))
                db.session.commit()
                return redirect(url_for("recruiter.rank_resumes", batch=batch.id))
    batch_id = request.args.get("batch", type=int)
    if batch_id:
        batch = ResumeRankingBatch.query.filter_by(id=batch_id, recruiter_id=g.user.id).first_or_404()
        items = [item for item in batch.items if item.match_score >= min_score and (not query or query in item.filename.casefold())]
        items.sort(key=lambda item: (item.match_score, item.ats_score), reverse=True)
    else:
        items = []
    return render_template("rank_resumes.html", batch=batch, items=items, min_score=min_score, query=request.args.get("q", ""))


@recruiter.get("/recruiter/rank/<int:batch_id>.csv")
@login_required("recruiter")
def ranking_csv(batch_id):
    batch = ResumeRankingBatch.query.filter_by(id=batch_id, recruiter_id=g.user.id).first_or_404()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Resume file", "ATS completeness", "Job match", "Matched skills", "Missing skills"])
    import json
    for item in batch.items:
        writer.writerow([item.filename, item.ats_score, item.match_score,
                         ", ".join(json.loads(item.matched_skills)), ", ".join(json.loads(item.missing_skills))])
    response = make_response("\ufeff" + output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = f'attachment; filename="rankings-{batch.id}.csv"'
    return response
