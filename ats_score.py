import re

skills = [
    "python", "java", "c++", "html", "css", "javascript",
    "sql", "flask", "django", "react", "machine learning",
    "tensorflow", "pandas", "numpy", "git", "postgresql"
]

education_keywords = [
    "b.tech", "btech", "bachelor", "master", "m.tech",
    "mtech", "degree"
]


def calculate_ats_score(resume_text):

    text = resume_text.lower()

    score = 0

    found_skills = []

    # Contact Information
    email = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", resume_text)

    phone = re.search(r"\d{10}", resume_text)

    if email:
        score += 10

    if phone:
        score += 10

    # Skills
    for skill in skills:

        if skill in text:
            score += 4
            found_skills.append(skill)

    # Education
    for edu in education_keywords:

        if edu in text:
            score += 10
            break

    # Projects
    if "project" in text:
        score += 10

    # Experience
    if "experience" in text or "internship" in text:
        score += 10

    # Certifications
    if "certification" in text or "certificate" in text:
        score += 10

    if score > 100:
        score = 100

    return score, found_skills