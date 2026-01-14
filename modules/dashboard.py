"""
Dashboard UI for Vinya
READS data + metrics only
NO calculations here
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import uuid

from core.health_store import (
    health_today_summary,
    protect_streak,
    weekly_health_recap,
    health_signal_today,
)

from core.shared_insights import finance_health_insight
from core.finance_store import load_finance
from core.finance_metrics import (
    portfolio_summary,
    loan_outstanding,
    loan_monthly_commitment,
    loan_health_status,
    next_gentle_action,
)

from core.life_store import gentle_life_insight
from core.career_store import weekly_growth_signal, gentle_nudge
from core.automation_store import list_automations, toggle_automation
from core.digest_store import latest_digest
from core.daily_digest import load_latest_digest


# ==================================================
# SESSION STATE
# ==================================================
if "insight_history" not in st.session_state:
    st.session_state.insight_history = []

if "dashboard_run_id" not in st.session_state:
    st.session_state.dashboard_run_id = uuid.uuid4().hex


# ==================================================
# MAIN DASHBOARD
# ==================================================
def render_dashboard():
    run_id = st.session_state.dashboard_run_id

    st.subheader("🏠 Dashboard")
    # ==================================================
    # 📰 DAILY DIGEST PREVIEW
    # ==================================================
    latest = latest_digest()

    if latest:
        with st.expander("📰 Latest Daily Digest"):
            st.json({
                "Health": latest.get("health"),
                "Finance": latest.get("finance"),
                "Career": latest.get("career"),
                "Gentle Action": latest.get("gentle_action"),
                "Timestamp": latest.get("timestamp"),
            })
    else:
        st.caption("No daily digest generated yet.")

    # ==================================================
    # 🌱 GLOBAL GENTLE INSIGHT
    # ==================================================
    insight = gentle_life_insight()
    if insight:
        st.markdown("### 🧠 Gentle Insight")
        st.info(insight)

    if protect_streak():
        st.warning(
            "🫶 You’ve had a few heavy days in a row. "
            "Consider resting, reducing load, or talking to someone you trust."
        )
    # ==================================================
    # 📰 LATEST DAILY DIGEST
    # ==================================================
    digest = load_latest_digest()
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    if digest:
        ts = datetime.fromisoformat(digest["timestamp"])
        pretty_time = ts.strftime("%d %b • %I:%M %p")

        st.markdown("## 📰 Daily Digest")
        st.caption(f"Last generated: {pretty_time}")

        c1, c2, c3 = st.columns(3)

        with c1:
            st.markdown("### 🩺 Health")
            st.info(f"{digest['health']['status']} — {digest['health']['message']}")

        with c2:
            st.markdown("### 💰 Finance")
            st.info(f"{digest['finance']['status']} — {digest['finance']['message']}")

        with c3:
            st.markdown("### 🧠 Career")
            st.info(digest["career"]["nudge"])

        st.success(f"🌱 **Gentle focus today:** {digest['gentle_action']}")

    # ==================================================
    # 🩺 TODAY’S HEALTH
    # ==================================================
    st.markdown("## 🩺 Today’s Health")

    signal = health_signal_today()

    status_color = {
        "PROTECT": "🟥",
        "BALANCE": "🟡",
        "OPTIMIZE": "🟢"
    }.get(signal["status"], "🟡")

    st.info(f"{status_color} **{signal['status']}** — {signal['message']}")

    recap = weekly_health_recap()
    if recap:
        st.markdown("### 🧠 Weekly Reflection")
        st.info(recap["message"])

    if st.button("➕ Log today (quick)"):
        from core.health_store import quick_log_today
        quick_log_today()
        st.toast("Health logged. Thanks for checking in 🤍")
        st.rerun()

    health = health_today_summary()

    st.markdown(
        f"""
        <div style="
            background:{health['color']};
            padding:14px;
            border-radius:10px;
            margin-bottom:12px;
        ">
            <strong>🧠 Health Today</strong><br/>
            {health['message']}
        </div>
        """,
        unsafe_allow_html=True
    )

    # ==================================================
    # 💰 FINANCE SNAPSHOT
    # ==================================================
    data = load_finance()
    loans = data.get("loans", [])

    if not loans:
        st.info("No loans added yet. Add a loan to see insights.")
        return

    summary = portfolio_summary(loans)

    c1, c2, c3 = st.columns(3)

    c1.metric("💰 Total Outstanding", f"₹ {summary['total_outstanding']:,.0f}")
    c2.metric("📆 Monthly Commitment", f"₹ {summary['total_monthly']:,.0f}")

    if summary["overdue_loans"] > 0:
        c3.metric("Status", "🔴 Action Needed")
    else:
        c3.metric("Status", "🟢 You’re Safe This Month")

    # Finance × Health gentle insight
    gentle = finance_health_insight(summary, health["status"])
    if gentle:
        st.info(gentle)

    # ==================================================
    # 🧠 NEXT GENTLE ACTION
    # ==================================================
    action = next_gentle_action(summary)
    st.info(f"🧠 **Next gentle action:** {action}")

    # Cap insight history to last 50 entries
    st.session_state.insight_history.append({
        "time": datetime.now().strftime("%d %b %Y, %I:%M %p"),
        "message": action,
    })
    st.session_state.insight_history = st.session_state.insight_history[-50:]

    with st.expander("🧠 Insight History (read-only)"):
        if st.session_state.insight_history:
            st.dataframe(
                pd.DataFrame(st.session_state.insight_history),
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.caption("No insights recorded yet.")

    # ==================================================
    # 📋 LOAN SNAPSHOT
    # ==================================================
    st.markdown("## 📋 Loan Snapshot")

    rows = []
    for loan in loans:
        rows.append({
            "Loan": loan.get("name", "—"),
            "Type": "Bank" if loan.get("loan_type") == "BANK" else "Family",
            "Health": loan_health_status(loan),
            "Monthly (₹)": f"₹ {loan_monthly_commitment(loan):,.2f}",
            "Outstanding (₹)": f"₹ {loan_outstanding(loan):,.2f}",
        })

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # ==================================================
    # ⚙️ AUTOMATIONS
    # ==================================================
    st.markdown("---")
    st.markdown("## ⚙️ Automations")

    autos = list_automations()

    if not autos:
        st.info("No automations configured yet.")
    else:
        for idx, auto in enumerate(autos):
            c1, c2, c3 = st.columns([3, 1, 2])

            with c1:
                st.markdown(f"**{auto['name']}**")
                st.caption(auto.get("description", ""))

            with c2:
                toggle_key = f"{run_id}_auto_toggle_{auto['id']}_{idx}"

                enabled = st.toggle(
                    "Enabled",
                    value=auto.get("enabled", True),
                    key=toggle_key,
                )

                if enabled != auto.get("enabled", True):
                    toggle_automation(auto["id"], enabled)
                    st.toast("Automation updated ✅")
                    st.rerun()

            with c3:
                last_run = auto.get("last_run")
                if last_run:
                    st.caption(f"Last run: {last_run}")
                else:
                    st.caption("Never run yet")

    # ==================================================
    # 🧠 CAREER SNAPSHOT
    # ==================================================
    st.markdown("## 🧠 Career")

    signal = weekly_growth_signal()
    nudge = gentle_nudge()

    c1, c2, c3 = st.columns(3)

    c1.metric("Weekly Status", signal["status"])
    c2.metric("Practice Minutes", f"{signal['total_minutes']} mins")
    c3.markdown(f"👉 **Next gentle action:** {nudge}")
