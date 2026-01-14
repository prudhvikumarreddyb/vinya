import json
from pathlib import Path
from core.automation_store import list_automations, AUTOMATION_FILE


def test_corrupt_automation_file_recovers(tmp_path, monkeypatch):
    fake_file = tmp_path / "automations.json"

    monkeypatch.setattr(
        "core.automation_store.AUTOMATION_FILE",
        fake_file
    )

    # Write corrupt data
    fake_file.parent.mkdir(parents=True, exist_ok=True)
    fake_file.write_text("{broken json")

    autos = list_automations()

    assert autos == []
    assert json.loads(fake_file.read_text()) == []
