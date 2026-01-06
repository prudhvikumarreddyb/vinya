# modules/health.py
"""
Health module UI for Vinya (Health v0.1)

Gentle, signal-based health tracking.
"""

import streamlit as st
import pandas as pd
from datetime import date

from core.health_store import (
    load_health,
    add_today_entry,
    get_today_entry,
    health_signal_today,
    maybe_store_insight,
    get_insight_history,
)

# ==================================================
# THEME
# ==================================================
st.markdown(
    """
    <style>
    .health-card {
        padding: 1rem;
        border-radius: 12px;
        background: #111827;
        margin-bottom: 1rem;
    }
    .health-status {
        font-size: 1.2rem;
        font-weight: 600;
    }
    .health-muted {
        color: #9ca3af;
        font-size: 0.9rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown("## 🧠 Insight History")

data = load_health()
insights = data.get("insights", [])[-7:][::-1]

for i in insights:
    st.markdown(
        f"• **{i['date']}** — {i['message']}",
    )
from core.health_store import health_streaks

streaks = health_streaks()

if streaks["sleep_streak"] > 1 or streaks["movement_streak"] > 1:
    st.markdown("### 🔁 Gentle Streaks")

    cols = st.columns(2)

    if streaks["sleep_streak"] > 1:
        cols[0].success(f"😴 {streaks['sleep_streak']} days of steady sleep")

    if streaks["movement_streak"] > 1:
        cols[1].success(f"🚶 {streaks['movement_streak']} days of movement")

# ==================================================
# MAIN RENDER
# ==================================================
def render_health():
    st.subheader("🧘 Health")

    # --------------------------------------------------
    # Today’s signal
    # --------------------------------------------------
    signal = health_signal_today()

    status_color = {
        "STABLE": "#22c55e",
        "WATCH": "#f59e0b",
        "PROTECT": "#ef4444",
        "UNKNOWN": "#9ca3af",
    }.get(signal["status"], "#9ca3af")

    st.markdown(
        f"""
        <div class="health-card">
            <div class="health-status" style="color:{status_color}">
                {signal["status"]}
            </div>
            <div class="health-muted">
                {signal["message"]}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --------------------------------------------------
    # Daily check-in
    # --------------------------------------------------
    st.markdown("### 📝 Today’s check-in")

    today_entry = get_today_entry()

    if today_entry:
        st.success("✅ Today’s health check-in is already logged.")

        st.write(
            {
                "Sleep": today_entry["sleep"],
                "Energy": today_entry["energy"],
                "Stress": today_entry["stress"],
                "Movement": "Yes" if today_entry["movement"] else "No",
            }
        )
    else:
        with st.form("health_checkin"):
            sleep = st.selectbox(
                "Sleep last night",
                ["<5", "5-6", "6-7", "7+"],
            )
            energy = st.selectbox(
                "Energy today",
                ["low", "okay", "good"],
            )
            stress = st.selectbox(
                "Stress level",
                ["calm", "busy", "overwhelmed"],
            )
            movement = st.checkbox("Any movement today? (walk, stretch, workout)")

            submitted = st.form_submit_button("Save today")

            if submitted:
                try:
                    add_today_entry(
                        sleep=sleep,
                        energy=energy,
                        stress=stress,
                        movement=movement,
                    )
                    maybe_store_insight()
                    st.success("Health check-in saved 🌱")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

    # --------------------------------------------------
    # Insight history (read-only)
    # --------------------------------------------------
    st.markdown("---")
    st.markdown("### 🧠 Insight history")

    insights = get_insight_history()

    if not insights:
        st.info("No insights yet. They’ll appear gently over time.")
    else:
        df = pd.DataFrame(insights)
        df = df.sort_values("date", ascending=False)
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%d %b %Y")

        st.dataframe(
            df.rename(columns={"date": "Date", "insight": "Insight"}),
            use_container_width=True,
            hide_index=True,
        )
