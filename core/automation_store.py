# core/automation_store.py

from hmac import digest
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

from core.daily_digest import generate_daily_digest
from core.digest_store import save_digest

AUTOMATION_FILE = Path("data/automations.json")

DEFAULT_AUTOMATIONS = [
    {
        "id": "DAILY_DIGEST",
        "name": "Daily Digest",
        "description": "Generate your daily health, finance & career summary.",
        "enabled": True,
        "last_run": None,
    }
]
# ==================================================
# PATHS
# ==================================================
AUTOMATION_FILE = Path("data/automations.json")


def _ensure_dirs():
    AUTOMATION_FILE.parent.mkdir(parents=True, exist_ok=True)

# ==================================================
# STORAGE
# ==================================================

def _ensure_file():
    AUTOMATION_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not AUTOMATION_FILE.exists():
        with open(AUTOMATION_FILE, "w") as f:
            json.dump(DEFAULT_AUTOMATIONS, f, indent=2)


def _load() -> List[Dict[str, Any]]:
    _ensure_file()
    with open(AUTOMATION_FILE, "r") as f:
        data = json.load(f)

    cleaned: List[Dict[str, Any]] = []

    # -------------------------------
    # Normalize into flat list[dict]
    # -------------------------------
    if isinstance(data, dict):
        data = list(data.values())

    if isinstance(data, list):
        for item in data:
            # Flatten nested lists
            if isinstance(item, list):
                for sub in item:
                    if isinstance(sub, dict):
                        cleaned.append(sub)
            elif isinstance(item, dict):
                cleaned.append(item)

    # Fallback safety
    if not cleaned:
        cleaned = DEFAULT_AUTOMATIONS.copy()
        _save(cleaned)

    return cleaned

def _save(data: List[Dict[str, Any]]):
    with open(AUTOMATION_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ==================================================
# PUBLIC API
# ==================================================

def list_automations():
    """
    Load automations safely.
    Auto-recovers from corrupt or missing file.
    """
    _ensure_dirs()

    if not AUTOMATION_FILE.exists():
        save_automations([])
        return []

    try:
        with open(AUTOMATION_FILE, "r") as f:
            data = json.load(f)

        # Ensure list structure
        if not isinstance(data, list):
            raise ValueError("Invalid automations format")

        return data

    except Exception:
        # Corrupt file → auto-reset
        save_automations([])
        return []


def toggle_automation(auto_id: str, enabled: bool):
    autos = _load()

    for a in autos:
        if a["id"] == auto_id:
            a["enabled"] = enabled

    _save(autos)


def update_last_run(auto_id: str):
    autos = _load()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    for a in autos:
        if a["id"] == auto_id:
            a["last_run"] = now

    _save(autos)


# ==================================================
# 🚀 RUNNERS
# ==================================================

def run_daily_digest():
    """
    Generate daily digest snapshot.
    Always returns digest payload.
    Automation only controls persistence / scheduling.
    """
    from core.daily_digest import generate_daily_digest

    # Always generate digest
    digest = generate_daily_digest()

    autos = list_automations()
    digest_auto = next(
        (a for a in autos if isinstance(a, dict) and a.get("id") == "DAILY_DIGEST"),
        None
    )

    # Only persist metadata if enabled
    if digest_auto and digest_auto.get("enabled", True):
        digest_auto["last_run"] = digest["timestamp"]
        save_automations(autos)

    return digest   # ✅ ALWAYS RETURN


def should_run_daily(auto: dict) -> bool:
    """
    Placeholder for scheduler logic.
    Later we can check last_run vs time-of-day.
    """
    return auto.get("enabled", True)
def save_automations(autos):
    """
    Persist automations list to disk safely.
    """
    _ensure_dirs()
    with open(AUTOMATION_FILE, "w") as f:
        json.dump(autos, f, indent=2)
