from flask import Flask, render_template, request

from resume_parser import extract_text
from ats_score import calculate_ats_score
from job_match import match_jobs
from skill_gap import find_missing_skills
from database import save_resume
from resume_suggestions import generate_resume_suggestions


app = Flask(__name__)


app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024


@app.route("/")
def home():

    return render_template("index.html")



@app.route("/upload", methods=["POST"])
def upload_resume():


    file = request.files.get("resume")
    if not file or not file.filename:
        return "Please choose a resume PDF.", 400
    if not file.filename.lower().endswith(".pdf"):
        return "Please upload a PDF file.", 400

    try:
        resume_text = extract_text(file.read())
    except Exception:
        return "We couldn’t read that PDF. Please try another file.", 400
    if not resume_text.strip():
        return "No selectable text was found in this PDF. Please upload a text-based PDF.", 400



    ats_score, skills = calculate_ats_score(
        resume_text
    )



    job_description = request.form.get("job_description", "").strip()
    jobs = match_jobs(resume_text, job_description)



    if jobs:

        top_job = jobs[0]["job"]

        missing_skills = find_missing_skills(resume_text, top_job, job_description or None)


    else:

        missing_skills = []



    suggestions = generate_resume_suggestions(
        ats_score,
        skills,
        missing_skills,
        resume_text
    )



    try:
        save_resume(file.filename, ats_score)
    except Exception:
        # Analysis remains available when optional database logging is not configured.
        app.logger.exception("Resume analysis logging failed")



    return render_template(
        "result.html",
        ats_score=ats_score,
        skills=skills,
        jobs=jobs,
        missing_skills=missing_skills,
        suggestions=suggestions
    )


@app.errorhandler(413)
def request_entity_too_large(_error):
    return "PDF must be 10 MB or smaller.", 413



if __name__ == "__main__":

    app.run()
