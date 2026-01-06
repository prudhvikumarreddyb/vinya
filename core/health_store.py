# core/health_store.py
"""
Health v0.1 – Signal-based health tracking for Vinya

Philosophy:
- Very small inputs
- No goals, no scores
- Gentle insights only
"""


import json
from pathlib import Path
from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Optional

# ==================================================
# PATH
# ==================================================
HEALTH_DATA_FILE = Path("data/health.json")

# ==================================================
# CONSTANTS (SCHEMA)
# ==================================================
SLEEP_LEVELS = {"4-5", "5-6", "6-7", "7-8", "8+"}
ENERGY_LEVELS = {"low", "okay", "high"}
STRESS_LEVELS = {"calm", "manageable", "overwhelmed"}


# ==================================================
# PATHS
# ==================================================
DATA_FILE = Path("data/health.json")
HEALTH_DATA_FILE = Path("data/health.json")

# ==================================================
# INTERNAL HELPERS
# ==================================================
def _ensure_file():
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        with open(DATA_FILE, "w") as f:
            json.dump({"entries": []}, f, indent=2)


def _load_raw() -> Dict:
    _ensure_file()
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def _save_raw(data: Dict):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _today_str() -> str:
    return date.today().isoformat()
def _safe_default() -> Dict[str, Any]:
    return {"entries": [], "insights": []}

def _ensure_dir():
    HEALTH_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

def _parse_date(d: str):
    try:
        return datetime.fromisoformat(d).date()
    except Exception:
        return None
# ==================================================
# LOAD / SAVE (VALIDATED)
# ==================================================
def load_health() -> Dict[str, Any]:
    _ensure_dir()

    if not HEALTH_DATA_FILE.exists():
        save_health(_safe_default())

    try:
        with open(HEALTH_DATA_FILE, "r") as f:
            data = json.load(f)
    except Exception:
        data = _safe_default()
        save_health(data)

    # ---- VALIDATE STRUCTURE ----
    data.setdefault("entries", [])
    data.setdefault("insights", [])

    validated_entries = []
    for e in data["entries"]:
        if not isinstance(e, dict):
            continue

        d = _parse_date(e.get("date", ""))
        if not d:
            continue

        sleep = e.get("sleep")
        energy = e.get("energy")
        stress = e.get("stress")

        if sleep not in SLEEP_LEVELS:
            continue
        if energy not in ENERGY_LEVELS:
            continue
        if stress not in STRESS_LEVELS:
            continue

        validated_entries.append({
            "date": d.isoformat(),
            "sleep": sleep,
            "energy": energy,
            "stress": stress,
            "movement": bool(e.get("movement", False)),
            "notes": e.get("notes", "")
        })

    data["entries"] = validated_entries
    save_health(data)
    return data

def save_health(data: Dict[str, Any]) -> None:
    _ensure_dir()
    with open(HEALTH_DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)
# ==================================================
# CORE LOGIC
# ==================================================
def last_n_entries(n: int = 3) -> List[Dict[str, Any]]:
    data = load_health()
    entries = sorted(
        data["entries"],
        key=lambda e: e["date"],
        reverse=True
    )
    return entries[:n]

def health_signal_today() -> Dict[str, str]:
    recent = last_n_entries(3)

    if len(recent) < 2:
        return {
            "status": "BALANCE",
            "message": "Not enough data. Log gently."
        }

    low_sleep = all(e["sleep"] in {"4-5", "5-6"} for e in recent)
    overwhelmed = all(e["stress"] == "overwhelmed" for e in recent)

    if low_sleep and overwhelmed:
        _append_insight("PROTECT", "Protect energy today. Reduce load.")
        return {
            "status": "PROTECT",
            "message": "Protect energy today. Reduce load."
        }

    return {
        "status": "BALANCE",
        "message": "You’re okay. Keep balance."
    }
