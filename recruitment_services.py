"""Local, deterministic helpers: no paid model or external API is called."""
import re
from urllib.parse import quote_plus

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ats_score import calculate_ats_score

SKILL_RESOURCES = {
    "python": ("Python Tutorial", "https://docs.python.org/3/tutorial/", "https://www.youtube.com/results?search_query=python+full+course"),
    "javascript": ("JavaScript Guide", "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide", "https://www.youtube.com/results?search_query=javascript+full+course"),
    "sql": ("SQL Tutorial", "https://www.postgresql.org/docs/current/tutorial.html", "https://www.youtube.com/results?search_query=sql+course"),
    "react": ("React Learn", "https://react.dev/learn", "https://www.youtube.com/results?search_query=react+course"),
    "flask": ("Flask Documentation", "https://flask.palletsprojects.com/en/stable/tutorial/", "https://www.youtube.com/results?search_query=flask+project+tutorial"),
    "django": ("Django Tutorial", "https://docs.djangoproject.com/en/stable/intro/tutorial01/", "https://www.youtube.com/results?search_query=django+course"),
    "machine learning": ("scikit-learn MOOC", "https://inria.github.io/scikit-learn-mooc/", "https://www.youtube.com/results?search_query=machine+learning+course"),
    "docker": ("Docker Get Started", "https://docs.docker.com/get-started/", "https://www.youtube.com/results?search_query=docker+course"),
    "aws": ("AWS Skill Builder", "https://skillbuilder.aws/", "https://www.youtube.com/results?search_query=aws+cloud+practitioner+course"),
    "git": ("Git Book", "https://git-scm.com/book/en/v2", "https://www.youtube.com/results?search_query=git+github+course"),
    "html": ("MDN HTML", "https://developer.mozilla.org/en-US/docs/Learn/HTML", "https://www.youtube.com/results?search_query=html+course"),
    "css": ("MDN CSS", "https://developer.mozilla.org/en-US/docs/Learn/CSS", "https://www.youtube.com/results?search_query=css+course"),
    "java": ("Dev.java", "https://dev.java/learn/", "https://www.youtube.com/results?search_query=java+course"),
    "postgresql": ("PostgreSQL Tutorial", "https://www.postgresql.org/docs/current/tutorial.html", "https://www.youtube.com/results?search_query=postgresql+course"),
    "pandas": ("Pandas Getting Started", "https://pandas.pydata.org/docs/getting_started/index.html", "https://www.youtube.com/results?search_query=pandas+course"),
    "numpy": ("NumPy Learn", "https://numpy.org/learn/", "https://www.youtube.com/results?search_query=numpy+course"),
    "tensorflow": ("TensorFlow Tutorials", "https://www.tensorflow.org/tutorials", "https://www.youtube.com/results?search_query=tensorflow+course"),
    "c++": ("Learn C++", "https://www.learncpp.com/", "https://www.youtube.com/results?search_query=c%2B%2B+course"),
    "linux": ("Linux Journey", "https://linuxjourney.com/", "https://www.youtube.com/results?search_query=linux+course"),
    "rest api": ("MDN HTTP", "https://developer.mozilla.org/en-US/docs/Web/HTTP", "https://www.youtube.com/results?search_query=rest+api+course"),
    "node.js": ("Node.js Learn", "https://nodejs.org/en/learn", "https://www.youtube.com/results?search_query=nodejs+course"),
}


def analyze_text(resume_text, job_description):
    score, skills = calculate_ats_score(resume_text)
    lower_resume = resume_text.casefold()
    lower_job = job_description.casefold()
    missing = [skill for skill in SKILL_RESOURCES if skill in lower_job and skill not in lower_resume]
    docs = [resume_text or "resume", job_description or "role"]
    try:
        matrix = TfidfVectorizer(stop_words="english").fit_transform(docs)
        similarity = round(float(cosine_similarity(matrix[0:1], matrix[1:])[0][0]) * 100, 1)
    except ValueError:
        similarity = 0.0
    role_skills = [skill for skill in SKILL_RESOURCES if skill in lower_job]
    matched = [skill for skill in role_skills if skill not in missing]
    # ATS is intentionally a transparent heuristic, not a hiring decision.
    role_score = round((similarity * 0.4) + (100 * len(matched) / len(role_skills) * 0.6 if role_skills else similarity * 0.6))
    return {"ats_score": score, "match_score": min(100, role_score), "similarity": similarity,
            "skills": skills, "matched_skills": matched, "missing_skills": missing}


