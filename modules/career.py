"""
Career UI — Vinya
Pure UI layer.
Reads & writes only through core.career_store.
"""

import streamlit as st
import pandas as pd
from datetime import date
from core.career_store import practice_streak, gentle_insight

from core.career_store import (
    practice_streak,
    gentle_insight,
    load_career,
    log_practice,
    weekly_growth_signal,
    weekly_logs,
    gentle_nudge,
    list_education,
    list_work,
    list_skills,
    add_education,
    delete_education,
    add_work,
    delete_work,
    add_skill,
    delete_skill,
    current_role,
)

from core.resume_builder import generate_resume_text
from core.resume_exporter import export_resume_pdf, export_resume_docx


# --------------------------------------------------
# UI STATE
# --------------------------------------------------
if "career_form_open" not in st.session_state:
    st.session_state.career_form_open = False


# ==================================================
# MAIN UI
# ==================================================
def render_career():
    st.subheader("🧠 Career Profile")

    # ==================================================
    # 📈 WEEKLY SIGNAL
    # ==================================================
    signal = weekly_growth_signal()
    nudge = gentle_nudge()

    status_color = {
        "GROWING": "🟢",
        "STABLE": "🟡",
        "STALLING": "🔴",
    }.get(signal["status"], "🟡")

    st.markdown("### 📈 Weekly Momentum")
    st.info(
        f"{status_color} **{signal['status']}** — {signal['message']}\n\n"
        f"⏱️ Minutes: **{signal['total_minutes']} mins**  |  "
        f"📅 Active days: **{signal['active_days']} days**"
    )

    st.markdown(f"🧭 **Next gentle action:** {nudge}")

    # ==================================================
    # ➕ LOG PRACTICE
    # ==================================================
    st.markdown("---")
    st.markdown("### ➕ Log Practice")

    with st.form("career_log_form", clear_on_submit=True):
        c1, c2 = st.columns(2)

        with c1:
            minutes = st.number_input(
                "Minutes *",
                min_value=5,
                step=5,
                value=30,
            )

        with c2:
            area = st.selectbox(
                "Area *",
                [
                    "Tech",
                    "System Design",
                    "Leadership",
                    "Communication",
                    "Finance",
                    "Health",
                    "Learning",
                    "Other",
                ],
            )

        note = st.text_input("Notes (optional)")
        entry_date = st.date_input("Date", value=date.today())

        submitted = st.form_submit_button("Save Practice")

        if submitted:
            try:
                log_practice(
                    minutes=int(minutes),
                    area=area,
                    note=note,
                    entry_date=entry_date,
                )
                st.success("✅ Practice logged")
                st.rerun()
            except Exception as e:
                st.error(str(e))

    st.caption(
        f"🔥 Streak: {practice_streak()} days   |   🎯 Focus: {signal.get('top_focus') or '—'}"
    )

    insight = gentle_insight()
    if insight:
        st.info(f"🧠 {insight}")

    # ==================================================
    # 📜 THIS WEEK LOGS
    # ==================================================
    st.markdown("---")
    st.markdown("### 📜 This Week Activity")

    logs = weekly_logs()

    if logs:
        rows = []
        for log in reversed(logs):
            rows.append({
                "Date": log.get("date"),
                "Minutes": log.get("minutes"),
                "Area": log.get("area"),
                "Note": log.get("note", ""),
            })

        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No practice logged this week yet.")

    # ==================================================
    # 📦 ALL-TIME SUMMARY
    # ==================================================
    st.markdown("---")
    st.markdown("### 📦 All-Time Summary")

    data = load_career()
    total_sessions = len(data.get("logs", []))
    total_minutes = sum(l.get("minutes", 0) for l in data.get("logs", []))

    c1, c2 = st.columns(2)

    c1.metric("Total Sessions", total_sessions)
    c2.metric("Total Minutes", total_minutes)

    # --------------------------------------------------
    # CURRENT ROLE
    # --------------------------------------------------
    role = current_role()
    if role:
        st.success(
            f"💼 **Current Role:** {role['role']} @ {role['company']} "
            f"({role['start_date']})"
        )
    else:
        st.info("No current role marked yet.")

    st.markdown("---")

    render_education()
    st.markdown("---")
    render_work()
    st.markdown("---")
    render_skills()

# ==================================================
# 📄 RESUME PREVIEW
# ==================================================
st.markdown("## 📄 Resume Preview")

resume_text = generate_resume_text()

st.text_area(
    "Generated Resume",
    resume_text,
    height=400
)

c1, c2 = st.columns(2)

with c1:
    if st.button("⬇️ Download PDF"):
        try:
            path = export_resume_pdf(resume_text)
            st.success("PDF generated ✅")
            st.download_button(
                "Download PDF file",
                data=open(path, "rb"),
                file_name=path.name,
                mime="application/pdf",
                key="download_pdf_resume",
            )
        except Exception as e:
            st.error(f"PDF export failed: {e}")

with c2:
    if st.button("⬇️ Download DOCX"):
        try:
            path = export_resume_docx(resume_text)
            st.success("DOCX generated ✅")
            st.download_button(
                "Download DOCX file",
                data=open(path, "rb"),
                file_name=path.name,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                key="download_docx_resume",
            )
        except Exception as e:
            st.error(f"DOCX export failed: {e}")

