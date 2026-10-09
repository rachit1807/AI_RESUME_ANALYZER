import re
from functools import wraps

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from models import AuditEvent, CandidateProfile, Company, User, db

auth = Blueprint("auth", __name__)


def role_home(user):
    if user.role == "admin":
        return url_for("admin.dashboard")
    if user.role == "recruiter":
        return url_for("recruiter.jobs_dashboard")
    return url_for("candidate.dashboard")


@auth.before_app_request
def load_user():
    user_id = session.get("user_id")
    g.user = db.session.get(User, user_id) if user_id else None
    if g.user and not g.user.active:
        session.clear()
        g.user = None


def login_required(*roles):
    def decorate(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not g.user:
                flash("Please sign in to continue.", "warning")
                return redirect(url_for("auth.login", next=request.path))
            if roles and g.user.role not in roles:
                return render_template("error.html", message="You do not have access to this page."), 403
            return view(*args, **kwargs)
        return wrapped
    return decorate


@auth.route("/register", methods=["GET", "POST"])
def register():
    if g.user:
        return redirect(role_home(g.user))
    if request.method == "POST":
        name = request.form.get("name", "").strip()[:120]
        email = request.form.get("email", "").strip().lower()[:254]
        password = request.form.get("password", "")
        role = request.form.get("role", "candidate")
        company_name = request.form.get("company", "").strip()[:180]
        if not name or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            flash("Enter your name and a valid email address.", "error")
        elif len(password) < 12:
            flash("Use a password with at least 12 characters.", "error")
        elif role not in {"candidate", "recruiter"}:
            flash("Select a valid account type.", "error")
        elif role == "recruiter" and not company_name:
            flash("Recruiter accounts need a company name.", "error")
        else:
            user = User(name=name, email=email, password_hash=generate_password_hash(password), role=role)
            user.profile = CandidateProfile()
            try:
                db.session.add(user)
                db.session.flush()
                if role == "recruiter":
                    db.session.add(Company(name=company_name, owner_id=user.id))
                db.session.add(AuditEvent(actor_id=user.id, action="account.created", target_type="user", target_id=str(user.id)))
                db.session.commit()
                session.clear()
                session["user_id"] = user.id
                session.permanent = True
                flash("Your account is ready.", "success")
                return redirect(role_home(user))
            except IntegrityError:
                db.session.rollback()
                flash("An account with that email already exists.", "error")
    return render_template("register.html")


@auth.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(role_home(g.user))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()[:254]
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email, active=True).first()
        if user and check_password_hash(user.password_hash, password):
            session.clear()
            session["user_id"] = user.id
            session.permanent = True
            db.session.add(AuditEvent(actor_id=user.id, action="auth.login", target_type="user", target_id=str(user.id)))
            db.session.commit()
            return redirect(request.args.get("next") if request.args.get("next", "").startswith("/") and not request.args.get("next", "").startswith("//") else role_home(user))
        flash("Email or password was incorrect.", "error")
    return render_template("login.html")


@auth.post("/logout")
def logout():
    session.clear()
    flash("You have signed out.", "success")
    return redirect(url_for("home"))
