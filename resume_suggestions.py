def generate_resume_suggestions(
        ats_score,
        skills,
        missing_skills,
        resume_text
):

    suggestions = []


    # ATS Score Analysis

    if ats_score < 60:

        suggestions.append(
            "⚠ Your ATS score is low. Add more job-related keywords and improve resume structure."
        )

    elif ats_score < 80:

        suggestions.append(
            "Your ATS score is moderate. Add more relevant skills and improve keyword matching."
        )

    else:

        suggestions.append(
            "Your ATS compatibility is good. Keep maintaining a clear and structured resume."
        )



    # Skill Analysis

    if len(skills) < 5:

        suggestions.append(
            "Add more technical skills related to your target job role."
        )

    else:

        suggestions.append(
            "Your technical skill section is good. Keep updating it with new technologies."
        )



    # Missing Skills Analysis

    if missing_skills:

        missing_names = []

        for item in missing_skills:

            if isinstance(item, dict):

                missing_names.append(
                    item["skill"]
                )

            else:

                missing_names.append(
                    item
                )


        suggestions.append(
            "You should improve these missing skills: "
            + ", ".join(missing_names)
            + "."
        )

    else:

        suggestions.append(
            "No major skill gaps detected for the matched job role."
        )



    # Resume Content Analysis

    resume_lower = resume_text.lower()


    if "project" not in resume_lower:

        suggestions.append(
            "Add practical projects with technologies used and measurable outcomes."
        )


    if "certification" not in resume_lower:

        suggestions.append(
            "Adding relevant certifications can improve your resume credibility."
        )


    if "github" not in resume_lower:

        suggestions.append(
            "Add your GitHub profile to showcase coding projects."
        )


    return suggestions