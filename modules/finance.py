import inspect
import streamlit as st
import pandas as pd
from datetime import datetime, date
from core.life_store import gentle_life_insight
from core.finance_store import (
    load_finance,
    save_finance,
    add_loan,
    delete_loan,
    add_payment,
    calculate_emi,
    calculate_interest_only,
    build_amortization_schedule,
    forecast_prepayment,
    calculate_emis_paid,
    calculate_emis_elapsed,
    calculate_emis_overdue,
)
if "active_loan_index" not in st.session_state:
    st.session_state.active_loan_index = None

# ==================================================
# THEME
# ==================================================
st.markdown("""
<style>
.block-container {
    padding-top: 1rem;
    max-width: 1100px;
}

h2, h3 {
    margin-bottom: 0.4rem;
}

.vinya-muted {
    color: #6b7280;
    font-size: 0.9rem;
}

.vinya-good {
    color: #16a34a;
    font-weight: 600;
}

div[data-testid="stMetric"] {
    background: #f9fafb;
    padding: 12px;
    border-radius: 10px;
}

hr {
    margin: 1.5rem 0;
    border: none;
    border-top: 1px solid #e5e7eb;
}
</style>
""", unsafe_allow_html=True)

# ==================================================
# DELETE UNDO STATE
# ==================================================
if "undo_delete" not in st.session_state:
    st.session_state.undo_delete = None
# ==================================================
# BACKWARD-COMPAT PAYMENT WRAPPER
# ==================================================
def safe_add_payment(loan_index, amount, note, month_key):
    """
    STRICT payment wrapper.
    Never drops month_key.
    Never swallows errors.
    """
    try:
        add_payment(
            loan_index=loan_index,
            amount=amount,
            note=note,
            month_key=month_key
        )
    except Exception as e:
        st.error(f"Payment failed: {e}")
        raise

# ==================================================
# HELPERS
# ==================================================
def loan_progress_percent(loan):
    taken = loan.get("taken_amount", loan.get("principal", 0))
    if taken <= 0:
        return 0
    repaid = taken - loan.get("principal", 0)
    return int(max(0, min(100, (repaid / taken) * 100)))

def loan_health_badge(loan):
    overdue = calculate_emis_overdue(loan)

    if overdue > 0:
        return "🔴 At Risk"
    elif loan_progress_percent(loan) < 25:
        return "🟡 Early Stage"
    else:
        return "🟢 On Track"

def current_month_key():
    return datetime.utcnow().strftime("%Y-%m")


def month_key_to_label(key):
    return datetime.strptime(key, "%Y-%m").strftime("%B %Y")

def derive_start_month(loan):
    if loan.get("start_month"):
        return loan["start_month"]

    if loan.get("payments"):
        months = [
            datetime.fromisoformat(p["date"]).strftime("%Y-%m")
            for p in loan["payments"]
            if p.get("date")
        ]
        start = min(months) if months else current_month_key()
    else:
        start = loan.get("created_at", current_month_key())[:7]

    loan["start_month"] = start
    return start


def month_range(start_key, end_key):
    start = datetime.strptime(start_key, "%Y-%m")
    end = datetime.strptime(end_key, "%Y-%m")
    months = []
    cur = start
    while cur <= end:
        months.append(cur.strftime("%Y-%m"))
        if cur.month == 12:
            cur = cur.replace(year=cur.year + 1, month=1)
        else:
            cur = cur.replace(month=cur.month + 1)
    return months


def payment_months(loan, note):
    note = note.upper()
    return {
        datetime.fromisoformat(p["date"]).strftime("%Y-%m")
        for p in loan.get("payments", [])
        if p.get("note", "").upper() == note and p.get("date")
    }



def payment_done_for_month(loan, month_key):
    if loan["loan_type"] == "BANK":
        return month_key in payment_months(loan, "EMI")
    return month_key in payment_months(loan, "INTEREST")


def oldest_unpaid_month(loan, months):
    note = "EMI" if loan["loan_type"] == "BANK" else "INTEREST"
    paid = payment_months(loan, note)
    for m in months:
        if m not in paid:
            return m
    return months[-1]


