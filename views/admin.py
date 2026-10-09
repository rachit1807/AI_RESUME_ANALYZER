import csv
from io import StringIO

from flask import Blueprint, abort, flash, g, make_response, redirect, render_template, url_for

from models import Analysis, Application, AuditEvent, Company, Job, ResumeVersion, User, db
from .auth import login_required

admin = Blueprint("admin", __name__)


@admin.get("/admin")
@login_required("admin")
def dashboard():
    users = User.query.order_by(User.created_at.desc()).limit(200).all()
    stats = {"users": User.query.count(), "candidates": User.query.filter_by(role="candidate").count(),
             "recruiters": User.query.filter_by(role="recruiter").count(), "jobs": Job.query.count(),
             "active_jobs": Job.query.filter_by(active=True).count(), "applications": Application.query.count(),
             "analyses": Analysis.query.count(), "resume_versions": ResumeVersion.query.count(),
             "companies": Company.query.count()}
    events = AuditEvent.query.order_by(AuditEvent.created_at.desc()).limit(20).all()
    jobs = Job.query.order_by(Job.created_at.desc()).limit(100).all()
    return render_template("admin_dashboard.html", users=users, stats=stats, events=events, jobs=jobs)


@admin.post("/admin/jobs/<int:job_id>/status")
@login_required("admin")
def set_job_status(job_id):
    job = db.session.get(Job, job_id)
    if job is None:
        abort(404)
    job.active = request_value("active") == "true"
    db.session.add(AuditEvent(actor_id=g.user.id, action="admin.job_status_changed", target_type="job", target_id=str(job.id)))
    db.session.commit()
    flash("Job listing updated.", "success")
    return redirect(url_for("admin.dashboard"))


@admin.post("/admin/users/<int:user_id>/update")
@login_required("admin")
def update_user(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    role = request_value("role")
    active = request_value("active")
    if role not in {"candidate", "recruiter", "admin"} or active not in {"true", "false"}:
        abort(400)
    if user.id == g.user.id and (role != "admin" or active != "true"):
        flash("You cannot remove your own administrator access.", "error")
        return redirect(url_for("admin.dashboard"))
    user.role = role
    user.active = active == "true"
    db.session.add(AuditEvent(actor_id=g.user.id, action="admin.user_updated", target_type="user", target_id=str(user.id)))
    db.session.commit()
    flash("User account updated.", "success")
    return redirect(url_for("admin.dashboard"))


@admin.post("/admin/users/<int:user_id>/delete")
@login_required("admin")
def delete_user(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    if user.id == g.user.id:
        flash("You cannot delete your own administrator account.", "error")
    else:
        db.session.delete(user)
        db.session.add(AuditEvent(actor_id=g.user.id, action="admin.user_deleted", target_type="user", target_id=str(user_id)))
        db.session.commit()
        flash("User and associated account data deleted.", "success")
    return redirect(url_for("admin.dashboard"))


@admin.get("/admin/reports.csv")
@login_required("admin")
def reports_csv():
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Report", "Count"])
    for label, count in (("Users", User.query.count()), ("Candidates", User.query.filter_by(role="candidate").count()),
                         ("Recruiters", User.query.filter_by(role="recruiter").count()), ("Companies", Company.query.count()),
                         ("Jobs", Job.query.count()), ("Applications", Application.query.count()),
                         ("Resume analyses", Analysis.query.count()), ("Resume versions", ResumeVersion.query.count())):
        writer.writerow([label, count])
    response = make_response("\ufeff" + output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = 'attachment; filename="platform-report.csv"'
    return response


def request_value(name):
    from flask import request
    return request.form.get(name, "")
