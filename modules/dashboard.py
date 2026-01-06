# modules/dashboard.py
"""
Dashboard UI for Vinya
READS data + metrics only
NO calculations here
"""

import streamlit as st
import pandas as pd
from datetime import datetime

from core.finance_store import load_finance
from core.finance_metrics import (
    portfolio_summary,
    loan_outstanding,
    loan_monthly_commitment,
    loan_health_status,
    next_gentle_action,
)

# ==================================================
# SESSION STATE
# ==================================================
if "insight_history" not in st.session_state:
    st.session_state.insight_history = []

# ==================================================
# MAIN DASHBOARD
# ==================================================
def render_dashboard():
    st.subheader("🏠 Dashboard")

    data = load_finance()
    loans = data.get("loans", [])

    if not loans:
        st.info("No loans added yet. Add a loan to see insights.")
        return

    # ==================================================
    # 📊 PORTFOLIO SUMMARY (SINGLE SOURCE OF TRUTH)
    # ==================================================
    summary = portfolio_summary(loans)

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "💰 Total Outstanding",
        f"₹ {summary['total_outstanding']:,.0f}",
    )

    c2.metric(
        "📆 Monthly Commitment",
        f"₹ {summary['total_monthly']:,.0f}",
    )

    if summary["overdue_loans"] > 0:
        c3.metric("Status", "🔴 Action Needed")
    else:
        c3.metric("Status", "🟢 You’re Safe This Month")

    # ==================================================
    # 🧠 NEXT GENTLE ACTION
    # ==================================================
    action = next_gentle_action(summary)

    st.info(f"🧠 **Next gentle action:** {action}")

    # store insight history (read-only log)
    st.session_state.insight_history.append({
        "time": datetime.now().strftime("%d %b %Y, %I:%M %p"),
        "message": action,
    })

    # ==================================================
    # 📜 INSIGHT HISTORY (READ-ONLY)
    # ==================================================
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
    # 📋 LOAN SNAPSHOT (LIGHTWEIGHT)
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

    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
    )
