# core/finance_metrics.py
"""
READ-ONLY financial calculations.
No Streamlit.
No file writes.
Safe to import anywhere.
"""

from datetime import date
from typing import Dict, Any, List

from core.finance_store import (
    calculate_emis_paid,
    calculate_emis_elapsed,
    calculate_emis_overdue,
    calculate_interest_only,
    build_amortization_schedule,
)

# ==================================================
# LOAN-LEVEL METRICS
# ==================================================
def loan_outstanding(loan: Dict[str, Any]) -> float:
    if loan.get("loan_type") == "BANK":
        try:
            _, remaining = build_amortization_schedule(loan)
            return round(remaining, 2)
        except Exception:
            return round(loan.get("principal", 0), 2)

    # Friends / Family
    return round(loan.get("principal", 0), 2)


def loan_monthly_commitment(loan: Dict[str, Any]) -> float:
    if loan.get("loan_type") == "BANK":
        return round(loan.get("emi", 0), 2)

    return calculate_interest_only(
        loan.get("principal", 0),
        loan.get("rate", 0),
        loan.get("interest_frequency", "MONTHLY"),
    )


def loan_health_status(loan: Dict[str, Any]) -> str:
    overdue = calculate_emis_overdue(loan)

    if overdue > 0:
        return "🔴 At Risk"

    if loan.get("loan_type") == "BANK":
        paid = calculate_emis_paid(loan)
        elapsed = calculate_emis_elapsed(loan)
        if elapsed > 0 and paid / elapsed < 0.5:
            return "🟡 Early Stage"

    return "🟢 On Track"

# ==================================================
# SHARED OUTSTANDING HELPERS (SINGLE SOURCE OF TRUTH)
# ==================================================

def loan_outstanding_principal(loan):
    """
    Calm default: principal only
    """
    return round(float(loan.get("principal", 0)), 2)


def loan_total_cost(loan):
    """
    Principal + remaining interest (BANK loans only)
    """
    if loan.get("loan_type") != "BANK":
        return loan_outstanding_principal(loan)

    try:
        schedule, rem_principal = build_amortization_schedule(loan)
        rem_interest = sum(r.get("interest", 0) for r in schedule)
    except Exception:
        rem_principal = loan.get("principal", 0)
        rem_interest = 0

    return round(rem_principal + rem_interest, 2)

# ==================================================
# PORTFOLIO-LEVEL METRICS
# ==================================================
def portfolio_summary(loans: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_outstanding = 0.0
    total_monthly = 0.0
    overdue_count = 0
    family_interest_due = 0.0

    for loan in loans:
        total_outstanding += loan_outstanding(loan)
        total_monthly += loan_monthly_commitment(loan)

        if loan.get("loan_type") == "BANK":
            if calculate_emis_overdue(loan) > 0:
                overdue_count += 1
        else:
            family_interest_due += loan_monthly_commitment(loan)

    return {
        "total_outstanding": round(total_outstanding, 2),
        "total_monthly": round(total_monthly, 2),
        "overdue_loans": overdue_count,
        "family_interest_due": round(family_interest_due, 2),
    }


# ==================================================
# 🧠 GENTLE INSIGHT (ONE-LINER)
# ==================================================
def next_gentle_action(summary: Dict[str, Any]) -> str:
    if summary["overdue_loans"] > 0:
        return "Clear one overdue EMI to immediately reduce stress."

    if summary["total_monthly"] == 0:
        return "No monthly burden right now — good time to plan or prepay."

    if summary["total_monthly"] > summary["total_outstanding"] * 0.03:
        return "Monthly load is high — a small prepayment could help."

    return "You’re on track. Stay consistent."
