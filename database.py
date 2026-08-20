import psycopg2


def get_connection():
    return psycopg2.connect(
        host="localhost",
        database="ai_resume_analyzer",
        user="postgres",
        password="Rachit2509",
        port="5432"
    )


def save_resume(filename, ats_score):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO resumes(filename, ats_score)
        VALUES(%s,%s)
        """,
        (filename, ats_score)
    )

    conn.commit()

    cursor.close()
    conn.close()


def get_jobs():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT job_title, job_description
        FROM jobs
        """
    )

    jobs = cursor.fetchall()

    cursor.close()
    conn.close()

    return jobs