# core/digest_store.py

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List

DIGEST_FILE = Path("data/digests.json")


# ---------------------------
# Internal helpers
# ---------------------------
def _ensure_file():
    DIGEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not DIGEST_FILE.exists():
        DIGEST_FILE.write_text("[]")


def _load() -> List[Dict]:
    _ensure_file()
    try:
        return json.loads(DIGEST_FILE.read_text())
    except Exception:
        return []


def _save(rows: List[Dict]):
    DIGEST_FILE.write_text(json.dumps(rows, indent=2))


# ---------------------------
# Public API
# ---------------------------
def save_digest(digest: Dict):
    rows = _load()

    digest = {
        **digest,
        "saved_at": datetime.utcnow().isoformat()
    }

    rows.append(digest)

    # keep last 30 only
    rows = rows[-30:]

    _save(rows)


def list_digests() -> List[Dict]:
    return _load()


def latest_digest() -> Dict | None:
    rows = _load()
    return rows[-1] if rows else None