# ==================================================
# STREAKS (READ-ONLY)
# ==================================================
def health_streaks():
    """
    Returns current streaks for:
    - sleep (6-7 or better)
    - movement (True)
    """
    data = load_health()
    entries = sorted(
        data.get("entries", []),
        key=lambda e: e["date"],
        reverse=True
    )

    sleep_streak = 0
    movement_streak = 0

    # ---- Sleep streak ----
    for e in entries:
        if e["sleep"] in {"6-7", "7-8", "8+"}:
            sleep_streak += 1
        else:
            break

    # ---- Movement streak ----
    for e in entries:
        if e.get("movement") is True:
            movement_streak += 1
        else:
            break

    return {
        "sleep_streak": sleep_streak,
        "movement_streak": movement_streak
    }

def _append_insight(kind: str, message: str):
    data = load_health()
    today = date.today().isoformat()

    # prevent duplicate same-day insight
    for i in data["insights"]:
        if i["date"] == today and i["type"] == kind:
            return

    data["insights"].append({
        "date": today,
        "type": kind,
        "message": message
    })
    save_health(data)
# ==================================================
# ENTRY OPERATIONS
# ==================================================
def get_today_entry() -> Optional[Dict]:
    data = load_health()
    for e in data.get("entries", []):
        if e.get("date") == _today_str():
            return e
    return None


def add_today_entry(
    sleep: str,
    energy: str,
    stress: str,
    movement: bool
):
    """
    Add today's health entry.
    One entry per day (enforced).
    """
    data = load_health()

    if get_today_entry():
        raise ValueError("Today's health entry already exists")

    entry = {
        "date": _today_str(),
        "sleep": sleep,         # "<5", "5-6", "6-7", "7+"
        "energy": energy,       # "low", "okay", "good"
        "stress": stress,       # "calm", "busy", "overwhelmed"
        "movement": movement    # bool
    }

    data.setdefault("entries", []).append(entry)
    save_health(data)

# ==================================================
# DERIVED SIGNALS
# ==================================================
def recent_entries(days: int = 7) -> List[Dict]:
    """
    Get last N days of entries (most recent last).
    """
    data = load_health()
    entries = sorted(
        data.get("entries", []),
        key=lambda e: e.get("date", "")
    )
    return entries[-days:]


def health_signal_today() -> Dict:
    """
    Returns a simple status + message for today.
    """
    entries = recent_entries(3)

    if not entries:
        return {
            "status": "UNKNOWN",
            "message": "No health data yet."
        }

    low_sleep_streak = sum(
        1 for e in entries if e.get("sleep") in ("<5", "5-6")
    )

    high_stress = any(
        e.get("stress") == "overwhelmed" for e in entries
    )

    low_energy = sum(
        1 for e in entries if e.get("energy") == "low"
    )

    if high_stress and low_energy >= 2:
        return {
        "status": "PROTECT",
        "message": "Protect today: high load detected. Go gently.",
        "reason": "low_sleep_high_stress"
    }


    if low_sleep_streak >= 3:
        return {
            "status": "WATCH",
            "message": "Low sleep streak. Expect lower focus."
        }

    return {
        "status": "STABLE",
        "message": "Health signals look stable today."
    }

# ==================================================
# INSIGHTS (GENTLE, 1-LINE)
# ==================================================
def generate_insights() -> Optional[Dict]:
    """
    Generate at most ONE gentle insight.
    Called once per day (read-only history).
    """
    entries = recent_entries(7)
    if len(entries) < 3:
        return None

    # Rule 1: No movement 3 days
    no_move = sum(1 for e in entries[-3:] if not e.get("movement"))
    if no_move == 3:
        return {
            "date": _today_str(),
            "insight": "No movement for a few days. A short walk may help."
        }

    # Rule 2: High stress + low energy
    stressed = any(e.get("stress") == "overwhelmed" for e in entries[-3:])
    low_energy = sum(1 for e in entries[-3:] if e.get("energy") == "low") >= 2
    if stressed and low_energy:
        return {
            "date": _today_str(),
            "insight": "High mental load detected. Avoid big decisions today."
        }

    # Rule 3: Good zone
    good_days = sum(
        1 for e in entries[-3:]
        if e.get("energy") == "good" and e.get("stress") == "calm"
    )
    if good_days >= 2:
        return {
            "date": _today_str(),
            "insight": "You’ve been in a good zone recently. Use it wisely."
        }

    return None

