from flask import Flask, render_template, request
import os

from resume_parser import extract_text
from ats_score import calculate_ats_score
from job_match import match_jobs
from skill_gap import find_missing_skills
from database import save_resume
from resume_suggestions import generate_resume_suggestions


app = Flask(__name__)


UPLOAD_FOLDER = "uploads"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route("/")
def home():

    return render_template("index.html")



@app.route("/upload", methods=["POST"])
def upload_resume():


    file = request.files["resume"]


    if not file:

        return "No file uploaded"



    filepath = os.path.join(
        app.config["UPLOAD_FOLDER"],
        file.filename
    )


    file.save(filepath)



    resume_text = extract_text(filepath)



    ats_score, skills = calculate_ats_score(
        resume_text
    )



    jobs = match_jobs(
        resume_text
    )



    if jobs:

        top_job = jobs[0]["job"]

        missing_skills = find_missing_skills(
            resume_text,
            top_job
        )


    else:

        missing_skills = []



    suggestions = generate_resume_suggestions(
        ats_score,
        skills,
        missing_skills,
        resume_text
    )



    save_resume(
        file.filename,
        ats_score
    )



    return render_template(
        "result.html",
        ats_score=ats_score,
        skills=skills,
        jobs=jobs,
        missing_skills=missing_skills,
        suggestions=suggestions
    )



if __name__ == "__main__":

    app.run(debug=True)