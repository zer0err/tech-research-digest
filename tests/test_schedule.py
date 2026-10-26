import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from research_bot import schedule


def now():
    return datetime(2026, 10, 24, 2, 44, tzinfo=UTC)  # Beijing 10:44


def empty():
    return {"version": 1, "slots": {}}


def test_catchup_selects_only_overdue_slots():
    assert schedule.due_slots(now(), empty(), []) == ["morning_radar", "model_research"]


def test_evening_catches_all_unfinished_slots():
    assert schedule.due_slots(now().replace(hour=15), empty(), []) == list(schedule.TIMES)


def test_before_morning_does_not_publish_future_slots():
    assert schedule.due_slots(now().replace(hour=0), empty(), []) == []


def test_east_eight_boundary_is_not_utc_hour():
    assert not schedule.is_due("morning_radar", datetime(2026, 10, 26, 1, 6, 59, tzinfo=UTC))
    assert schedule.is_due("morning_radar", datetime(2026, 10, 26, 1, 7, tzinfo=UTC))
    assert not schedule.is_due("model_research", datetime(2026, 10, 26, 1, 24, tzinfo=UTC))


def test_beijing_day_rollover_has_no_next_day_early_slots():
    assert schedule.key("morning_radar", datetime(2026, 10, 25, 16, tzinfo=UTC)) == "2026-10-26:morning_radar"
    assert schedule.due_slots(datetime(2026, 10, 25, 16, tzinfo=UTC), empty(), []) == []


def test_production_entrypoint_refuses_future_slot(tmp_path, monkeypatch):
    from research_bot import editorial
    monkeypatch.chdir(tmp_path)
    Path("editorial.yml").write_text("slots:\n  model_research:\n    topic: model_research\n")
    Path("sources.yml").write_text("topics: {}\n")
    Path("work").mkdir()
    Path("work/pending.json").write_text('{"stale":true}')
    monkeypatch.setenv("PUBLICATION_MODE", "production")
    monkeypatch.setattr(schedule, "is_due", lambda *args: False)
    monkeypatch.setattr("sys.argv", ["editorial", "--slot", "model_research", "--editorial-config", "editorial.yml",
                                     "--sources-config", "sources.yml"])
    assert editorial.main() == 0
    assert not Path("work/pending.json").exists()
    assert not Path("state/slots.json").exists()
    assert json.loads(Path("reports/decision-model_research.json").read_text())["reason"] == "not_due_yet"


def test_valid_visible_article_prevents_repeat():
    entries = [{"topic": "morning_radar", "date": "2026-10-24T09:30:00+08:00", "count": 2, "status": "published"}]
    assert schedule.due_slots(now(), empty(), entries) == ["model_research"]


def test_empty_or_yesterday_article_does_not_block_today():
    entries = [{"topic": "morning_radar", "date": "2026-10-24", "count": 0, "status": "empty"},
               {"topic": "model_research", "date": "2026-10-23", "count": 2, "status": "published"}]
    assert len(schedule.due_slots(now(), empty(), entries)) == 2


def test_transient_retry_is_bounded_and_cooled_down():
    ledger = empty()
    record = {"status": "source_failure", "attempts": 1, "updated_at": now().isoformat()}
    ledger["slots"][schedule.key("morning_radar", now())] = record
    assert not schedule.eligible("morning_radar", now() + timedelta(minutes=30), ledger, [])
    assert schedule.eligible("morning_radar", now() + timedelta(minutes=61), ledger, [])
    record["attempts"] = 3
    assert not schedule.eligible("morning_radar", now() + timedelta(hours=4), ledger, [])


def test_prepared_receipt_resumes_despite_visible_article():
    ledger = empty()
    ledger["slots"][schedule.key("morning_radar", now())] = {"status": "prepared", "attempts": 3}
    entries = [{"topic": "morning_radar", "date": "2026-10-24", "count": 2, "status": "published"}]
    assert schedule.eligible("morning_radar", now(), ledger, entries)


def test_ledger_persists_publish_and_clears_pending(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    schedule.record("morning_radar", now(), "prepared", {"url": "https://example.com/post"})
    assert "pending" in schedule.load()["slots"][schedule.key("morning_radar", now())]
    schedule.record("morning_radar", now(), "published")
    record = json.loads(Path("state/slots.json").read_text())["slots"][schedule.key("morning_radar", now())]
    assert record["status"] == "published"
    assert "pending" not in record


def test_no_new_receipt_is_terminal_but_not_next_day():
    ledger = empty()
    ledger["slots"][schedule.key("morning_radar", now())] = {"status": "no_matching_in_window"}
    assert not schedule.eligible("morning_radar", now(), ledger, [])
    assert schedule.eligible("morning_radar", now() + timedelta(days=1), ledger, [])
