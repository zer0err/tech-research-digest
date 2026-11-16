import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from research_bot import schedule


def now():
    return datetime(2026, 10, 24, 2, 44, tzinfo=UTC)  # Beijing 10:44


def empty():
    return {"version": 1, "slots": {}}


def test_catchup_selects_only_the_daily_report_after_nine():
    assert schedule.due_slots(now(), empty(), []) == ["daily_report"]


def test_evening_still_selects_only_the_unfinished_daily_report():
    assert schedule.due_slots(now().replace(hour=15), empty(), []) == ["daily_report"]


def test_before_morning_does_not_publish_future_slots():
    assert schedule.due_slots(now().replace(hour=0), empty(), []) == []


def test_taipei_boundary_is_not_utc_hour():
    assert not schedule.is_due("daily_report", datetime(2026, 10, 26, 0, 59, 59, tzinfo=UTC))
    assert schedule.is_due("daily_report", datetime(2026, 10, 26, 1, 0, tzinfo=UTC))


def test_taipei_day_rollover_does_not_publish_before_nine():
    assert schedule.key("daily_report", datetime(2026, 10, 25, 16, tzinfo=UTC)) == "2026-10-26:daily_report"
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
    assert json.loads(Path("reports/decision-model_research.json").read_text())["reason"] == "retired_slot"


def test_valid_visible_article_prevents_repeat():
    entries = [{"topic": "daily_report", "date": "2026-10-24T09:00:00+08:00", "count": 2, "status": "published"}]
    assert schedule.due_slots(now(), empty(), entries) == []


def test_empty_or_yesterday_article_does_not_block_today():
    entries = [{"topic": "daily_report", "date": "2026-10-24", "count": 0, "status": "empty"},
               {"topic": "daily_report", "date": "2026-10-23T09:00:00+08:00", "count": 2, "status": "published"}]
    assert schedule.due_slots(now(), empty(), entries) == ["daily_report"]


def test_yesterday_backfill_does_not_complete_today_slot():
    entries = [{"topic": "daily_report", "date": "2026-10-26T09:00:00+08:00",
                "execution_date": "2026-10-25", "status": "published", "count": 2}]
    today = datetime(2026, 10, 26, 2, tzinfo=UTC)
    assert not schedule.completed("daily_report", today, empty(), entries)
    assert schedule.due_slots(today, empty(), entries) == ["daily_report"]


def test_transient_retry_is_bounded_and_cooled_down():
    ledger = empty()
    record = {"status": "source_failure", "attempts": 1, "updated_at": now().isoformat()}
    ledger["slots"][schedule.key("daily_report", now())] = record
    assert not schedule.eligible("daily_report", now() + timedelta(minutes=30), ledger, [])
    assert schedule.eligible("daily_report", now() + timedelta(minutes=61), ledger, [])
    record["attempts"] = 3
    assert not schedule.eligible("daily_report", now() + timedelta(hours=4), ledger, [])


def test_prepared_receipt_resumes_despite_visible_article():
    ledger = empty()
    ledger["slots"][schedule.key("daily_report", now())] = {"status": "prepared", "attempts": 3}
    entries = [{"topic": "daily_report", "date": "2026-10-24", "count": 2, "status": "published"}]
    assert schedule.eligible("daily_report", now(), ledger, entries)


def test_ledger_persists_publish_and_clears_pending(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    schedule.record("daily_report", now(), "prepared", {"url": "https://example.com/post"})
    assert "pending" in schedule.load()["slots"][schedule.key("daily_report", now())]
    schedule.record("daily_report", now(), "published")
    record = json.loads(Path("state/slots.json").read_text())["slots"][schedule.key("daily_report", now())]
    assert record["status"] == "published"
    assert "pending" not in record


def test_no_new_receipt_waits_for_rescan_and_does_not_block_next_day():
    ledger = empty()
    ledger["slots"][schedule.key("daily_report", now())] = {"status": "no_matching_in_window"}
    assert not schedule.eligible("daily_report", now(), ledger, [])
    assert schedule.eligible("daily_report", now() + timedelta(days=1), ledger, [])


def test_empty_day_can_be_rescanned_after_the_long_cooldown():
    ledger = empty()
    moment = now()
    ledger["slots"][schedule.key("daily_report", moment)] = {
        "status": "already_published", "attempts": 1, "updated_at": moment.isoformat(),
    }
    assert not schedule.eligible("daily_report", moment + timedelta(minutes=179), ledger, [])
    assert schedule.eligible("daily_report", moment + timedelta(minutes=181), ledger, [])
    ledger["slots"][schedule.key("daily_report", moment)]["attempts"] = 3
    assert not schedule.eligible("daily_report", moment + timedelta(hours=6), ledger, [])
