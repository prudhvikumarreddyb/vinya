# tests/test_daily_digest.py

from datetime import datetime

from core.automation_store import run_daily_digest


def test_daily_digest_runs_and_has_required_fields():
    """
    Regression test:
    - Daily digest runs without crashing
    - Required sections exist
    - Timestamp is valid ISO format
    """

    digest = run_daily_digest()

    # -----------------------------
    # Basic structure checks
    # -----------------------------
    assert isinstance(digest, dict)

    assert "timestamp" in digest
    assert "health" in digest
    assert "finance" in digest
    assert "career" in digest
    assert "gentle_action" in digest

    # -----------------------------
    # Timestamp validation
    # -----------------------------
    # Should not raise
    datetime.fromisoformat(digest["timestamp"])

    # -----------------------------
    # Health block
    # -----------------------------
    health = digest["health"]
    assert "status" in health
    assert "message" in health

    # -----------------------------
    # Finance block
    # -----------------------------
    finance = digest["finance"]
    assert "status" in finance
    assert "total_outstanding" in finance

    # -----------------------------
    # Career block
    # -----------------------------
    career = digest["career"]
    assert "nudge" in career

    # -----------------------------
    # Gentle action sanity
    # -----------------------------
    assert isinstance(digest["gentle_action"], str)
    assert len(digest["gentle_action"]) > 0
