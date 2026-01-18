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
def _new_id(prefix: str):
    return f"{prefix}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S-%f')}"

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
"""
Career Store — Vinya v1
Manages:
- Education
- Work Experience
- Skills
- Career meta

Single source of truth for career profile.
"""

import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import uuid

# ==================================================
# PATHS
# ==================================================
CAREER_DATA_FILE = Path("data/career.json")
BACKUP_DIR = Path("data/backups")
MAX_BACKUPS = 10


# ==================================================
# INTERNAL HELPERS
# ==================================================
def _ensure_dirs():
    CAREER_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def _timestamp():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def _safe_default():
    return {
        "profile": {
            "name": "",
            "headline": "",
            "summary": ""
        },
        "education": [],
        "work": [],
        "skills": [],
        "meta": {
            "version": "career-v1",
            "last_updated": None
        }
    }


def _atomic_write(data: Dict[str, Any]):
    tmp = CAREER_DATA_FILE.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, default=str)
    tmp.replace(CAREER_DATA_FILE)


def _create_backup(tag="auto"):
    if CAREER_DATA_FILE.exists():
        name = f"career_{_timestamp()}_{tag}.json"
        shutil.copy2(CAREER_DATA_FILE, BACKUP_DIR / name)

        backups = sorted(BACKUP_DIR.glob("career_*.json"))
        if len(backups) > MAX_BACKUPS:
            for old in backups[:-MAX_BACKUPS]:
                try:
                    old.unlink()
                except Exception:
                    pass


def _validate_schema(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensures required top-level keys exist and types are sane.
    Auto-heals if possible.
    """
    changed = False

    if "education" not in data or not isinstance(data["education"], list):
        data["education"] = []
        changed = True

    if "work" not in data or not isinstance(data["work"], list):
        data["work"] = []
        changed = True

    if "skills" not in data or not isinstance(data["skills"], list):
        data["skills"] = []
        changed = True

    if "meta" not in data or not isinstance(data["meta"], dict):
        data["meta"] = {}
        changed = True

    data["meta"].setdefault("version", "career-v1")
    data["meta"].setdefault("last_updated", None)

    if changed:
        data["meta"]["last_updated"] = datetime.utcnow().isoformat()

    return data


# ==================================================
# LOAD / SAVE
# ==================================================
def load_career() -> Dict[str, Any]:
    _ensure_dirs()

    if not CAREER_DATA_FILE.exists():
        _atomic_write(_safe_default())

    try:
        with open(CAREER_DATA_FILE, "r") as f:
            data = json.load(f)
    except Exception:
        _create_backup(tag="corrupt")
        data = _safe_default()
        _atomic_write(data)

    data = _validate_schema(data)
    return data


def save_career(data: Dict[str, Any], tag="auto"):
    _ensure_dirs()
    _create_backup(tag=tag)

    data["meta"]["last_updated"] = datetime.utcnow().isoformat()
    data = _validate_schema(data)

    _atomic_write(data)


# ==================================================
# ID GENERATOR
# ==================================================
def _new_id(prefix: str):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


# ==================================================
# EDUCATION
# ==================================================
def add_education(
    degree: str,
    field: str,
    institution: str,
    start_year: int,
    end_year: int | None = None,
    score: str | None = None,
    notes: str | None = None,
):
    data = load_career()

    entry = {
        "id": _new_id("edu"),
        "degree": degree.strip(),
        "field": field.strip(),
        "institution": institution.strip(),
        "start_year": int(start_year),
        "end_year": int(end_year) if end_year else None,
        "score": score,
        "notes": notes,
    }

    data["education"].append(entry)
    save_career(data, tag="add_education")


def delete_education(edu_id: str):
    data = load_career()
    before = len(data["education"])
    data["education"] = [e for e in data["education"] if e["id"] != edu_id]

    if len(data["education"]) != before:
        save_career(data, tag="delete_education")


# ==================================================
# WORK EXPERIENCE
# ==================================================
def add_work(
    company: str,
    role: str,
    start_date: str,     # YYYY-MM
    end_date: str | None = None,
    current: bool = False,
    location: str | None = None,
    tech_stack: List[str] | None = None,
    achievements: List[str] | None = None,
    impact_tags: List[str] | None = None,
):
    data = load_career()

    entry = {
        "id": _new_id("work"),
        "company": company.strip(),
        "role": role.strip(),
        "start_date": start_date,
        "end_date": end_date,
        "current": bool(current),
        "location": location,
        "tech_stack": tech_stack or [],
        "achievements": achievements or [],
        "impact_tags": impact_tags or [],
    }

    # Auto-unset other "current" roles if this is current
    if current:
        for w in data["work"]:
            w["current"] = False

    data["work"].append(entry)
    save_career(data, tag="add_work")


def delete_work(work_id: str):
    data = load_career()
    before = len(data["work"])
    data["work"] = [w for w in data["work"] if w["id"] != work_id]

    if len(data["work"]) != before:
        save_career(data, tag="delete_work")

def migrate_missing_skill_ids(data):
    changed = False

    for skill in data.get("skills", []):
        if "id" not in skill:
            skill["id"] = _new_id("SKILL")
            changed = True

    if changed:
        save_career(data, tag="migrate_skill_ids")

# ==================================================
# SKILLS
# ==================================================
def add_skill(
    name: str,
    category: str,
    level: str,
    last_used: str | None = None,
    evidence: List[str] | None = None,
):
    data = load_career()

    entry = {
        "id": _new_id("skill"),
        "name": name.strip(),
        "category": category.strip(),
        "level": level,
        "last_used": last_used,
        "evidence": evidence or [],
    }

    data["skills"].append(entry)
    save_career(data, tag="add_skill")


def delete_skill(skill_id):
    data = load_career()

    cleaned = []
    for s in data.get("skills", []):
        sid = s.get("id") or s.get("name")   # 👈 fallback for old data

        if sid != skill_id:
            cleaned.append(s)

    data["skills"] = cleaned
    save_career(data)



# ==================================================
# READ HELPERS (FOR UI / RESUME ENGINE LATER)
# ==================================================
def list_education() -> List[Dict[str, Any]]:
    return load_career().get("education", [])


def list_work() -> List[Dict[str, Any]]:
    return load_career().get("work", [])


def list_skills() -> List[Dict[str, Any]]:
    return load_career().get("skills", [])


def current_role():
    work = load_career().get("work", [])
    for w in work:
        if w.get("current"):
            return w
    return None
# ==================================================
# PROFILE
# ==================================================

def update_profile(name: str, headline: str, summary: str):
    data = load_career()

    data["profile"] = {
        "name": name.strip(),
        "headline": headline.strip(),
        "summary": summary.strip(),
    }

    save_career(data, tag="update_profile")


def get_profile():
    data = load_career()
    return data.get("profile", {})


