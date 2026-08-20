from database import get_jobs


def find_missing_skills(
    resume_text,
    matched_job,
    job_description=None
):

    resume_text = resume_text.lower()


    # If user pasted Job Description,
    # use it instead of database description

    if job_description and job_description.strip() != "":

        required_skills = job_description.lower()

    else:

        jobs = get_jobs()

        required_skills = ""

        for job in jobs:

            if job[0] == matched_job:

                required_skills = job[1].lower()

                break



    skill_details = {

        "python": {
            "why": "Python is widely used for backend development, automation, and data applications.",
            "learn": "Practice Python projects, APIs, automation scripts, and problem solving."
        },

        "java": {
            "why": "Java is commonly required for enterprise software development.",
            "learn": "Learn Java OOP, collections, Spring Boot, and build applications."
        },

        "sql": {
            "why": "SQL is required for managing and analyzing databases.",
            "learn": "Practice queries, joins, normalization, and database projects."
        },

        "flask": {
            "why": "Flask is used for creating lightweight Python web applications.",
            "learn": "Build REST APIs and deploy Flask applications."
        },

        "django": {
            "why": "Django is a popular Python framework for web development.",
            "learn": "Learn Django models, views, authentication, and APIs."
        },

        "react": {
            "why": "React is widely used for modern frontend development.",
            "learn": "Learn components, hooks, state management, and build projects."
        },

        "javascript": {
            "why": "JavaScript is essential for interactive web applications.",
            "learn": "Practice DOM, ES6 features, and frontend projects."
        },

        "html": {
            "why": "HTML forms the structure of web applications.",
            "learn": "Improve semantic HTML and responsive layouts."
        },

        "css": {
            "why": "CSS is required for designing attractive user interfaces.",
            "learn": "Learn Flexbox, Grid, animations, and responsive design."
        },

        "git": {
            "why": "Git is used for version control in software teams.",
            "learn": "Practice Git commands and GitHub workflow."
        },

        "machine learning": {
            "why": "Machine Learning skills are required for AI-based roles.",
            "learn": "Learn algorithms, model training, and evaluation techniques."
        },

        "tensorflow": {
            "why": "TensorFlow is used for deep learning applications.",
            "learn": "Build neural network and deep learning projects."
        },

        "docker": {
            "why": "Docker helps in application deployment and DevOps workflows.",
            "learn": "Learn containers, images, and Docker deployment."
        },

        "aws": {
            "why": "AWS skills are important for cloud-based applications.",
            "learn": "Learn cloud basics, EC2, S3, and deployment."
        },

        "rest api": {
            "why": "REST APIs connect frontend applications with backend services.",
            "learn": "Build and consume APIs using Flask or other frameworks."
        }

    }



    missing_skills = []


    for skill, details in skill_details.items():

        if skill in required_skills and skill not in resume_text:

            missing_skills.append({

                "skill": skill,

                "why": details["why"],

                "learn": details["learn"]

            })


    return missing_skills