def undo_last_payment(loan_index):
    data = load_finance()
    loan = data["loans"][loan_index]

    if not loan["payments"]:
        return False

    last = loan["payments"].pop()

    if loan["loan_type"] == "INTEREST_ONLY" and last.get("note") == "PRINCIPAL":
        loan["principal"] += last.get("amount", 0)

    save_finance(data, tag="undo_payment")
    return True


def build_payment_history(loan):
    rows = []
    for p in loan.get("payments", []):
        try:
            dt = datetime.fromisoformat(p.get("date"))
            month = dt.strftime("%B %Y")
            date_fmt = dt.strftime("%d %b %Y")
            sort_key = dt
        except Exception:
            month = "—"
            date_fmt = "—"
            sort_key = datetime.min

        rows.append({
            "Month": month,
            "Type": p.get("note", "—"),
            "Amount (₹)": f"₹ {(p.get('amount') or 0):,.2f}",
            "Date": date_fmt,
            "_sort": sort_key
        })

    rows.sort(key=lambda x: x["_sort"], reverse=True)
    for r in rows:
        r.pop("_sort", None)
    return rows


def principal_vs_interest_paid(loan):
    if loan["loan_type"] != "BANK":
        return 0, 0

    schedule, _ = build_amortization_schedule(loan)
    principal_paid = 0
    interest_paid = 0
    emi_idx = 0

    for p in loan.get("payments", []):
        if p.get("note") == "EMI" and emi_idx < len(schedule):
            principal_paid += schedule[emi_idx]["principal"]
            interest_paid += schedule[emi_idx]["interest"]
            emi_idx += 1

    return round(principal_paid, 2), round(interest_paid, 2)


def compute_stress_score(loan):
    if loan["loan_type"] != "BANK":
        return 0

    schedule, rem_principal = build_amortization_schedule(loan)
    rem_interest = sum(r.get("interest", 0) for r in schedule)
    total_outstanding = rem_principal + rem_interest

    emi = loan.get("emi", 0)
    emis_paid = sum(1 for p in loan.get("payments", []) if p.get("note") == "EMI")
    total_emis = loan.get("tenure", 1)

    burden = min(emi / (total_outstanding + 1), 1)
    progress = emis_paid / total_emis
    stress = (burden * 50) + ((1 - progress) * 50)

    return int(min(100, max(0, stress)))
def compute_data_health_score():
    data = load_finance()

    total_fields = 0
    broken_fields = 0

    for loan in data.get("loans", []):
        for p in loan.get("payments", []):
            total_fields += 3  # amount, note, date

            if p.get("amount") is None:
                broken_fields += 1
            if not p.get("note"):
                broken_fields += 1
            if not p.get("date"):
                broken_fields += 1

    if total_fields == 0:
        return 100  # no data = perfect

    score = 100 - int((broken_fields / total_fields) * 100)
    return max(0, score)

def scan_repair_candidates():
    """
    Scan data and report what WOULD be fixed, without changing anything.
    """
    data = load_finance()
    report = []

    for loan in data.get("loans", []):
        loan_issues = {
            "loan_name": loan.get("name", "—"),
            "missing_amount": 0,
            "missing_note": 0,
            "missing_date": 0
        }

        for p in loan.get("payments", []):
            if p.get("amount") is None:
                loan_issues["missing_amount"] += 1
            if not p.get("note"):
                loan_issues["missing_note"] += 1
            if not p.get("date"):
                loan_issues["missing_date"] += 1

        if any(v > 0 for k, v in loan_issues.items() if k != "loan_name"):
            report.append(loan_issues)

    return report

def repair_old_payments():
    data = load_finance()
    fixes = {"payments_fixed": 0}

    for loan in data.get("loans", []):
        for p in loan.get("payments", []):
            if p.get("amount") is None:
                p["amount"] = 0
                fixes["payments_fixed"] += 1
            if not p.get("note"):
                p["note"] = "UNKNOWN"
            if not p.get("date"):
                p["date"] = loan.get("created_at")

    if fixes["payments_fixed"] > 0:
        save_finance(data, tag="repair_payments")

    return fixes
def validate_bank_loan(name, principal, rate, start_date, loan_no, tenure):
    errors = {}
    if not name.strip():
        errors["name"] = "Loan name is required"
    if principal <= 0:
        errors["principal"] = "Principal must be greater than 0"
    if rate <= 0:
        errors["rate"] = "Interest rate must be greater than 0"
    if not start_date:
        errors["start_date"] = "Start date is required"
    if not loan_no.strip():
        errors["loan_no"] = "Loan number is required"
    if tenure <= 0:
        errors["tenure"] = "Tenure must be at least 1 month"
    return errors


