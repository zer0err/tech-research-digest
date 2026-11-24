import json
from datetime import UTC, date, datetime
from pathlib import Path

from research_bot import schedule


def now():
    return datetime(2026, 10, 24, 2, 44, tzinfo=UTC)  # Beijing 10:44


def test_taipei_boundary_and_historical_time():
    assert schedule.key("daily_report", datetime(2026, 11, 23, 16, tzinfo=UTC)) == "2026-11-24:daily_report"
    assert schedule.daily_planned_time(date(2026, 11, 23)) == "09:00"
    assert schedule.daily_planned_time(date(2026, 11, 24)) == "18:00"
    assert not schedule.is_due("daily_report", datetime(2026, 10, 26, 0, 59, 59, tzinfo=UTC))
    assert schedule.is_due("daily_report", datetime(2026, 10, 26, 1, 0, tzinfo=UTC))


def test_ledger_persists_publish_and_clears_pending(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    schedule.record("daily_report", now(), "prepared", {"url": "https://example.com/post"})
    assert "pending" in schedule.load()["slots"][schedule.key("daily_report", now())]
    schedule.record("daily_report", now(), "published")
    record = json.loads(Path("state/slots.json").read_text())["slots"][schedule.key("daily_report", now())]
    assert record["status"] == "published"
    assert "pending" not in record
