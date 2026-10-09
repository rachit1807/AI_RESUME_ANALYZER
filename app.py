"""Application factory and backward-compatible Flask entry point."""
import logging
import os
import secrets
import stat
import time
from pathlib import Path

import click
from flask import Flask, jsonify, render_template, request
from flask_wtf.csrf import CSRFProtect
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import generate_password_hash

from models import CandidateProfile, User, db

csrf = CSRFProtect()


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    if not database_url:
        database_url = "sqlite:///" + str(Path(app.instance_path) / "resume_analyzer.sqlite3")

    secret_key = os.environ.get("SESSION_SECRET")
    if not secret_key:
        secret_path = Path(app.instance_path) / ".session-secret"
        try:
            secret_key = secret_path.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            candidate_secret = secrets.token_urlsafe(48)
            try:
                descriptor = os.open(secret_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, stat.S_IRUSR | stat.S_IWUSR)
                with os.fdopen(descriptor, "w", encoding="utf-8") as secret_file:
                    secret_file.write(candidate_secret)
                secret_key = candidate_secret
            except FileExistsError:
                secret_key = secret_path.read_text(encoding="utf-8").strip()
    app.config.update(
        SECRET_KEY=secret_key,
        SQLALCHEMY_DATABASE_URI=database_url,
        STORAGE_PERSISTENT=bool(database_url),
        STORAGE_TEMPORARY=not bool(database_url) and bool(os.environ.get("RENDER_SERVICE_ID")),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True},
        MAX_CONTENT_LENGTH=10 * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "true").lower() != "false",
        PERMANENT_SESSION_LIFETIME=60 * 60 * 8,
        WTF_CSRF_TIME_LIMIT=60 * 60 * 4,
        MAIL_HOST=os.environ.get("MAIL_HOST", ""),
        MAIL_PORT=int(os.environ.get("MAIL_PORT", "587")),
        MAIL_USERNAME=os.environ.get("MAIL_USERNAME", ""),
        MAIL_PASSWORD=os.environ.get("MAIL_PASSWORD", ""),
        MAIL_FROM=os.environ.get("MAIL_FROM", ""),
        MAIL_USE_TLS=os.environ.get("MAIL_USE_TLS", "true").lower() != "false",
    )
    if test_config:
        app.config.update(test_config)
    app.logger.setLevel(logging.INFO)
    @app.context_processor
    def inject_storage_state():
        return {"storage_temporary": app.config["STORAGE_TEMPORARY"]}
    db.init_app(app)
    csrf.init_app(app)

    app.extensions["db_health"] = {"checked": 0.0, "ready": False}

    @app.before_request
    def ensure_schema():
        health = app.extensions["db_health"]
        if health["ready"] or time.monotonic() - health["checked"] < 30:
            return None
        health["checked"] = time.monotonic()
        try:
            with app.app_context():
                db.create_all()
            health["ready"] = True
        except SQLAlchemyError:
            app.logger.exception("Database unavailable; core resume analysis remains online")
            health["ready"] = False

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault("Content-Security-Policy", "default-src 'self'; style-src 'self' https://fonts.googleapis.com https://cdnjs.cloudflare.com 'unsafe-inline'; font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; script-src 'self'; img-src 'self' data:; form-action 'self'; frame-ancestors 'none'")
        return response

    @app.get("/health")
    def health():
        db_status = "not-connected" if not app.extensions["db_health"]["ready"] else (
            "postgresql" if app.config["STORAGE_PERSISTENT"] else "sqlite-temporary" if app.config["STORAGE_TEMPORARY"] else "sqlite-local")
        return jsonify({"status": "ok", "database": db_status})

    @app.get("/")
    def home():
        return render_template("index.html")

    @app.errorhandler(413)
    def request_entity_too_large(_error):
        return render_template("error.html", message="Files must be 10 MB or smaller."), 413

    @app.errorhandler(400)
    def bad_request(error):
        if request.path.startswith("/api/"):
            return jsonify(error="Invalid request. Refresh the page and try again."), 400
        return render_template("error.html", message="Invalid or expired form. Refresh the page and try again."), 400

    @app.errorhandler(SQLAlchemyError)
    def database_error(_error):
        db.session.rollback()
        app.logger.exception("Database operation failed")
        return render_template("error.html", message="Account storage is temporarily unavailable. Resume analysis still works; please try again later."), 503

    from views.auth import auth
    from views.candidate import candidate
    from views.recruiter import recruiter
    from views.admin import admin
    app.register_blueprint(auth)
    app.register_blueprint(candidate)
    app.register_blueprint(recruiter)
    app.register_blueprint(admin)

    @app.cli.command("create-admin")
    @click.option("--email", prompt=True)
    @click.option("--name", prompt="Administrator name")
    def create_admin(email, name):
        """Create the first admin account from a trusted server shell."""
        password = click.prompt("Administrator password (12+ characters)", hide_input=True, confirmation_prompt=True)
        if len(password) < 12:
            raise click.ClickException("Password must be at least 12 characters.")
        db.create_all()
        email = email.strip().lower()
        if User.query.filter_by(email=email).first():
            raise click.ClickException("An account with that email already exists.")
        user = User(name=name.strip(), email=email, password_hash=generate_password_hash(password), role="admin")
        db.session.add(user)
        db.session.commit()
        click.echo("Administrator account created.")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
