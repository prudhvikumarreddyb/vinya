from core.health_store import weekly_health_recap
from core.finance_store import dashboard_summary
from datetime import date, timedelta
from core.health_store import load_health
from core.finance_store import load_finance


def gentle_life_insight():
    """
    Cross-domain gentle safety insight.
    Heavy health load + financial pressure → avoid big decisions.
    """

    # -------------------------
    # Load health (last 7 days)
    # -------------------------
    health = load_health()
    entries = health.get("entries", [])

    last_7_days = {
        (date.today() - timedelta(days=i)).isoformat()
        for i in range(7)
    }

    recent = [
        e for e in entries
        if e.get("date") in last_7_days
    ]

    if len(recent) < 5:
        return None  # not enough signal yet

    heavy_days = sum(
        1
        for e in recent
        if e.get("stress") == "overwhelmed"
        or e.get("sleep") in ("0-4", "5-6")
    )

    heavy_week = heavy_days >= 4

    # -------------------------
    # Load finance pressure
    # -------------------------
    finance = load_finance()
    loans = finance.get("loans", [])

    total_emi = sum(
        l.get("emi", 0)
        for l in loans
        if l.get("loan_type") == "BANK"
    )

    financial_pressure = total_emi > 20000

    # -------------------------
    # Cross-domain insight
    # -------------------------
    if heavy_week and financial_pressure:
        return (
            "⚠️ You’ve had a heavy health week and financial load is meaningful. "
            "Avoid big decisions, commitments, or risky changes right now. "
            "Stabilize first."
        )

    return None