def learning_recommendations(missing_skills):
    items = []
    for skill in missing_skills:
        label, docs, videos = SKILL_RESOURCES.get(skill, (f"Search learning resources for {skill}", "https://developer.mozilla.org/", ""))
        items.append({"skill": skill, "course": label, "documentation": docs,
                      "youtube": videos or f"https://www.youtube.com/results?search_query={quote_plus(skill + ' course')}",
                      "project": f"Build a small portfolio project that demonstrates {skill.title()}, includes a README, and has one measurable outcome."})
    return items


def rewrite_resume(text):
    """Make conservative copy edits and never invent metrics or qualifications."""
    output = []
    substitutions = ((r"\bworked on\b", "Contributed to"), (r"\bhelped\b", "Supported"),
                     (r"\bmade\b", "Created"), (r"\bdid\b", "Delivered"),
                     (r"\bused\b", "Applied"), (r"\bresponsible for\b", "Managed"))
    for raw in text.splitlines():
        line = raw.strip(" •-*\t")
        if not line:
            continue
        sentence = line[0].upper() + line[1:]
        for pattern, replacement in substitutions:
            sentence = re.sub(pattern, replacement, sentence, flags=re.IGNORECASE)
        if sentence[-1:] not in ".!?":
            sentence += "."
        output.append(sentence)
    return "\n".join(output) or "Add a concise, fact-based summary of your impact and the tools you used."


def make_cover_letter(name, resume_text, job_title, company, job_description):
    name = name.strip() or "Candidate"
    company = company.strip() or "the team"
    title = job_title.strip() or "the open position"
    skills = [s for s in SKILL_RESOURCES if s in resume_text.casefold() and s in job_description.casefold()][:5]
    evidence = ", ".join(skills) if skills else "the experience and projects described in my resume"
    return (f"Dear Hiring Team at {company},\n\n"
            f"I am applying for the {title} role. My background includes {evidence}, which aligns with the needs described for this position. "
            "I would welcome the opportunity to explain how my experience can contribute to your team.\n\n"
            "Thank you for your consideration. I look forward to discussing the role and the work your team is doing.\n\n"
            f"Sincerely,\n{name}")


def interview_questions(role, skills, projects, description):
    skills = [item.strip() for item in re.split(r"[,\n]", skills) if item.strip()][:8]
    projects = projects.strip()[:250]
    role = role.strip() or "this role"
    technical = [f"How have you used {skill} to solve a practical problem? What trade-offs did you make?" for skill in skills[:4]]
    if not technical:
        technical = [f"Walk me through a technical problem relevant to {role} and how you would approach it."]
    if projects:
        technical.insert(0, f"Describe the project '{projects}'. What was your specific contribution and what would you improve?")
    if description.strip():
        technical.append("Which requirement in the job description best matches your experience? Give a specific example.")
    return {"Technical": technical[:6],
            "Behavioral": ["Tell me about a difficult problem you owned from start to finish.", "Describe a time you received feedback and changed your approach."],
            "HR": [f"Why are you interested in {role}?", "What kind of team helps you do your best work?"]}


def evaluate_answer(answer):
    words = re.findall(r"\b[\w+#.]+\b", answer)
    lower = answer.casefold()
    evidence = sum(bool(token in lower) for token in ("because", "result", "impact", "learned", "built", "measured", "team"))
    score = min(100, max(20, round(min(len(words) / 1.2, 55) + evidence * 6)))
    feedback = []
    if len(words) < 35:
        feedback.append("Add more detail: explain the situation, your actions, and the result.")
    if not any(token in lower for token in ("result", "impact", "improved", "reduced", "increased")):
        feedback.append("State the outcome or impact; use a real number only if you can support it.")
    if not feedback:
        feedback.append("Good structure. Make your personal contribution and the outcome easy to identify.")
    return score, " ".join(feedback)
