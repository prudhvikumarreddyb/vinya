from core.health_store import weekly_health_recap
from core.finance_store import dashboard_summary

def gentle_life_insight():
    """
    Returns a single gentle insight string or None.
    """
    health = weekly_health_recap()
    finance = dashboard_summary()

    if not health or not finance:
        return None

    if (
        health["stress_pattern"] == "overwhelmed"
        and finance["status"] in ["TIGHT", "CRITICAL"]
    ):
        return (
            "This has been a heavy week. "
            "If possible, avoid major financial decisions right now."
        )

    if health["stress_pattern"] == "calm" and finance["status"] == "SAFE":
        return "Good week for planning or small optimizations."

    return None
