import streamlit as st
from datetime import datetime
from dateutil.relativedelta import relativedelta

from core.finance_store import load_finance, build_amortization_schedule


# =========================
# HELPERS
# =========================
def calculate_stress(loans, emi_paid_loans, total_outstanding, total_monthly_emi):
    # EMI risk (40%)
    bank_loans = [l for l in loans if l["loan_type"] == "BANK"]
    total_bank = len(bank_loans)
    paid_bank = len(emi_paid_loans)

    if total_bank == 0 or paid_bank == total_bank:
        emi_risk = 0
    elif paid_bank == 0:
        emi_risk = 100
    else:
        emi_risk = 50

    emi_component = emi_risk * 0.4

    # Burden (40%)
    if total_monthly_emi == 0:
        burden_component = 0
    else:
        ratio = min(total_outstanding / (total_monthly_emi * 24), 1)
        burden_component = ratio * 40

    # Fragmentation (20%)
    fragmentation_component = min(len(loans) * 4, 20)

    return round(emi_component + burden_component + fragmentation_component)


def health_insight(score):
    if score <= 20:
        return "🧘 Calm zone. Financial stress unlikely to affect health."
    elif score <= 40:
        return "🙂 Mild load. Maintain sleep and routines."
    elif score <= 60:
        return "😐 Medium stress. Watch focus and recovery."
    elif score <= 80:
        return "⚠️ High stress. Elevated cortisol risk."
    else:
        return "🚨 Critical stress. Burnout risk — de-risk urgently."


# =========================
# DASHBOARD
# =========================
def render_dashboard():
    st.subheader("📊 Dashboard")

    data = load_finance()
    loans = data["loans"]

    now = datetime.utcnow()
    current_month = now.strftime("%Y-%m")

    # =========================
    # CURRENT MONTH AGGREGATES
    # =========================
    total_outflow = 0
    total_emi_paid = 0
    total_interest_paid = 0
    total_principal_reduced = 0
    loans_touched = set()
    emi_paid_loans = set()

    for idx, loan in enumerate(loans):
        for p in loan.get("payments", []):
            paid_month = datetime.fromisoformat(p["date"]).strftime("%Y-%m")
            if paid_month != current_month:
                continue

            total_outflow += p["amount"]
            loans_touched.add(idx)

            if p["note"] == "EMI":
                total_emi_paid += p["amount"]
                emi_paid_loans.add(idx)
            elif p["note"] == "INTEREST":
                total_interest_paid += p["amount"]
            elif p["note"] == "PRINCIPAL":
                total_principal_reduced += p["amount"]

    # =========================
    # OUTSTANDING
    # =========================
    principal_outstanding = 0
    interest_outstanding = 0
    total_monthly_emi = 0

    for loan in loans:
        if loan["loan_type"] == "BANK":
            schedule, remaining = build_amortization_schedule(loan)
            principal_outstanding += remaining
            interest_outstanding += sum(r["interest"] for r in schedule)
            total_monthly_emi += loan["emi"]
        else:
            principal_outstanding += loan["principal"]

    total_outstanding = principal_outstanding + interest_outstanding

    # =========================
    # CURRENT STRESS
    # =========================
    stress_score = calculate_stress(
        loans,
        emi_paid_loans,
        total_outstanding,
        total_monthly_emi
    )

    # =========================
    # SIGNAL
    # =========================
    if stress_score <= 40:
        st.success("🟢 You’re safe this month")
    elif stress_score <= 60:
        st.warning("🟡 Attention needed")
    else:
        st.error("🔴 Financial risk detected")

    # =========================
    # KEY METRICS
    # =========================
    st.markdown("---")
    st.metric("Stress Score (0–100)", stress_score)

    c1, c2, c3 = st.columns(3)
    c1.metric("Principal Outstanding", f"₹ {principal_outstanding:,.0f}")
    c2.metric("Interest Outstanding", f"₹ {interest_outstanding:,.0f}")
    c3.metric("Total Outstanding", f"₹ {total_outstanding:,.0f}")

    # =========================
    # 🔮 WHAT-IF
    # =========================
    st.markdown("---")
    st.markdown("### 🔮 What-If Simulator")

    prepay = st.number_input("If I prepay (₹)", min_value=0, step=10000)
    if prepay > 0:
        new_outstanding = max(total_outstanding - prepay, 0)
        new_stress = calculate_stress(
            loans,
            emi_paid_loans,
            new_outstanding,
            total_monthly_emi
        )
        st.info(
            f"Prepaying ₹{prepay:,.0f} changes stress "
            f"from **{stress_score} → {new_stress}**"
        )

    # =========================
    # 🧠 HEALTH SYNC
    # =========================
    st.markdown("---")
    st.markdown("### 🧠 Health Insight")
    st.write(health_insight(stress_score))

    # =========================
    # 📈 STRESS TREND (6 MONTHS)
    # =========================
    st.markdown("---")
    st.markdown("### 📈 Stress Trend (Last 6 Months)")

    trend = []

    for i in range(5, -1, -1):
        month_date = now - relativedelta(months=i)
        month_key = month_date.strftime("%Y-%m")

        emi_paid = set()
        for idx, loan in enumerate(loans):
            for p in loan.get("payments", []):
                if p["note"] == "EMI":
                    if datetime.fromisoformat(p["date"]).strftime("%Y-%m") == month_key:
                        emi_paid.add(idx)

        score = calculate_stress(
            loans,
            emi_paid,
            total_outstanding,
            total_monthly_emi
        )

        trend.append({"Month": month_key, "Stress": score})

    st.line_chart(
        {row["Month"]: row["Stress"] for row in trend}
    )

    # =========================
    # 📅 MONTHLY SUMMARY
    # =========================
    st.markdown("---")
    st.markdown("### 📅 This Month Summary")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Outflow", f"₹ {total_outflow:,.0f}")
    c2.metric("EMI Paid", f"₹ {total_emi_paid:,.0f}")
    c3.metric("Interest Paid", f"₹ {total_interest_paid:,.0f}")
    c4.metric("Principal Reduced", f"₹ {total_principal_reduced:,.0f}")

    st.write(f"Loans touched this month: **{len(loans_touched)}**")
