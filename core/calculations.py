from datetime import date

REQUIRED_LOAN_FIELDS = {
    "loan_id", "lender_name", "loan_type",
    "principal", "interest_rate", "emi",
    "start_date", "tenure_months",
    "emis_paid", "status"
}

def validate_loans(loans):
    for i, loan in enumerate(loans):
        missing = REQUIRED_LOAN_FIELDS - loan.keys()
        if missing:
            raise ValueError(f"Loan {i} missing fields: {missing}")

def build_dashboard_summary(loans, payments):
    validate_loans(loans)

    today = date.today()
    active = [l for l in loans if l["status"] == "active"]

    total_outstanding = sum(l["principal"] for l in active)
    total_emi = sum(l["emi"] for l in active)

    highest_interest = (
        max(active, key=lambda x: x["interest_rate"])["lender_name"]
        if active else None
    )

    weighted_months = sum(
        (l["tenure_months"] - l["emis_paid"]) * l["principal"]
        for l in active if l["tenure_months"] > l["emis_paid"]
    )
    total_weight = sum(l["principal"] for l in active)

    remaining_months = round(weighted_months / total_weight) if total_weight else 0

    emis_paid_this_month = sum(
        1 for p in payments
        if p["type"] == "emi"
        and p["date"].month == today.month
        and p["date"].year == today.year
    )

    overdue = False
    for l in active:
        expected = (
            (today.year - l["start_date"].year) * 12
            + (today.month - l["start_date"].month) + 1
        )
        if l["emis_paid"] < expected:
            overdue = True
            break

    return {
        "total_outstanding": total_outstanding,
        "total_emi": total_emi,
        "active_loans": len(active),
        "highest_interest_loan": highest_interest,
        "remaining_months": remaining_months,
        "emis_paid_this_month": emis_paid_this_month,
        "overdue": overdue
    }
