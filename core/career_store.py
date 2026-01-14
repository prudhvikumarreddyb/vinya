"""
Career data + intelligence engine for Vinya
Single source of truth.
"""

import json
from pathlib import Path
from datetime import date, datetime, timedelta
from collections import Counter
from typing import Dict, List

# ==================================================
# STORAGE
# ==================================================
CAREER_DATA_FILE = Path("data/career.json")


def _safe_default():
    return {
        "logs": []  # each: {date, minutes, area, note}
    }


def _ensure_dir():
    CAREER_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_career():
    _ensure_dir()

    if not CAREER_DATA_FILE.exists():
        save_career(_safe_default())

    try:
        with open(CAREER_DATA_FILE, "r") as f:
            return json.load(f)
    except Exception:
        save_career(_safe_default())
        return _safe_default()


def save_career(data):
    _ensure_dir()
    with open(CAREER_DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ==================================================
# WRITE OPERATIONS
# ==================================================
def log_practice(minutes: int, area: str, note: str = "", entry_date: date = None):
    if minutes <= 0:
        raise ValueError("Minutes must be positive")

    if not area:
        raise ValueError("Area is required")

    if entry_date is None:
        entry_date = date.today()

    data = load_career()

    data["logs"].append({
        "date": entry_date.isoformat(),
        "minutes": int(minutes),
        "area": area,
        "note": note,
    })

    save_career(data)


# ==================================================
# READ HELPERS
# ==================================================
def _parse_date(d):
    return datetime.fromisoformat(d).date()


def all_logs():
    data = load_career()
    return data.get("logs", [])


def logs_between(start: date, end: date):
    return [
        l for l in all_logs()
        if start <= _parse_date(l["date"]) <= end
    ]


def weekly_logs(ref: date = None):
    if ref is None:
        ref = date.today()

    start = ref - timedelta(days=6)
    return logs_between(start, ref)


def previous_week_logs(ref: date = None):
    if ref is None:
        ref = date.today()

    end = ref - timedelta(days=7)
    start = end - timedelta(days=6)
    return logs_between(start, end)


# ==================================================
# METRICS
# ==================================================
def total_minutes(logs: List[Dict]) -> int:
    return sum(l.get("minutes", 0) for l in logs)


def active_days(logs: List[Dict]) -> int:
    return len(set(l["date"] for l in logs))


def top_focus_area(logs: List[Dict]):
    if not logs:
        return None

    counter = Counter(l["area"] for l in logs)
    return counter.most_common(1)[0][0]


def practice_streak() -> int:
    """
    Consecutive days with at least one log.
    """
    logs = all_logs()
    if not logs:
        return 0

    days = sorted({ _parse_date(l["date"]) for l in logs }, reverse=True)

    streak = 0
    cursor = date.today()

    for d in days:
        if d == cursor:
            streak += 1
            cursor -= timedelta(days=1)
        else:
            break

    return streak


# ==================================================
# INTELLIGENCE
# ==================================================
def weekly_growth_signal():
    current = weekly_logs()
    previous = previous_week_logs()

    current_minutes = total_minutes(current)
    previous_minutes = total_minutes(previous)

    days = active_days(current)

    if current_minutes == 0:
        status = "STALLING"
        message = "No practice logged this week yet."
    elif previous_minutes == 0:
        status = "GROWING"
        message = "Great start — you’re building momentum."
    elif current_minutes > previous_minutes * 1.1:
        status = "GROWING"
        message = "Nice! You’re improving your weekly consistency."
    elif current_minutes < previous_minutes * 0.9:
        status = "STALLING"
        message = "Activity dipped slightly — a small push helps."
    else:
        status = "STABLE"
        message = "Good steady progress. Keep rhythm."

    return {
        "status": status,
        "message": message,
        "total_minutes": current_minutes,
        "active_days": days,
        "top_focus": top_focus_area(current),
        "streak": practice_streak(),
    }


def balance_score(logs: List[Dict]) -> float:
    """
    1.0 = perfectly balanced across areas
    0.0 = all time in one area
    """
    if not logs:
        return 0

    counter = Counter(l["area"] for l in logs)
    total = sum(counter.values())
    dominant = max(counter.values())

    return round(1 - (dominant / total), 2)


def gentle_insight():
    signal = weekly_growth_signal()

    if signal["status"] == "STALLING":
        return "Tiny progress beats zero. Even 15 minutes compounds."

    if signal["streak"] >= 5:
        return "Strong streak building. Protect this rhythm."

    if signal["top_focus"]:
        return f"Most energy went into **{signal['top_focus']}** this week."

    return "Steady growth is happening quietly."


def gentle_nudge():
    signal = weekly_growth_signal()

    if signal["status"] == "STALLING":
        return "Schedule one short focused session today."

    if signal["streak"] >= 3:
        return "Keep the streak alive — even 20 mins is enough."

    return "Pick one small improvement task and start."


