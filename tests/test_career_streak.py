from datetime import date, timedelta
import tempfile
from pathlib import Path

import core.career_store as career


def test_practice_streak_and_growth_signal(monkeypatch):
    """
    Regression test:
    - 3 consecutive practice days
    - streak should be 3
    - weekly status should not be STALLING
    """

    # --------------------------------------------------
    # Redirect career data file to temp directory
    # --------------------------------------------------
    tmp_dir = tempfile.TemporaryDirectory()
    data_file = Path(tmp_dir.name) / "career.json"

    monkeypatch.setattr(
        career,
        "CAREER_DATA_FILE",
        data_file
    )

    # --------------------------------------------------
    # Log 3 consecutive days of practice
    # --------------------------------------------------
    today = date.today()

    career.log_practice(30, "Python", entry_date=today)
    career.log_practice(45, "System Design", entry_date=today - timedelta(days=1))
    career.log_practice(20, "Algorithms", entry_date=today - timedelta(days=2))

    # --------------------------------------------------
    # Validate streak
    # --------------------------------------------------
    streak = career.practice_streak()
    assert streak == 3

    # --------------------------------------------------
    # Validate weekly signal
    # --------------------------------------------------
    signal = career.weekly_growth_signal()

    assert signal["total_minutes"] > 0
    assert signal["status"] != "STALLING"
    assert signal["streak"] == 3

    tmp_dir.cleanup()
