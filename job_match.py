from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from database import get_jobs


def calculate_skill_score(resume_text, job_description):

    resume_text = resume_text.lower()
    job_description = job_description.lower()


    skills = [
        "python",
        "java",
        "sql",
        "flask",
        "django",
        "react",
        "javascript",
        "html",
        "css",
        "git",
        "machine learning",
        "tensorflow",
        "pandas",
        "numpy",
        "docker",
        "aws",
        "rest api",
        "node.js",
        "mongodb",
        "spring boot",
        "c++",
        "linux"
    ]


    required_skills = []

    matched_skills = 0


    for skill in skills:

        if skill in job_description:

            required_skills.append(skill)


            if skill in resume_text:

                matched_skills += 1



    if len(required_skills) == 0:

        return 0



    return (matched_skills / len(required_skills)) * 100





def match_jobs(resume_text):


    jobs = get_jobs()


    if not jobs:

        return []



    documents = [resume_text]


    for job in jobs:

        documents.append(job[1])



    vectorizer = TfidfVectorizer(
        stop_words="english"
    )


    matrix = vectorizer.fit_transform(documents)



    similarity = cosine_similarity(
        matrix[0:1],
        matrix[1:]
    )[0]



    results = []



    for i, job in enumerate(jobs):


        tfidf_score = similarity[i] * 100



        skill_score = calculate_skill_score(
            resume_text,
            job[1]
        )



        final_score = (
            (tfidf_score * 0.4) +
            (skill_score * 0.6)
        )



        results.append({

            "job": job[0],

            "score": round(
                final_score,
                2
            )

        })



    results = sorted(
        results,
        key=lambda x: x["score"],
        reverse=True
    )


    return results[:5]