def validate_family_loan(name, principal, rate, start_date):
    errors = {}
    if not name.strip():
        errors["name"] = "Loan name is required"
    if principal <= 0:
        errors["principal"] = "Principal must be greater than 0"
    if rate <= 0:
        errors["rate"] = "Interest rate must be greater than 0"
    if not start_date:
        errors["start_date"] = "Start date is required"
    return errors
def last_interest_payment(loan):
    payments = [
        p for p in loan.get("payments", [])
        if p.get("note") == "INTEREST"
    ]
    if not payments:
        return None
    latest = max(
        payments,
        key=lambda p: p.get("date", "")
    )
    return datetime.fromisoformat(latest["date"]).strftime("%d %b %Y")
def gentle_finance_insights(loans):
    insights = []

    if not loans:
        return insights

    # Biggest monthly outflow
    biggest = None
    biggest_amt = 0

    for loan in loans:
        if loan["loan_type"] == "BANK":
            amt = loan.get("emi", 0)
        else:
            amt = calculate_interest_only(
                loan.get("principal", 0),
                loan.get("rate", 0),
                loan.get("interest_frequency", "MONTHLY")
            )

        if amt > biggest_amt:
            biggest_amt = amt
            biggest = loan.get("name")

    if biggest:
        insights.append(
            f"💸 **{biggest}** is currently your highest monthly outflow."
        )

    # Long untouched loans
    for loan in loans:
        if not loan.get("payments"):
            insights.append(
                f"⏳ **{loan.get('name')}** hasn’t had any payments yet."
            )

    if not insights:
        insights.append("🌱 Everything looks steady. No action needed right now.")

    return insights
def next_gentle_action(loans):
    if not loans:
        return "Start by adding your first loan — everything else will build naturally."

    # Bank loan overdue
    for loan in loans:
        if loan.get("loan_type") == "BANK" and calculate_emis_overdue(loan) > 0:
            return f"Consider catching up on **{loan.get('name')}** to reduce stress."

    # No interest paid yet for family loans
    for loan in loans:
        if loan.get("loan_type") == "INTEREST_ONLY":
            has_interest = any(
                p.get("note") == "INTEREST" for p in loan.get("payments", [])
            )
            if not has_interest:
                return f"A small interest payment on **{loan.get('name')}** could keep things smooth."

    # Otherwise calm state
    return "No immediate action needed — you’re in a stable spot this month 🌱"

def record_insight_snapshot(loans):
    """
    Stores only 1 insight per day.
    """
    data = load_finance()
    history = data.setdefault("insight_history", [])

    today = date.today().isoformat()
    if history and history[-1]["date"] == today:
        return  # already recorded today

    history.append({
        "date": today,
        "summary": next_gentle_action(loans)
    })

    # keep last 30 only
    data["insight_history"] = history[-30:]
    save_finance(data, tag="insight_snapshot")


def load_insight_history():
    data = load_finance()
    return data.get("insight_history", [])

# ==================================================
# MAIN UI
# ==================================================
def render_finance():
    st.subheader("💳 Finance")
# ==================================================
# 📊 DATA HEALTH SCORE
# ==================================================
    health_score = compute_data_health_score()

    if health_score >= 95:
        st.success(f"📊 Data Quality: {health_score}% — Excellent")
    elif health_score >= 85:
        st.warning(f"📊 Data Quality: {health_score}% — Good")
    else:
        st.error(f"📊 Data Quality: {health_score}% — Needs Attention")
    data = load_finance()
    loans = data["loans"]
    # 🔁 One-time migration: set taken_amount for old loans
    migrated = False
    for loan in loans:
        if "taken_amount" not in loan:
            loan["taken_amount"] = loan.get("principal", 0)
            migrated = True

    if migrated:
        save_finance(data, tag="migrate_taken_amount")

# ==================================================
# 🧾 AUTO-REPAIR (SAFE MODE)
# ==================================================
    repair_report = scan_repair_candidates()

    if repair_report:
        # silently repair without UI interruption
        repair_old_payments()

