# AI Resume Analyzer

Analyze a text-based PDF resume against a job description. The app calculates a heuristic ATS-style score, finds supported skills, compares resume and role keywords, highlights selected skill gaps, and offers practical suggestions.

> **Live app:** [ai-resume-analyzer-rachit.onrender.com](https://ai-resume-analyzer-rachit.onrender.com/)

## What it does

- Accepts PDF resumes up to 10 MB.
- Extracts selectable text from the PDF in memory.
- Calculates an ATS-style score from contact details, education, resume sections, and a built-in technical skills list.
- Compares resume text with a pasted job description using TF-IDF similarity and keyword overlap.
- Lists detected skills and selected missing skills from the role description, with learning guidance.
- Produces rule-based resume improvement suggestions.
- Works without a database or paid AI API key.

## How the analysis works

The project uses scikit-learn's TF-IDF vectorizer and cosine similarity for text matching, plus hand-written rules for ATS scoring, skill detection, and feedback. It does **not** call a hosted generative AI model, and its score is an informational heuristic—not a hiring decision or a guarantee of ATS results.

For the most useful comparison, paste the target role's job description along with the resume. The current skill-gap catalogue covers a defined set of common technical skills, so it may not identify every requirement in a role.

## Privacy and file handling

Resume PDFs are read and analyzed in memory; the app does not save the uploaded PDF to disk. If a `DATABASE_URL` is configured, the optional logging code records the uploaded filename and ATS score in the `resumes` table. Without that variable, analysis works without database logging. Avoid uploading documents you do not have permission to process.

## Technology

- Python and Flask
- pdfplumber for PDF text extraction
- scikit-learn for TF-IDF and cosine similarity
- PostgreSQL support for optional score logging and stored job listings
- Jinja templates and CSS
- Gunicorn for production serving

## Run locally

1. Clone the repository and open its folder:

   ```bash
   git clone https://github.com/rachit1807/AI_RESUME_ANALYZER.git
   cd AI_RESUME_ANALYZER
   ```

2. Create and activate a virtual environment (recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate       # macOS / Linux
   # .venv\Scripts\activate       # Windows PowerShell
   ```

3. Install dependencies and start Flask:

   ```bash
   python -m pip install -r requirements.txt
   python app.py
   ```

4. Open [http://127.0.0.1:5000](http://127.0.0.1:5000), choose a text-based PDF, paste a job description, and select **Analyze Resume**.

## Deploy on Render

The live site is deployed as a Render Web Service connected to the `main` branch of this repository. To create another deployment, create a Web Service from the repository and use:

| Setting | Value |
| --- | --- |
| Build command | `pip install -r requirements.txt` |
| Start command | `gunicorn app:app` |
| Instance | Free |

No environment variables or database are required for the core analyzer. Render's free service can spin down when idle, so its first request after inactivity may take around a minute to respond.

## Project layout

```text
.
├── app.py                    # Flask routes and upload handling
├── ats_score.py              # ATS-style heuristic score and skill extraction
├── job_match.py              # TF-IDF and keyword-based job matching
├── skill_gap.py              # Skill gap detection and learning guidance
├── resume_parser.py          # PDF text extraction
├── resume_suggestions.py     # Rule-based improvement suggestions
├── database.py               # Optional PostgreSQL access
├── database.sql              # Database setup placeholder
├── templates/
│   ├── index.html             # Upload form
│   └── result.html            # Analysis results
├── static/style.css           # App styles
├── requirements.txt           # Python dependencies
└── Procfile                   # Production start command
```

## Known limitations

- Scanned PDFs without selectable text are not OCR processed.
- ATS scores and feedback are rule-based approximations; review the resume yourself before relying on them.
- Job and skill matching depends on text overlap and the built-in skill vocabulary.
- The current web service has no user accounts or saved analysis history.

## License

No license file is currently included. Contact the repository owner before redistributing or reusing this project.
