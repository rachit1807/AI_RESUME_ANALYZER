# AI Resume Analyzer & Career Development Platform

**Live analyzer:** [ai-resume-analyzer-rachit.onrender.com](https://ai-resume-analyzer-rachit.onrender.com/)

A Flask career platform for resume analysis, candidate career tools, recruiter job management, and candidate matching. It extends the original PDF analyzer while keeping `/`, `/upload`, the legacy PostgreSQL helpers, and the existing `resumes` and `jobs` tables available.

> **Scoring and generation:** This project runs without paid AI APIs. Matching uses TF-IDF, cosine similarity, and a finite skills catalogue. Resume editing, cover letters, learning guidance, interview prompts, and mock interview feedback use deterministic templates and heuristics. They are drafts and practice aids, not generative AI, verified salary data, hiring recommendations, or employment decisions. Review all output and use only accurate details.

## Features

### Resume analysis

- Upload a text-based PDF (10 MB maximum); PDF bytes are parsed in memory and discarded after the request.
- Get an ATS-style completeness score, skill detection, job-text similarity, missing skills, and concrete suggestions.
- Compare one resume with up to ten roles side by side. Matching is an estimate and only recognizes the built-in skills catalogue.
- Signed-in candidates may save extracted resume text and analysis history. Resume versions can be compared by score and deleted.

### Candidate workspace

- Candidate registration, sign-in, profile, application tracking, saved jobs, resume history, and analysis history.
- Resume builder with Classic, Modern, and Compact previews and PDF downloads.
- Conservative resume rewriter. It improves wording but does not invent experience, keywords, or achievements.
- Role-specific cover letter drafts based on profile and saved resume text; downloadable as PDF.
- Free learning resources, documentation, YouTube search links, project prompts, and a six-week career plan for recognized skill gaps.
- LinkedIn headline, About, and skills suggestions based on entered resume text.
- Technical, behavioral, and HR interview prompts; mock answers receive local rubric feedback. Mock answers are not stored.
- Download analysis, resume, and cover letter PDFs; email those reports only after a signed-in user submits the recipient address and only when SMTP is configured.

### Recruiter and company portal

- Recruiters create a company account, publish and pause roles, review applicants, filter and search candidates, shortlist or reject, and export CSV reports.
- Candidate match estimates are saved on applications to support applicant sorting.
- Recruiters may rank up to 25 PDF resumes against one role at a time. The files and extracted text are processed in memory; only the original filename and score/skill summaries are stored for the ranking report. The ranking batch can be exported as CSV.
- Recruiter access is scoped to the recruiter's company. Admins can pause any company listing.

### Admin and security

- Admin dashboard for user access, recruiter/company/job oversight, aggregate analytics, and recent audit activity.
- Passwords use Werkzeug's password hashing. Forms use CSRF tokens, sessions use HTTP-only/SameSite cookies, request size and field limits are enforced, and uploads are checked for PDF signatures.
- ORM parameter binding protects database operations from SQL injection. User role checks and record ownership checks protect candidate, recruiter, and admin pages.
- Security headers are set by default. Do not disable cookie security in production.

## Local setup

Python 3.10 or newer is recommended.

```bash
git clone https://github.com/rachit1807/AI_RESUME_ANALYZER.git
cd AI_RESUME_ANALYZER
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
```

Without `DATABASE_URL`, the app uses SQLite under `instance/` for local development. For PostgreSQL, set `DATABASE_URL` to a private connection URL. Set a long, random `SESSION_SECRET` and set `COOKIE_SECURE=false` only for local HTTP development. Copy `.env.example` to `.env` if you load environment variables with your preferred local tool; the app intentionally does not load `.env` automatically.

```bash
export SESSION_SECRET="replace-with-a-long-random-secret"
export COOKIE_SECURE=false
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000). A durable PostgreSQL database is required for production account, resume, job, and report persistence. SQLite is a convenient local fallback; its data is not durable on Render's ephemeral filesystem.

### Create an administrator

Public registration only permits candidate and recruiter accounts. From a trusted shell connected to the configured database, run:

```bash
flask --app app create-admin
```

The command prompts for an email, display name, and password (12 characters minimum). Avoid passing passwords in shell command arguments or deployment logs.

### Optional email delivery

PDF downloads work without email configuration. To enable report email, configure all of these server-side environment variables with an SMTP account:

| Variable | Purpose |
| --- | --- |
| `MAIL_HOST` | SMTP host |
| `MAIL_PORT` | SMTP port (default `587`) |
| `MAIL_USERNAME` | SMTP login |
| `MAIL_PASSWORD` | SMTP password or application password |
| `MAIL_FROM` | Approved sender address |
| `MAIL_USE_TLS` | Use STARTTLS (default `true`) |

Never put SMTP credentials in GitHub or a client-side file.

## Database and backward compatibility

The app creates the new tables on startup using SQLAlchemy. The definitions are also documented in [`database.sql`](database.sql). New recruiter jobs use a separate `recruiter_jobs` table so a previous installation's `jobs(job_title, job_description)` table remains intact. Existing `resumes(filename, ats_score)` rows are not changed. The original analyzer continues to work without a database; account-backed pages return a service-unavailable response if the configured PostgreSQL service is down.

For production, attach a PostgreSQL database to the Render web service and set `DATABASE_URL` using Render's **internal** database URL. Also set `SESSION_SECRET` to a stable random value so sessions remain valid across instances and deploys. The code understands Render's `postgres://` URL form. Database backups and retention are the operator's responsibility.

## Deploy on Render

The existing Render Web Service is connected to the `main` branch. It uses:

| Setting | Value |
| --- | --- |
| Build command | `pip install -r requirements.txt` |
| Start command | `gunicorn --preload app:app` |
| Required for durable accounts | PostgreSQL `DATABASE_URL`, stable `SESSION_SECRET` |
| Optional | SMTP variables above |

The existing live URL remains the analyzer URL above. New tables are created at app startup; legacy tables are left in place. Render's free web service may sleep while idle. A free ephemeral filesystem does not preserve SQLite across restarts, so configure PostgreSQL before relying on account or recruiter history in production.

Health check: [`/health`](https://ai-resume-analyzer-rachit.onrender.com/health).

## Run checks

Install development dependencies, then run the test suite:

```bash
python -m pip install -r requirements-dev.txt
pytest
```

The tests use isolated SQLite databases and do not send email or call external AI services.

## Project structure

```text
app.py                    Flask app factory, security settings, health check, admin CLI
models.py                 PostgreSQL/SQLite models for users, jobs, history, applications
views/                    Auth, candidate, recruiter, and admin route blueprints
recruitment_services.py   Offline matching, rewriting, career and interview helpers
reporting.py              PDF creation and optional SMTP report delivery
ats_score.py              Original ATS-style completeness heuristic
database.py               Legacy optional PostgreSQL helpers
database.sql              Additive SQL schema reference for new platform tables
resume_parser.py          In-memory PDF text extraction
resume_suggestions.py     Resume improvement guidance
templates/                Responsive Jinja views
static/style.css          Accessible responsive design system
requirements.txt          Runtime dependencies
tests/                    Automated service and route tests
```

## Privacy and limitations

- Anonymous analyzer requests do not persist the extracted resume text. If you are signed in, the extracted text is saved to your account for version history and reports; delete a version in your dashboard to remove its linked analyses.
- Bulk recruiter uploads are parsed in memory. The batch retains filenames and summary scores, not the original PDF or extracted text.
- This release does not OCR image-only PDFs. It does not call a hosted language model, produce market salary estimates, verify education/work history, or make an employment decision.
- The ATS score is a transparent heuristic. A missing-skill result only covers supported catalogue items; validate role requirements yourself.
- User registration, resume history, and recruiter workflows require database persistence. Configure PostgreSQL before production use; Render's local filesystem is ephemeral.
- Email report delivery is disabled until SMTP is configured. When enabled, a signed-in user's explicit action is required; the destination address and report type are recorded in the user's account.

## License

No license file is currently included. Contact the repository owner before redistributing or reusing this project.
