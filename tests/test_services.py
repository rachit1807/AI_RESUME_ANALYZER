from recruitment_services import analyze_text, evaluate_answer, interview_questions, learning_recommendations, make_cover_letter, rewrite_resume
from reporting import make_pdf


def test_analysis_reports_score_skills_and_role_gaps():
    result = analyze_text("Python Flask SQL project experience", "Python SQL Docker engineer")
    assert 0 <= result["ats_score"] <= 100
    assert 0 <= result["match_score"] <= 100
    assert "python" in result["matched_skills"]
    assert "docker" in result["missing_skills"]


def test_rewriter_is_conservative_and_does_not_make_up_metrics():
    result = rewrite_resume("worked on Python APIs\nhelped with testing")
    assert "Contributed to Python APIs." in result
    assert "Supported with testing." in result
    assert "100%" not in result


def test_learning_links_questions_and_cover_letter_are_created():
    resources = learning_recommendations(["docker"])
    assert resources[0]["documentation"].startswith("https://")
    assert "Docker" in resources[0]["project"]
    questions = interview_questions("Backend Engineer", "Python, SQL", "Job board API", "REST API")
    assert set(questions) == {"Technical", "Behavioral", "HR"}
    letter = make_cover_letter("Rae", "Python SQL", "Engineer", "Acme", "Python SQL")
    assert "Acme" in letter and "Engineer" in letter


def test_mock_interview_feedback_and_pdf_export():
    score, feedback = evaluate_answer("I built a project with my team because it improved the result and impact for the users.")
    assert 20 <= score <= 100
    assert feedback
    pdf = make_pdf("Report", "Resume score: 80%")
    assert pdf.startswith(b"%PDF-")
