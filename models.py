"""Database models for the candidate, recruiter, and administrator portals."""
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint

db = SQLAlchemy()


def utc_now_naive():
    """Return UTC as a naive value for the existing TIMESTAMP columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="candidate", index=True)
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now_naive)
    profile = db.relationship("CandidateProfile", backref="user", uselist=False, cascade="all, delete-orphan")


class CandidateProfile(db.Model):
    __tablename__ = "candidate_profiles"
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    headline = db.Column(db.String(180), default="")
    location = db.Column(db.String(120), default="")
    phone = db.Column(db.String(40), default="")
    skills = db.Column(db.Text, default="")
    salary_expectation = db.Column(db.String(80), default="")
    linkedin_url = db.Column(db.String(300), default="")
    github_url = db.Column(db.String(300), default="")


class Company(db.Model):
    __tablename__ = "companies"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(180), nullable=False)
    website = db.Column(db.String(300), default="")
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now_naive)
    owner = db.relationship("User", backref=db.backref("company", uselist=False, cascade="all, delete-orphan", single_parent=True))


class Job(db.Model):
    # Keep the legacy `jobs` table available to database.py/get_jobs().
    __tablename__ = "recruiter_jobs"
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(180), nullable=False)
    location = db.Column(db.String(120), default="")
    salary_range = db.Column(db.String(100), default="")
    description = db.Column(db.Text, nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now_naive)
    company = db.relationship("Company", backref=db.backref("jobs", cascade="all, delete-orphan"))


class ResumeVersion(db.Model):
    __tablename__ = "resume_versions"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    extracted_text = db.Column(db.Text, nullable=False)
    builder_data = db.Column(db.Text, nullable=False, default="{}")
    ats_score = db.Column(db.Integer, nullable=False, default=0)
    template_name = db.Column(db.String(30), nullable=False, default="classic")
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now_naive, index=True)
    user = db.relationship("User", backref=db.backref("resume_versions", cascade="all, delete-orphan", order_by="ResumeVersion.created_at.desc()"))


class Analysis(db.Model):
    __tablename__ = "analyses"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    resume_id = db.Column(db.Integer, db.ForeignKey("resume_versions.id", ondelete="CASCADE"), nullable=False)
    job_title = db.Column(db.String(180), default="Target role")
    job_description = db.Column(db.Text, nullable=False)
    ats_score = db.Column(db.Integer, nullable=False)
    matched_skills = db.Column(db.Text, nullable=False, default="[]")
    missing_skills = db.Column(db.Text, nullable=False, default="[]")
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now_naive, index=True)
    user = db.relationship("User", backref=db.backref("analyses", cascade="all, delete-orphan"))
    resume = db.relationship("ResumeVersion", backref=db.backref("analyses", cascade="all, delete-orphan"))


class SavedJob(db.Model):
    __tablename__ = "saved_jobs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now_naive)
    __table_args__ = (UniqueConstraint("user_id", "title", name="uq_saved_job_title"),)
    user = db.relationship("User", backref=db.backref("saved_jobs", cascade="all, delete-orphan"))


class Application(db.Model):
    __tablename__ = "applications"
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("recruiter_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    resume_id = db.Column(db.Integer, db.ForeignKey("resume_versions.id", ondelete="SET NULL"), nullable=True)
    ats_score = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(24), nullable=False, default="submitted", index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now_naive)
    __table_args__ = (UniqueConstraint("job_id", "user_id", name="uq_application_candidate_job"),)
    job = db.relationship("Job", backref=db.backref("applications", cascade="all, delete-orphan"))
    candidate = db.relationship("User", backref=db.backref("applications", cascade="all, delete-orphan"))
    resume = db.relationship("ResumeVersion")


class CoverLetter(db.Model):
    __tablename__ = "cover_letters"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    job_title = db.Column(db.String(180), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now_naive)
    user = db.relationship("User", backref=db.backref("cover_letters", cascade="all, delete-orphan"))


class InterviewSession(db.Model):
    __tablename__ = "interview_sessions"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role_title = db.Column(db.String(180), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    feedback = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now_naive)
    user = db.relationship("User", backref=db.backref("interview_sessions", cascade="all, delete-orphan"))


class ResumeRankingBatch(db.Model):
    __tablename__ = "resume_ranking_batches"
    id = db.Column(db.Integer, primary_key=True)
    recruiter_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    job_title = db.Column(db.String(180), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now_naive)
    recruiter = db.relationship("User", backref=db.backref("ranking_batches", cascade="all, delete-orphan"))
    items = db.relationship("ResumeRankingItem", backref="batch", cascade="all, delete-orphan", order_by="ResumeRankingItem.match_score.desc()")


class ResumeRankingItem(db.Model):
    __tablename__ = "resume_ranking_items"
    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey("resume_ranking_batches.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    ats_score = db.Column(db.Integer, nullable=False)
    match_score = db.Column(db.Integer, nullable=False)
    matched_skills = db.Column(db.Text, nullable=False, default="[]")
    missing_skills = db.Column(db.Text, nullable=False, default="[]")


class EmailReport(db.Model):
    __tablename__ = "email_reports"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    report_type = db.Column(db.String(50), nullable=False)
    recipient = db.Column(db.String(254), nullable=False)
    sent_at = db.Column(db.DateTime, nullable=False, default=utc_now_naive)


class AuditEvent(db.Model):
    __tablename__ = "audit_events"
    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = db.Column(db.String(80), nullable=False)
    target_type = db.Column(db.String(60), nullable=False)
    target_id = db.Column(db.String(80), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now_naive)
