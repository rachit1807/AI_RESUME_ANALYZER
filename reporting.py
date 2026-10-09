"""PDF and optional SMTP helpers shared by candidate and recruiter reports."""
from email.message import EmailMessage
from html import escape
from io import BytesIO
import smtplib

from flask import current_app
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def make_pdf(title, body, theme="classic"):
    output = BytesIO()
    document = SimpleDocTemplate(output, pagesize=letter, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54)
    styles = getSampleStyleSheet()
    if theme == "modern":
        styles["Title"].textColor = colors.HexColor("#176b62")
        styles["Title"].fontName = "Helvetica-Bold"
    elif theme == "compact":
        styles["Title"].fontSize = 18
        styles["BodyText"].fontSize = 9
        styles["BodyText"].leading = 12
    blocks = [Paragraph(escape(title), styles["Title"]), Spacer(1, 16)]
    for paragraph in body.split("\n"):
        if paragraph.strip():
            blocks.append(Paragraph(escape(paragraph), styles["BodyText"]))
            blocks.append(Spacer(1, 7))
        else:
            blocks.append(Spacer(1, 8))
    document.build(blocks)
    return output.getvalue()


def send_email(recipient, subject, body, attachment_name=None, attachment=None):
    config = current_app.config
    if not all((config.get("MAIL_HOST"), config.get("MAIL_FROM"), config.get("MAIL_USERNAME"), config.get("MAIL_PASSWORD"))):
        raise RuntimeError("Email is not configured. Set the SMTP environment variables first.")
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = config["MAIL_FROM"]
    message["To"] = recipient
    message.set_content(body)
    if attachment is not None and attachment_name:
        message.add_attachment(attachment, maintype="application", subtype="pdf", filename=attachment_name)
    with smtplib.SMTP(config["MAIL_HOST"], config["MAIL_PORT"], timeout=15) as server:
        if config.get("MAIL_USE_TLS"):
            server.starttls()
        server.login(config["MAIL_USERNAME"], config["MAIL_PASSWORD"])
        server.send_message(message)
