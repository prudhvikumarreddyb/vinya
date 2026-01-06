from datetime import date, timedelta
from core.health_store import weekly_health_recap, save_health

def test_weekly_recap_only_on_sunday(monkeypatch):
    monkeypatch.setattr("core.health_store.date", date)

    save_health({
        "entries": [
            {
                "date": (date.today() - timedelta(days=i)).isoformat(),
                "sleep": "5-6",
                "stress": "overwhelmed",
                "energy": "low",
                "movement": False,
            }
            for i in range(7)
        ],
        "insights": []
    })

    recap = weekly_health_recap()
    if date.today().weekday() == 6:
        assert recap is not None
    else:
        assert recap is None
