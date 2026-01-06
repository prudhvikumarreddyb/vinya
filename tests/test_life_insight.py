from datetime import date, timedelta
from core.health_store import save_health
from core.finance_store import save_finance
from core.life_store import gentle_life_insight

def test_heavy_week_blocks_big_decisions():
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

    save_finance({
        "loans": [
            {
                "name": "Test Loan",
                "principal": 500000,
                "rate": 12,
                "emi": 25000,
                "tenure": 24,
                "loan_type": "BANK",
                "payments": [],
                "start_date": date.today().isoformat(),
            }
        ]
    })

    insight = gentle_life_insight()
    assert insight is not None
    assert "avoid" in insight.lower()
