import inspect
import streamlit as st
import pandas as pd
from datetime import datetime, date

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

# ==================================================
# THEME
# ==================================================
st.markdown("""
<style>
.block-container { padding-top: 1rem; }
.vinya-muted { color: #9aa4b2; font-size: 0.9rem; }
.vinya-good { color: #2ecc71; font-weight: 600; }
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
def safe_add_payment(loan_index, amount, note, month_key=None):
    try:
        sig = inspect.signature(add_payment)
        if "month_key" in sig.parameters:
            add_payment(loan_index, amount, note, month_key=month_key)
        else:
            add_payment(loan_index, amount, note)
    except Exception:
        add_payment(loan_index, amount, note)

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
    return {
        datetime.fromisoformat(p["date"]).strftime("%Y-%m")
        for p in loan.get("payments", [])
        if p.get("note") == note and p.get("date")
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

    # migrate start_month
    migrated = False
    for loan in loans:
        if not loan.get("start_month"):
            derive_start_month(loan)
            migrated = True
    if migrated:
        save_finance(data, tag="migrate_start_month")

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
            monthly = (
        loan.get("emi", 0)
        if loan["loan_type"] == "BANK"
        else calculate_interest_only(
            loan.get("principal", 0),
            loan.get("rate", 0),
            loan.get("interest_frequency", "MONTHLY")
        )
    )

            emi_paid = calculate_emis_paid(loan)
            emi_elapsed = calculate_emis_elapsed(loan)
            emi_overdue = calculate_emis_overdue(loan)
            payments = loan.get("payments", [])
            total_paid = sum((p.get("amount") or 0) for p in payments)

            if loan["loan_type"] == "BANK":
                try:
                    schedule, rem_principal = build_amortization_schedule(loan)
                    rem_interest = sum(r.get("interest", 0) for r in schedule)
                except Exception:
                    rem_principal = loan.get("principal", 0)
                    rem_interest = 0

                monthly = loan.get("emi") or 0
                paid_count = sum(1 for p in payments if p.get("note") == "EMI")
            else:
                rem_principal = loan.get("principal", 0)
                rem_interest = 0
                monthly = calculate_interest_only(
                    loan.get("principal", 0),
                    loan.get("rate", 0),
                    loan.get("interest_frequency", "MONTHLY")
                )
                paid_count = sum(1 for p in payments if p.get("note") == "INTEREST")

            rem_principal = round(rem_principal or 0, 2)
            rem_interest = round(rem_interest or 0, 2)
            total_outstanding = rem_principal + rem_interest
            taken = loan.get("taken_amount", loan.get("principal", 0))
            progress = loan_progress_percent(loan)
            health = loan_health_badge(loan)
            rows.append({
                "Loan": loan.get("name", "—"),
                #"Loan No": loan.get("loan_no", "—") if loan["loan_type"] == "BANK" else "—",
                "Health": health,
                "Taken Amount (₹)": f"₹ {taken:,.2f}",
                "Start Month": loan.get("start_month", "—"),
                "Monthly Amount (₹)": f"₹ {monthly:,.2f}",
                "EMIs Paid": emi_paid,
                "Progress": f"{progress}%",
                "Principal Outstanding (₹)": f"₹ {rem_principal:,.2f}",
                "Interest Outstanding (₹)": f"₹ {rem_interest:,.2f}",
                "Total Outstanding (₹)": f"₹ {total_outstanding:,.2f}",
                "Total Paid (₹)": f"₹ {total_paid:,.2f}",
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

    # ==================================================
    # ➕ ADD LOAN
    # ==================================================
    st.markdown("---")
    with st.expander("➕ Add Loan"):
        loan_type = st.selectbox("Loan Type", ["Bank (EMI)", "Friends / Family"])

        name = st.text_input("Loan name")
        principal = st.number_input("Principal (₹)", min_value=0.0, step=1000.0)
        rate = st.number_input("Interest rate (%)", min_value=0.0, step=0.1)
        start_date = st.date_input(
    "Loan start date",
    value=date.today().replace(day=1),
    min_value=date(2000, 1, 1),
    max_value=date.today()
)

        start_month = start_date.strftime("%Y-%m")
        if start_date > date.today():
            raise ValueError("Loan start date cannot be in the future")

        if loan_type == "Bank (EMI)":
            loan_no = st.text_input("Loan Number")
            tenure = st.number_input("Tenure (months)", min_value=1)
            emi = calculate_emi(principal, rate, tenure)

            if st.button("Save Bank Loan"):
                add_loan(
                    name=name,
                    principal=principal,
                    rate=rate,
                    tenure=tenure,
                    emi=emi,
                    loan_type="BANK"
                )
                data = load_finance()
                data["loans"][-1]["start_month"] = start_month
                data["loans"][-1]["loan_no"] = loan_no
                save_finance(data, tag="add_bank_loan")
                st.success("Bank loan added")
                st.rerun()
        else:
            freq = st.selectbox("Interest frequency", ["MONTHLY", "YEARLY"])
            if st.button("Save Family Loan"):
                add_loan(
                    name=name,
                    principal=principal,
                    rate=rate,
                    loan_type="INTEREST_ONLY",
                    interest_frequency=freq
                )
                data = load_finance()
                data["loans"][-1]["start_month"] = start_month
                save_finance(data, tag="add_family_loan")
                st.success("Family loan added")
                st.rerun()

    if not loans:
        return

    # ==================================================
    # 🔧 MANAGE LOAN
    # ==================================================
    st.markdown("---")
    st.markdown("## 🔧 Manage Loan")

    idx = st.selectbox(
        "Select a loan",
        range(len(loans)),
        format_func=lambda i: loans[i]["name"]
    )

    loan = loans[idx]

    st.markdown(f"### 💼 {loan['name']}")
    st.caption(f"📅 Loan start month: {loan['start_month']}")

    if loan["loan_type"] == "BANK":
        c1, c2 = st.columns(2)
        c1.caption(f"🏷️ Loan No: {loan.get('loan_no', '—')}")
        c2.caption(f"📊 Total EMIs: {loan.get('tenure', '—')}")

    months = month_range(loan["start_month"], current_month_key())
    selected_month = st.selectbox(
        "Select payment month",
        months,
        index=months.index(oldest_unpaid_month(loan, months))
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
                safe_add_payment(idx, interest, "INTEREST", selected_month)
                st.rerun()

        reduce = st.number_input("Reduce Principal (₹)", min_value=0, step=1000)
        if st.button("Reduce Principal"):
            safe_add_payment(idx, reduce, "PRINCIPAL", selected_month)
            st.rerun()

    # ==================================================
    # 📜 PAYMENT HISTORY
    # ==================================================
    st.markdown("---")
    st.markdown("## 📜 Payment History")

    history = build_payment_history(loan)
    if history:
        st.dataframe(pd.DataFrame(history), use_container_width=True, hide_index=True)
    else:
        st.info("No payments yet.")

    # ==================================================
    # UNDO / DELETE (UPDATED)
    # ==================================================
    st.markdown("---")
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