# ==================================================
# INSIGHT HISTORY (READ-ONLY)
# ==================================================
def get_insight_history() -> List[Dict]:
    """
    Collect insights without duplication.
    """
    data = load_health()
    return data.get("insights", [])


def maybe_store_insight():
    """
    Generate and store today's insight (once).
    Safe to call multiple times.
    """
    data = load_health()
    insights = data.setdefault("insights", [])

    today = _today_str()
    if any(i.get("date") == today for i in insights):
        return

    insight = generate_insights()
    if insight:
        insights.append(insight)
        save_health(data)
def health_today_summary():
    """
    Single source of truth for dashboard & health page.
    """
    signal = health_signal_today()

    return {
        "status": signal["status"],   # PROTECT / STEADY / BUILD
        "message": signal["message"],
        "color": {
            "PROTECT": "#fdecea",
            "STEADY": "#fff8e1",
            "BUILD": "#e8f5e9"
        }.get(signal["status"], "#f5f5f5")
    }
def quick_log_today(
    sleep: str = None,
    energy: str = None,
    stress: str = None,
    movement: bool = None
):
    """
    Fast, partial log for today.
    Missing fields are allowed.
    """
    data = load_health()
    today = date.today().isoformat()

    # Prevent duplicate entry
    for e in data["entries"]:
        if e.get("date") == today:
            return False

    data["entries"].append({
        "date": today,
        "sleep": sleep,
        "energy": energy,
        "stress": stress,
        "movement": movement,
    })

    save_health(data)
    return True
    data["insights"].append({
        "date": date.today().isoformat(),
        "status": signal["status"],
        "message": signal["message"]
    })
    save_health(data)
def protect_streak(days: int = 3) -> bool:
    data = load_health()
    recent = data.get("insights", [])[-days:]

    if len(recent) < days:
        return False

    return all(i["status"] == "PROTECT" for i in recent)
def upsert_health_entry(entry: dict):
    """
    Insert or update a health entry by date.
    Date (YYYY-MM-DD) is the primary key.
    """
    data = load_health()
    date_key = entry.get("date")

    if not date_key:
        raise ValueError("Health entry must include a date")

    updated = False
    for i, e in enumerate(data["entries"]):
        if e.get("date") == date_key:
            data["entries"][i] = entry
            updated = True
            break

    if not updated:
        data["entries"].append(entry)

    # Keep entries sorted (old → new)
    data["entries"] = sorted(
        data["entries"],
        key=lambda x: x.get("date", "")
    )

    save_health(data)
def weekly_health_recap():
    """
    Returns weekly recap dict if today is Sunday, else None.
    """
    today = date.today()
    if today.weekday() != 6:  # Sunday
        return None

    data = load_health()
    last_7 = data.get("entries", [])[-7:]

    if not last_7:
        return None

    stress_counts = {
        "calm": 0,
        "busy": 0,
        "overwhelmed": 0
    }

    sleep_low_days = 0

    for e in last_7:
        stress = e.get("stress")
        if stress in stress_counts:
            stress_counts[stress] += 1

        if e.get("sleep") in ["<5", "5-6"]:
            sleep_low_days += 1

    dominant_stress = max(stress_counts, key=stress_counts.get)

    message = "You showed up consistently this week."

    if dominant_stress == "overwhelmed" or sleep_low_days >= 3:
        message = (
            "This week carried a lot. "
            "Next week, protect rest and reduce non-essential load."
        )
    elif dominant_stress == "calm":
        message = "You found steadiness this week. Keep protecting it."

    return {
        "week_ending": today.isoformat(),
        "message": message,
        "stress_pattern": dominant_stress,
        "low_sleep_days": sleep_low_days
    }
def health_dashboard_card():
    """
    Minimal snapshot for dashboard.
    Never writes data.
    """
    signal = health_signal_today()

    return {
        "status": signal["status"],
        "message": signal["message"]
    }
