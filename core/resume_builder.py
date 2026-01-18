# core/resume_builder.py

from core.career_store import load_career


def generate_resume_text():
    """
    Build a clean text resume from career profile data.
    """
    data = load_career()

    profile = data.get("profile", {})
    education = data.get("education", [])
    work = data.get("work", [])
    skills = data.get("skills", [])

    lines = []

    # -------------------------
    # HEADER
    # -------------------------
    name = profile.get("name", "Your Name")
    headline = profile.get("headline", "Professional")

    lines.append(name.upper())
    lines.append(headline)
    lines.append("")

    # -------------------------
    # SUMMARY
    # -------------------------
    summary = profile.get("summary")
    if summary:
        lines.append("SUMMARY")
        lines.append(summary)
        lines.append("")

    # -------------------------
    # EXPERIENCE
    # -------------------------
    if work:
        lines.append("EXPERIENCE")

        for w in sorted(work, key=lambda x: x.get("start_year", 0), reverse=True):
            title = w.get("role", "Role")
            company = w.get("company", "Company")
            start = w.get("start_year", "")
            end = w.get("end_year", "Present")
            notes = w.get("notes", "")

            lines.append(f"{company} — {title}")
            lines.append(f"{start} – {end}")

            if notes:
                for bullet in notes.split("\n"):
                    lines.append(f"• {bullet.strip()}")

            lines.append("")

    # -------------------------
    # EDUCATION
    # -------------------------
    if education:
        lines.append("EDUCATION")

        for e in sorted(education, key=lambda x: x.get("start_year", 0), reverse=True):
            degree = e.get("degree", "")
            institution = e.get("institution", "")
            start = e.get("start_year", "")
            end = e.get("end_year", "")

            lines.append(f"{degree} — {institution}")
            lines.append(f"{start} – {end}")
            lines.append("")

    # -------------------------
    # SKILLS
    # -------------------------
    if skills:
        lines.append("SKILLS")
        skill_names = [s.get("name") for s in skills if s.get("name")]
        lines.append(", ".join(skill_names))
        lines.append("")

    return "\n".join(lines)