# ==================================================
# 🎓 EDUCATION
# ==================================================
def render_education():
    st.markdown("## 🎓 Education")

    education = list_education()

    if education:
        df = pd.DataFrame(education)
        df = df.drop(columns=["id"], errors="ignore")
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.caption("No education records yet.")

    with st.expander("➕ Add Education"):
        degree = st.text_input("Degree")
        field = st.text_input("Field of study")
        institution = st.text_input("Institution")

        # ✅ Safe default value prevents crash
        start_year = st.number_input(
            "Start year",
            min_value=1950,
            max_value=2100,
            step=1,
            value=2015,
        )

        still_studying = st.checkbox("Currently studying / ongoing")

        end_year = None
        if not still_studying:
            end_year = st.number_input(
                "End year",
                min_value=int(start_year),
                max_value=2100,
                step=1,
                value=int(start_year),
            )

        score = st.text_input("Score / Grade (optional)")
        notes = st.text_area("Notes (optional)")

        valid = degree and field and institution and start_year

        if st.button("Save Education", disabled=not valid):
            add_education(
                degree=degree,
                field=field,
                institution=institution,
                start_year=int(start_year),
                end_year=int(end_year) if end_year else None,
                score=score or None,
                notes=notes or None,
            )
            st.success("Education added ✅")
            st.rerun()

    # Delete
    if education:
        with st.expander("🗑️ Delete Education"):
            options = {
                f"{e['degree']} @ {e['institution']}": e.get("id")
                for e in education
            }
            label = st.selectbox("Select record", list(options.keys()))
            if st.button("Delete Selected", key="delete_education"):
                delete_education(options[label])
                st.warning("Education deleted")
                st.rerun()


# ==================================================
# 💼 WORK EXPERIENCE
# ==================================================
def render_work():
    st.markdown("## 💼 Work Experience")

    work = list_work()

    if work:
        df = pd.DataFrame(work)
        df = df.drop(columns=["id"], errors="ignore")
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.caption("No work experience yet.")

    with st.expander(
        "➕ Add Work",
        expanded=st.session_state.career_form_open
    ):
        # ✅ Inputs with keys (important)
        company = st.text_input("Company", key="work_company")
        role = st.text_input("Role / Title", key="work_role")
        start_date = st.text_input("Start date (YYYY-MM)", key="work_start_date")
        end_date = st.text_input("End date (YYYY-MM or blank)", key="work_end_date")
        current = st.checkbox("This is my current role", key="work_current")
        location = st.text_input("Location (optional)", key="work_location")
        tech_stack = st.text_input("Tech stack (comma separated)", key="work_tech_stack")
        achievements = st.text_area("Key achievements (one per line)", key="work_achievements")
        impact_tags = st.text_input("Impact tags (comma separated)", key="work_impact_tags")

        valid = company and role and start_date

        if st.button("Save Work", disabled=not valid, key="save_work"):
            add_work(
                company=company,
                role=role,
                start_date=start_date,
                end_date=end_date or None,
                current=current,
                location=location or None,
                tech_stack=[t.strip() for t in tech_stack.split(",") if t.strip()],
                achievements=[a.strip() for a in achievements.split("\n") if a.strip()],
                impact_tags=[t.strip() for t in impact_tags.split(",") if t.strip()],
            )

            # ✅ Clear form fields
            st.session_state.work_company = ""
            st.session_state.work_role = ""
            st.session_state.work_start_date = ""
            st.session_state.work_end_date = ""
            st.session_state.work_current = False
            st.session_state.work_location = ""
            st.session_state.work_tech_stack = ""
            st.session_state.work_achievements = ""
            st.session_state.work_impact_tags = ""

            # ✅ Close form
            st.session_state.career_form_open = False

            st.success("Work experience added ✅")
            st.rerun()

    # Delete
    if work:
        with st.expander("🗑️ Delete Work Experience"):
            options = {
                f"{w['role']} @ {w['company']} ({w['start_date']})": w["id"]
                for w in work
            }
            label = st.selectbox("Select record", list(options.keys()))
            if st.button("Delete Selected", key="delete_work_selected"):
                delete_work(options[label])
                st.warning("Work entry deleted")
                st.rerun()


# ==================================================
# 🛠️ SKILLS
# ==================================================
def render_skills():
    st.markdown("## 🛠️ Skills")

    skills = list_skills()

    if skills:
        df = pd.DataFrame(skills)
        df = df.drop(columns=["id"], errors="ignore")
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.caption("No skills added yet.")

    with st.expander("➕ Add Skill"):
        name = st.text_input("Skill name")
        category = st.selectbox(
            "Category",
            ["Programming", "System Design", "Cloud", "Data", "Leadership", "Other"]
        )
        level = st.selectbox(
            "Level",
            ["Beginner", "Intermediate", "Advanced", "Expert"]
        )
        last_used = st.text_input("Last used (YYYY-MM, optional)")
        evidence = st.text_area("Evidence (projects, links — one per line)")

        valid = name and category and level

        if st.button("Save Skill", disabled=not valid, key="save_skill"):
            add_skill(
                name=name,
                category=category,
                level=level,
                last_used=last_used or None,
                evidence=[e.strip() for e in evidence.split("\n") if e.strip()],
            )
            st.success("Skill added ✅")
            st.rerun()

    # Delete
    if skills:
        with st.expander("🗑️ Delete Skill"):
            options = {
                f"{s['name']} ({s['level']})": s.get("id", s["name"])
                for s in skills
            }
            label = st.selectbox("Select skill", list(options.keys()))
            if st.button("Delete Selected", key="delete_selected_skill"):
                delete_skill(options[label])
                st.warning("Skill deleted")
                st.rerun()
