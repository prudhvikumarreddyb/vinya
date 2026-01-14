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
    load_career,
    log_practice,
    weekly_growth_signal,
    weekly_logs,
    gentle_nudge,
)

# ==================================================
# MAIN UI
# ==================================================
def render_career():
    st.subheader("🧠 Career Growth")

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
    # 📦 ALL-TIME SUMMARY (LIGHT)
    # ==================================================
    st.markdown("---")
    st.markdown("### 📦 All-Time Summary")

    data = load_career()
    total_sessions = len(data.get("logs", []))
    total_minutes = sum(l.get("minutes", 0) for l in data.get("logs", []))

    c1, c2 = st.columns(2)

    c1.metric("Total Sessions", total_sessions)
    c2.metric("Total Minutes", total_minutes)

