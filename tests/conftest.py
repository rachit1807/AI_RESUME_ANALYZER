from io import BytesIO

import pytest
from reportlab.pdfgen import canvas

from app import create_app
from models import db


@pytest.fixture
def app(tmp_path):
    application = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-only-session-secret",
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.sqlite3'}",
        "SESSION_COOKIE_SECURE": False,
        "WTF_CSRF_ENABLED": False,
    })
    with application.app_context():
        db.drop_all()
        db.create_all()
    yield application
    with application.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def resume_pdf():
    output = BytesIO()
    document = canvas.Canvas(output)
    document.drawString(72, 740, "Taylor Sample")
    document.drawString(72, 720, "taylor@example.com | 5551234567")
    document.drawString(72, 700, "Education: Bachelor degree. Experience and internship.")
    document.drawString(72, 680, "Projects: Python Flask REST API, SQL, PostgreSQL and Docker.")
    document.drawString(72, 660, "Skills: Python, Flask, SQL, PostgreSQL, Docker, JavaScript, Git.")
    document.save()
    return output.getvalue()


def register(client, email, role="candidate", company=""):
    return client.post("/register", data={
        "name": "Test User", "email": email, "password": "VeryStrongPassword123",
        "role": role, "company": company,
    }, follow_redirects=True)
