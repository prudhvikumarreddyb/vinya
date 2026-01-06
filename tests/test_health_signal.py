# tests/test_health_signal.py

from datetime import date, timedelta

from core.health_store import (
    load_health,
    save_health,
    health_signal_today,
)

DATA_TEMPLATE = {
    "entries": [],
    "insights": []
}


def test_low_sleep_and_high_stress_triggers_protect(tmp_path, monkeypatch):
    """
    Regression test:
    sleep <6h + stress = overwhelmed → PROTECT
    """

    # --------------------------------------------------
    # Redirect data file to temp directory
    # --------------------------------------------------
    data_file = tmp_path / "health.json"

    monkeypatch.setattr(
        "core.health_store.HEALTH_DATA_FILE",
        data_file
    )

    # --------------------------------------------------
    # Prepare test data (last 3 days)
    # --------------------------------------------------
    today = date.today()

    entries = [
        {
            "date": (today - timedelta(days=2)).isoformat(),
            "sleep": "5-6",
            "energy": "low",
            "stress": "overwhelmed",
            "movement": False,
        },
        {
            "date": (today - timedelta(days=1)).isoformat(),
            "sleep": "5-6",
            "energy": "okay",
            "stress": "overwhelmed",
            "movement": False,
        },
        {
            "date": today.isoformat(),
            "sleep": "5-6",
            "energy": "low",
            "stress": "overwhelmed",
            "movement": False,
        },
    ]

    save_health({
        "entries": entries,
        "insights": []
    })

    # --------------------------------------------------
    # Assert signal
    # --------------------------------------------------
    signal = health_signal_today()

    assert signal["status"] == "PROTECT"
    assert "protect" in signal["message"].lower()
