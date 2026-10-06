import os
import psycopg2


def get_connection():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        return None
    return psycopg2.connect(database_url)


def save_resume(filename, ats_score):

    conn = get_connection()
    if conn is None:
        return

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
    if conn is None:
        return []

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
