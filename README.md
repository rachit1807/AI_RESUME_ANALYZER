# AI Resume Analyzer

A resume analysis web app that evaluates PDF resumes, calculates a heuristic ATS score, compares a resume with a pasted job description, identifies keyword skill gaps, and provides improvement suggestions. Matching uses TF-IDF and keyword overlap; it does not call a hosted generative AI service.

## Features

✅ Resume PDF Analysis  
✅ ATS Score Calculation  
✅ Skill Extraction  
✅ Job Description Matching
✅ Skill Gap Detection  
✅ Resume Improvement Suggestions  

## Tech Stack

- Python
- Flask
- PostgreSQL
- HTML/CSS
- Natural Language Processing (NLP)
- Scikit-learn
- TF-IDF & Cosine Similarity

## Run locally

```bash
python -m pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000` and upload a text-based PDF (up to 10 MB).

## Deploy on Render

Create a Render **Web Service** from this repository with:

- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`
- Instance type: Free

The app works without a database. If `DATABASE_URL` is configured, it can also read job listings from the `jobs` table and log scores to the `resumes` table. Uploaded PDF content is processed in memory and is not saved to disk.

Render's free web services can spin down when idle, so the first request after inactivity may take longer.

## How It Works

1. Upload Resume PDF
2. Extract resume information using NLP
3. Compare skills with job requirements
4. Generate ATS compatibility score
5. Suggest missing skills and improvements

## Project Structure
