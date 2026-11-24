from datetime import timedelta

from research_bot import rotation, rotation_collect, schedule


def test_rejected_retry_writes_only_bounded_canonical_codes(tmp_path, monkeypatch, caplog):
    monkeypatch.chdir(tmp_path)
    day = schedule.ROTATION_START
    cutoff = rotation.stamp(day, 9)
    old = {"domain": "models", "cutoff": cutoff.isoformat(), "finished_at": cutoff.isoformat(),
           "status": "analysis_rejected", "attempts": 1}
    rotation.save({"day": str(day), "status": "drafting", "slots": {"09": old}})
    now = cutoff + timedelta(minutes=30)
    monkeypatch.setattr(rotation_collect, "generate", lambda *_: {
        "ok": False, "reason": "analysis_rejected", "report": "private-raw-report",
        "issues": ["missing_sections", {"text": "private-raw-issue"}, True,
                   "private-raw-error", "insufficient_analysis", "missing_sections", *([None] * 40),
                   "unsupported_commands"],
    })
    with caplog.at_level("INFO"):
        rotation.tick(now, clock=lambda: now)
    row = rotation.state_for(day)["slots"]["09"]
    assert row == {**old, "finished_at": now.isoformat(), "attempts": 2,
                   "issue_codes_by_attempt": {"2": ["insufficient_analysis", "missing_sections"]}}
    assert "insufficient_analysis, missing_sections" in caplog.text
    assert "private-raw" not in caplog.text
    assert "private-raw" not in (rotation.STATE / f"{day}.json").read_text()
    assert not rotation.PENDING.exists()
    assert rotation.plan(now + timedelta(minutes=30)) == []


def test_retries_old_receipt_without_issue_list_and_ignores_other_failure_codes(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    day = schedule.ROTATION_START
    cutoff = rotation.stamp(day, 9)
    monkeypatch.setattr(rotation_collect, "generate", lambda *_: {
        "ok": False, "reason": "source_failure", "issues": ["missing_sections"],
    })
    rotation.tick(cutoff, clock=lambda: cutoff)
    row = rotation.state_for(day)["slots"]["09"]
    assert row["status"] == "source_failure"
    assert "issue_codes_by_attempt" not in row
    assert rotation.rejection_codes({"missing_sections": True}) == []
    assert rotation.rejection_codes("missing_sections") == []



def test_safe_history_survives_success_and_resanitizes_previous_receipt(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    day = schedule.ROTATION_START
    cutoff = rotation.stamp(day, 9)
    monkeypatch.setattr(rotation_collect, "generate", lambda *_: {
        "ok": False, "reason": "analysis_rejected", "issues": ["missing_source_numbers"],
    })
    rotation.tick(cutoff, clock=lambda: cutoff)
    state = rotation.state_for(day)
    row = state["slots"]["09"]
    assert row["issue_codes_by_attempt"] == {"1": ["missing_source_numbers"]}
    row["issue_codes_by_attempt"]["1"].append("private-raw-old")
    row["issue_codes_by_attempt"]["4"] = ["missing_sections"]
    rotation.save(state)

    def prepared(domain, cutoff, blocked):
        return {"ok": True, "topic": domain, "report": "Validated test draft", "items": [
            {"url": "https://example.com/evidence", "title": "Evidence", "summary": "fixture", "published": cutoff.isoformat()}
        ]}

    monkeypatch.setattr(rotation_collect, "generate", prepared)
    now = cutoff + timedelta(minutes=30)
    rotation.tick(now, clock=lambda: now)
    row = rotation.state_for(day)["slots"]["09"]
    assert row["status"] == "prepared"
    assert row["issue_codes_by_attempt"] == {"1": ["missing_source_numbers"]}
    assert "private-raw-old" not in (rotation.STATE / f"{day}.json").read_text()


def test_different_rejections_keep_each_attempts_codes():
    old = {"status": "analysis_rejected", "issue_codes": ["missing_sections", "secret"]}
    assert rotation.rejection_history(old, 2, ["unsupported_commands"]) == {
        "1": ["missing_sections"], "2": ["unsupported_commands"],
    }
    assert rotation.rejection_history({}, 1, []) == {}
