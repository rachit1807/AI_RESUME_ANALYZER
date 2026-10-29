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
                if request.path == "/admin" or request.path.startswith("/admin/"):
                    endpoint = "auth.admin_login"
                elif request.path == "/recruiter" or request.path.startswith("/recruiter/"):
                    endpoint = "auth.recruiter_login"
                else:
                    endpoint = "auth.login"
                return redirect(url_for(endpoint, next=request.path))
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


def _safe_portal_next(target, role):
    if not target.startswith("/") or target.startswith("//"):
        return None
    path = target.partition("?")[0]
    if role == "admin":
        return target if path == "/admin" or path.startswith("/admin/") else None
    if role == "recruiter":
        return target if path == "/recruiter" or path.startswith("/recruiter/") else None
    if path == "/admin" or path.startswith("/admin/") or path == "/recruiter" or path.startswith("/recruiter/"):
        return None
    return target


def _portal_login(expected_role):
    if g.user:
        return redirect(role_home(g.user))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()[:254]
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email, active=True).first()
        if user and check_password_hash(user.password_hash, password):
            if user.role != expected_role:
                flash(f"This is a {user.role} account. Choose its matching sign-in link below.", "error")
            else:
                session.clear()
                session["user_id"] = user.id
                session.permanent = True
                db.session.add(AuditEvent(actor_id=user.id, action="auth.login", target_type="user", target_id=str(user.id)))
                db.session.commit()
                target = _safe_portal_next(request.args.get("next", ""), expected_role)
                return redirect(target or role_home(user))
        else:
            flash("Email or password was incorrect.", "error")
    return render_template("login.html", portal=expected_role)


@auth.route("/login", methods=["GET", "POST"])
def login():
    return _portal_login("candidate")


@auth.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    return _portal_login("admin")


@auth.route("/recruiter/login", methods=["GET", "POST"])
def recruiter_login():
    return _portal_login("recruiter")


def _portal_logout():
    session.clear()
    flash("You have signed out.", "success")
    return redirect(url_for("home"))


@auth.post("/logout")
def logout():
    return _portal_logout()


@auth.post("/admin/logout")
def admin_logout():
    return _portal_logout()


@auth.post("/recruiter/logout")
def recruiter_logout():
    return _portal_logout()