# ==================================================
# 🛠️ DATA REPAIR (SMART)
# ==================================================
    repair_report = scan_repair_candidates()

    if repair_report:
        with st.expander("🛠️ Data Health Check"):
            st.caption("Preview of issues found in existing data:")

        preview_rows = []
        for r in repair_report:
            preview_rows.append({
                "Loan": r["loan_name"],
                "Missing Amount": r["missing_amount"],
                "Missing Note": r["missing_note"],
                "Missing Date": r["missing_date"],
            })

        st.dataframe(
            pd.DataFrame(preview_rows),
            use_container_width=True,
            hide_index=True
        )

        st.warning(
            "Fixing will only fill missing values (0 / UNKNOWN / created date). "
            "No amounts or loans will be deleted."
        )

        if st.button("Fix these issues"):
            result = repair_old_payments()

            fixed_loans = [r["loan_name"] for r in repair_report]

            st.success(
                f"Repaired {result['payments_fixed']} payment records "
                f"across {len(fixed_loans)} loan(s)."
            )

            st.markdown("**Loans repaired:**")
            st.write(", ".join(fixed_loans))

            st.rerun()

    st.markdown("### 🧠 Gentle Insights")

    for tip in gentle_finance_insights(loans):
        st.info(tip)

    # ==================================================
    # 📊 LOANS OVERVIEW
    # ==================================================
    st.markdown("## 📊 Loans Overview")
    
    data = load_finance()
    loans = data["loans"]

    total_taken = sum(
        l.get("taken_amount", l.get("principal", 0)) for l in loans
    )
    total_outstanding = sum(
        l.get("principal", 0) for l in loans
    )

    overall_progress = (
        int(((total_taken - total_outstanding) / total_taken) * 100)
        if total_taken > 0 else 0
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("💰 Total Taken", f"₹ {total_taken:,.0f}")
    c2.metric("📉 Total Outstanding", f"₹ {total_outstanding:,.0f}")
    c3.metric("📊 Overall Progress", f"{overall_progress}%")

    def build_rows(items):
        rows = []

        for loan in items:
            payments = loan.get("payments", [])
            total_paid = sum((p.get("amount") or 0) for p in payments)

            # ---------------- BANK LOANS ----------------
            if loan["loan_type"] == "BANK":
                try:
                    schedule, rem_principal = build_amortization_schedule(loan)
                    rem_interest = sum(r.get("interest", 0) for r in schedule)
                except Exception:
                    rem_principal = loan.get("principal", 0)
                    rem_interest = 0

                taken = loan.get("taken_amount", loan.get("principal", 0))
                progress = loan_progress_percent(loan)
                emi_paid = calculate_emis_paid(loan)

                rows.append({
                    "Loan Name": loan.get("name", "—"),
                    "Health": loan_health_badge(loan),
                    "Amount Taken (₹)": f"₹ {taken:,.2f}",
                    "Start Month": loan.get("start_month", "—"),
                    "Monthly EMI (₹)": f"₹ {loan.get('emi', 0):,.2f}",
                    "EMIs Paid": emi_paid,
                    "Progress": f"{progress}%",
                    "Principal Left (₹)": f"₹ {rem_principal:,.2f}",
                    "Interest Left (₹)": f"₹ {rem_interest:,.2f}",
                    "Total Due (₹)": f"₹ {(rem_principal + rem_interest):,.2f}",
                    "Paid So Far (₹)": f"₹ {total_paid:,.2f}",
                })

            # ---------------- FRIENDS / FAMILY ----------------
            else:
                monthly_interest = calculate_interest_only(
                    loan.get("principal", 0),
                    loan.get("rate", 0),
                    loan.get("interest_frequency", "MONTHLY")
                )

                last_paid = last_interest_payment(loan)
                last_badge = f"🟣 {last_paid}" if last_paid else "⚪ Never"

                rows.append({
                    "Loan Name": loan.get("name", "—"),
                    "Amount Taken (₹)": f"₹ {loan.get('taken_amount', loan.get('principal', 0)):,.2f}",
                    "Start Month": loan.get("start_month", "—"),
                    "Monthly Interest (₹)": f"₹ {monthly_interest:,.2f}",
                    "Principal Left (₹)": f"₹ {loan.get('principal', 0):,.2f}",
                    "Last Interest Paid": last_badge,
                    "Paid So Far (₹)": f"₹ {total_paid:,.2f}",
                })

        return rows


    bank_loans = [l for l in loans if l["loan_type"] == "BANK"]
    family_loans = [l for l in loans if l["loan_type"] == "INTEREST_ONLY"]

    if bank_loans:
        st.markdown("### 🏦 Bank Loans")
        st.dataframe(pd.DataFrame(build_rows(bank_loans)), use_container_width=True)

    if family_loans:
        st.markdown("### 👨‍👩‍👧 Friends / Family Loans")
        st.dataframe(pd.DataFrame(build_rows(family_loans)), use_container_width=True)
    insight = gentle_life_insight()
    if insight:
        st.caption(f"🧠 {insight}")
    # ==================================================
    # ➕ ADD LOAN (VALIDATED)
    # ==================================================
    st.markdown("<hr/>", unsafe_allow_html=True)
    with st.expander(
        "➕ Add Loan",
        expanded=(len(loans) == 0)  # 👈 auto-open when no loans
    ):

        loan_type = st.selectbox("Loan Type *", ["Bank (EMI)", "Friends / Family"])

        name = st.text_input("Loan name *")
        principal = st.number_input("Principal (₹) *", min_value=0.0, step=1000.0)
        rate = st.number_input("Interest rate (%) *", min_value=0.0, step=0.1)

        start_date = st.date_input(
            "Loan start date *",
            value=date.today().replace(day=1),
            min_value=date(2000, 1, 1),
            max_value=date.today()
        )

        # ---------------- BANK LOAN ----------------
        errors = {}  # 👈 ALWAYS initialize

        if loan_type == "Bank (EMI)":
            loan_no = st.text_input("Loan Number *")
            tenure = st.number_input("Tenure (months) *", min_value=1)

            emi = calculate_emi(principal, rate, tenure) if principal > 0 and rate > 0 else 0
            st.caption(f"Calculated EMI: ₹ {emi:,.2f}" if emi else "Calculated EMI will appear here")


            errors = validate_bank_loan(
                name, principal, rate, start_date, loan_no, tenure
            )

            for e in errors.values():
                st.error(e)

            if st.button("Save Bank Loan", disabled=len(errors) > 0):
                add_loan(
                    name=name,
                    principal=principal,
                    rate=rate,
                    start_date=start_date,
                    tenure=tenure,
                    emi=emi,
                    loan_type="BANK"
                )

                data = load_finance()
                new_index = len(data["loans"]) - 1

                data["loans"][new_index]["loan_no"] = loan_no
                data["loans"][new_index]["start_date"] = start_date.isoformat()
                data["loans"][new_index]["start_month"] = start_date.strftime("%Y-%m")

                save_finance(data, tag="add_bank_loan")


                st.session_state.active_loan_index = new_index
                st.success("Bank loan added")
                st.rerun()

        # ---------------- FAMILY LOAN ----------------
        errors = {}  # 👈 ALWAYS initialize

        if loan_type == "Friends / Family":
            freq = st.selectbox("Interest frequency *", ["MONTHLY", "YEARLY"])

            errors = validate_family_loan(
                name, principal, rate, start_date
            )

            for e in errors.values():
                st.error(e)

            if st.button("Save Family Loan", disabled=len(errors) > 0):
                add_loan(
                    name=name,
                    principal=principal,
                    rate=rate,
                    start_date=start_date,
                    loan_type="INTEREST_ONLY",
                    interest_frequency=freq
                )


                data = load_finance()
                new_index = len(data["loans"]) - 1

                data["loans"][new_index]["start_date"] = start_date.isoformat()
                data["loans"][new_index]["start_month"] = start_date.strftime("%Y-%m")

                st.session_state.active_loan_index = new_index

                save_finance(data, tag="add_family_loan")


                st.success("Family loan added")
                st.rerun()

    # ==================================================
    # 🔧 MANAGE LOAN
    # ==================================================
    st.markdown("<hr/>", unsafe_allow_html=True)
    st.markdown("## 🔧 Manage Loan")

    # 🛡️ SAFETY: no loans → no manage section
    if not loans:
        st.info("No loans available.")
        return

    default_idx = (
        st.session_state.active_loan_index
        if st.session_state.active_loan_index is not None
        else 0
    )

    idx = st.selectbox(
        "Select a loan",
        options=list(range(len(loans))),
        index=default_idx,
        format_func=lambda i: loans[i]["name"]
    )

    # reset router after use
    st.session_state.active_loan_index = None


    # 🛡️ Streamlit can briefly return None during reruns
    if idx is None:
        st.stop()

    loan = loans[idx]


    st.markdown(f"### 💼 {loan['name']}")
    st.caption(f"📅 Loan start month: {loan['start_month']}")

    if loan["loan_type"] == "BANK":
        c1, c2 = st.columns(2)
        c1.caption(f"🏷️ Loan No: {loan.get('loan_no', '—')}")
        c2.caption(f"📊 Total EMIs: {loan.get('tenure', '—')}")
    if not loan.get("start_month") and loan.get("start_date"):
        loan["start_month"] = datetime.fromisoformat(
            loan["start_date"]
        ).strftime("%Y-%m")
        save_finance(data, tag="fix_missing_start_month")

    months = month_range(loan["start_month"], current_month_key())
    default_month = oldest_unpaid_month(loan, months)
    if default_month not in months:
        default_month = months[0]
    selected_month = st.selectbox(
        "Select payment month",
        months,
        index=months.index(default_month)
    )

    month_label = month_key_to_label(selected_month)

    # ==================================================
    # PAYMENTS
    # ==================================================
    if loan["loan_type"] == "BANK":
        if payment_done_for_month(loan, selected_month):
            st.success(f"EMI for {month_label} already paid ✔️")
            st.button("Pay EMI", disabled=True)
        else:
            if st.button(f"Pay EMI for {month_label}"):
                safe_add_payment(idx, loan["emi"], "EMI", selected_month)
                st.rerun()
    else:
        interest = calculate_interest_only(
            loan["principal"], loan["rate"], loan["interest_frequency"]
        )

        if payment_done_for_month(loan, selected_month):
            st.success(f"Interest for {month_label} already paid ✔️")
            st.button("Pay Interest", disabled=True)
        else:
            if st.button(f"Pay Interest for {month_label}"):
                st.caption("ℹ️ Interest payment does not reduce principal for this loan.")
                safe_add_payment(idx, interest, "INTEREST", selected_month)
                st.rerun()

        reduce = st.number_input("Reduce Principal (₹)", min_value=0, step=1000)
        if st.button("Reduce Principal"):
            safe_add_payment(idx, reduce, "PRINCIPAL", selected_month)
            st.rerun()

    # ==================================================
    # 📜 PAYMENT HISTORY
    # ==================================================
    st.markdown("<hr/>", unsafe_allow_html=True)
    st.markdown("## 📜 Payment History")

    history = build_payment_history(loan)
    if history:
        st.dataframe(pd.DataFrame(history), use_container_width=True, hide_index=True)
    else:
        st.info("No payments yet.")

    # ==================================================
    # UNDO / DELETE (UPDATED)
    # ==================================================
    st.markdown("<hr/>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)

    with c1:
        if st.button("Undo Last Payment"):
            if undo_last_payment(idx):
                st.rerun()

    with c2:
        if st.button("Delete Loan"):
            data = load_finance()
            deleted_loan = data["loans"].pop(idx)
            save_finance(data, tag="delete_loan")

            st.session_state.undo_delete = {
                "loan": deleted_loan,
                "expires_at": datetime.utcnow().timestamp() + 10
            }

            st.toast("🗑️ Loan deleted — Undo?", icon="⚠️")
            st.rerun()

    # ==================================================
    # UNDO DELETE HANDLER
    # ==================================================
    undo = st.session_state.undo_delete
    if undo:
        now = datetime.utcnow().timestamp()

        if now <= undo["expires_at"]:
            if st.button("Undo delete"):
                data = load_finance()
                data["loans"].append(undo["loan"])
                save_finance(data, tag="undo_delete")

                st.session_state.undo_delete = None
                st.toast("✅ Loan restored", icon="♻️")
                st.rerun()
        else:
            st.session_state.undo_delete = None
    with st.expander("🧠 Insight history"):
        history = load_insight_history()

        if not history:
            st.caption("No insights recorded yet.")
        else:
            rows = [
                {
                    "Date": h["date"],
                    "Insight": h["summary"]
                }
                for h in reversed(history)
            ]
            st.dataframe(
                pd.DataFrame(rows),
                use_container_width=True,
                hide_index=True
            )
