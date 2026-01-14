# core/daily_digest.py
"""
Daily Digest Generator for Vinya

Pure logic only.
No UI. No Streamlit. No side-effects.

Builds a single daily snapshot combining:
- Health signal
- Finance summary
- Career nudge
- Gentle action
"""

from datetime import datetime
from pathlib import Path
import json
from core.health_store import health_signal_today
from core.finance_store import dashboard_summary, load_finance
from core.finance_metrics import portfolio_summary, next_gentle_action
from core.career_store import gentle_nudge


# ==================================================
# DIGEST GENERATOR
# ==================================================

def generate_daily_digest() -> dict:
    """
    Returns a structured daily digest snapshot.
    """

    # ---------------- Health ----------------
    health = health_signal_today()

    # ---------------- Finance ----------------
    finance_raw = dashboard_summary()

    data = load_finance()
    loans = data.get("loans", [])
    portfolio = portfolio_summary(loans) if loans else {}

    gentle_action = next_gentle_action(portfolio) if loans else "No financial actions today."

    # ---------------- Career ----------------
    career = gentle_nudge()

    # ---------------- Digest ----------------
    digest = {
        "timestamp": datetime.now().isoformat(timespec="minutes"),
        "health": {
            "status": health.get("status"),
            "message": health.get("message"),
        },
        "finance": {
            "status": finance_raw.get("status"),
            "message": finance_raw.get("message"),
            "total_outstanding": finance_raw.get("total_outstanding"),
        },
        "career": {
            "nudge": career,
        },
        "gentle_action": gentle_action,
    }

    return digest


# ==================================================
# LOCAL TEST RUN (optional)
# ==================================================

if __name__ == "__main__":
    from pprint import pprint

    pprint(generate_daily_digest())

def load_latest_digest():
    path = Path("data/digests.json")
    if not path.exists():
        return None

    try:
        with open(path, "r") as f:
            digests = json.load(f)
    except Exception:
        return None

    if not digests:
        return None

    return digests[-1]
