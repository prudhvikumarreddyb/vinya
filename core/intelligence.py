from core.finance_store import (
    load_finance,
    calculate_interest_only,
    build_amortization_schedule
)

def generate_finance_insights():
    data = load_finance()
    loans = data["loans"]

    if not loans:
        return {
            "risk": "No financial liabilities recorded",
            "watch": "You are currently debt-free",
            "positive": "Clean financial slate",
            "focus": "Maintain this position"
        }

    total_emi = 0
    interest_only_loans = 0
    bank_loans = 0
    stagnant_family_loans = 0
    improving_loans = 0

    for loan in loans:
        if loan["loan_type"] == "BANK":
            bank_loans += 1
            total_emi += loan["emi"] or 0

            schedule, remaining = build_amortization_schedule(loan)
            if remaining < loan["principal"] * 0.9:
                improving_loans += 1

        else:
            interest_only_loans += 1
            interest = calculate_interest_only(
                loan["principal"],
                loan["rate"],
                loan["interest_frequency"]
            )

            total_emi += interest

            principal_paid = any(
                p["note"] == "PRINCIPAL" for p in loan["payments"]
            )
            if not principal_paid:
                stagnant_family_loans += 1

    # -------------------------
    # Risk
    # -------------------------
    if total_emi > 50000:
        risk = "Monthly financial outflow is very high"
    elif interest_only_loans > 2:
        risk = "Too many interest-only loans without closure"
    else:
        risk = "Financial load is manageable"

    # -------------------------
    # Watch
    # -------------------------
    if stagnant_family_loans > 0:
        watch = "Some family loans have no principal reduction yet"
    elif bank_loans > 3:
        watch = "Multiple active bank loans need consolidation"
    else:
        watch = "No immediate concerns detected"

    # -------------------------
    # Positive
    # -------------------------
    if improving_loans > 0:
        positive = "You are actively reducing debt"
    elif total_emi < 20000:
        positive = "Monthly obligations are light"
    else:
        positive = "You are staying consistent"

    # -------------------------
    # Focus
    # -------------------------
    if stagnant_family_loans > 0:
        focus = "Reduce principal on at least one family loan this month"
    elif total_emi > 50000:
        focus = "Try closing or prepaying one EMI"
    else:
        focus = "Continue current repayment discipline"

    return {
        "risk": risk,
        "watch": watch,
        "positive": positive,
        "focus": focus
    }
