from datetime import timedelta
from pathlib import Path

import pytest

from research_bot import finalize, rotation, rotation_collect, schedule
from research_bot.domain_report import MODULES


START = schedule.ROTATION_START


def at(hour, minute=0, day=START):
    return rotation.stamp(day, hour).replace(minute=minute)


def draft(domain, cutoff, suffix=None, doi=""):
    key = suffix or domain
    return dict(ok=True, reason="prepared", title=MODULES[domain], topic=domain,
                report=f"## 核心变化\n\n证据边界：[原始资料](https://example.com/{key})",
                items=[dict(uid=key, url=f"https://example.com/{key}", title=f"Evidence {key}",
                            summary="Fixture", published=cutoff.isoformat(), source="example.com",
                            doi=doi)],
                analysis={"provider": "Fixture", "model": "Offline"})


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(rotation_collect, "generate_other", lambda *_: {"ok": False})
    return tmp_path


def run(now, clock=None):
    rotation.tick(now, clock=clock or (lambda: now))


def test_plan_continuous_domain_rotation():
    expected = list(MODULES) * 3
    whole_cycle = [d for k in range(10) for _, d in rotation.slots(START + timedelta(days=k))]
    assert whole_cycle == expected
    assert schedule.daily_planned_time(START - timedelta(days=1)) == "09:00"
    assert schedule.daily_planned_time(START) == "18:00"


def test_isolated_batches_failure_partial_edition_and_immutable_assembly(workspace, monkeypatch):
    calls = []

    def generator(domain, cutoff, blocked):
        calls.append((domain, cutoff, blocked))
        if domain == "training":
            return {"ok": False, "reason": "analysis_rejected"}
        return draft(domain, cutoff)

    monkeypatch.setattr(rotation_collect, "generate", generator)
    assert rotation.plan(at(8, 59)) == []
    run(at(9, 25))
    assert calls[0][:2] == ("models", at(9))
    run(at(13, 4))
    run(at(17, 8))
    assert [domain for domain, _, _ in calls] == ["models", "training", "training", "inference"]
    assert calls[-1][1] == at(17)
    assert "url:https://example.com/models" in calls[-1][2]
    assert not Path("docs").exists()
    assert not rotation.PENDING.exists()
    run(at(18, 2))
    article = Path("docs") / rotation.canonical_name(START.isoformat())
    assert "本期未收录：训练方法与数据" in article.read_text()
    assert "18:02" in article.read_text()
    assert "18:00" in article.read_text()
    assert "基础模型与能力" in article.read_text() and "推理系统与计算效率" in article.read_text()
    assert "补充" not in article.read_text()
    assert rotation.DEPLOY_REQUIRED.exists()
    assert len(rotation.read(rotation.INDEX, [])) == 1
    assert rotation.plan(at(18, 10)) == [f"resume:{START}"]
    run(at(18, 10))
    assert article.exists()
    assert len(calls) == 4 and len(rotation.read(rotation.INDEX, [])) == 1


def test_failed_or_missing_domains_close_with_no_release_even_if_other_exists(workspace, monkeypatch):
    def forbidden(*_):
        pytest.fail("should not generate after seal or call Other on empty core")
    monkeypatch.setattr(rotation_collect, "generate", forbidden)
    monkeypatch.setattr(rotation_collect, "generate_other", forbidden)
    run(at(18))
    assert rotation.state_for(START)["status"] == "sealed_empty"
    assert rotation.plan(at(20)) == []
    run(at(20))
    assert not rotation.PENDING.exists() and not rotation.INDEX.exists()
    assert schedule.load()["slots"][f"{START}:daily_report"]["status"] == "empty_digest"


def test_late_completion_never_enters_edition(workspace, monkeypatch):
    monkeypatch.setattr(rotation_collect, "generate", lambda domain, cutoff, _: draft(domain, cutoff))
    run(at(9))
    now = at(17, 59)
    moments = iter([now, now, at(18), at(18), at(18)])
    monkeypatch.setattr(rotation_collect, "generate", lambda domain, cutoff, _: draft(domain, cutoff))
    run(now, clock=lambda: next(moments, at(18)))
    state = rotation.state_for(START)
    actual = rotation.read(rotation.INDEX, [])[0]
    assert state["slots"]["13"]["status"] == "missed_deadline"
    assert [s["topic"] for s in actual["sections"]] == ["models"]


def test_doi_collision_rejected_without_stealing_from_later_domain(workspace, monkeypatch):
    def generator(domain, cutoff, blocked):
        doi = "10.1010/overlap" if domain != "inference" else "10.1010/unique"
        return draft(domain, cutoff, doi=doi)

    monkeypatch.setattr(rotation_collect, "generate", generator)
    run(at(9))
    run(at(13))
    run(at(17))
    assert rotation.state_for(START)["slots"]["13"]["status"] == "invalid_draft"
    run(at(18))
    entry = rotation.read(rotation.INDEX, [])[0]
    assert [s["topic"] for s in entry["sections"]] == ["models", "inference"]


def test_prepared_deploy_claim_finalize_state_survives_restart(workspace, monkeypatch):
    monkeypatch.setattr(rotation_collect, "generate", lambda domain, cutoff, _: draft(domain, cutoff))
    run(at(9))
    run(at(18, 1))
    with pytest.raises(ValueError):
        rotation.transition("claim", at(18, 2))
    rotation.transition("deployed", at(18, 2))
    rotation.transition("claim", at(18, 3))
    assert rotation.read(rotation.PENDING, {})["notify"]
    assert rotation.state_for(START)["notification_claim"] == at(18, 3).isoformat()
    # Simulate a fresh job following an uncertain external send. It must
    # finish state bookkeeping without attempting another notification.
    run(at(18, 10))
    assert not rotation.DEPLOY_REQUIRED.exists()
    assert not rotation.read(rotation.PENDING, {})["notify"]
    rotation.transition("claim", at(18, 11))
    monkeypatch.setattr("sys.argv", ["finalize"])
    monkeypatch.setattr(finalize, "send_telegram", lambda *_: pytest.fail("duplicate notification"))
    finalize.main()
    rotation.transition("finalized", at(18, 12))
    assert rotation.plan(at(19)) == []
    assert rotation.state_for(START)["status"] == "finalized"
    assert rotation.read(Path("state/seen.json"), {})["publications"]


def test_resume_after_midnight_never_claims_yesterdays_notice(workspace, monkeypatch):
    monkeypatch.setattr(rotation_collect, "generate", lambda domain, cutoff, _: draft(domain, cutoff))
    run(at(9))
    run(at(18, 1))
    next_day = START + timedelta(days=1)
    run(at(0, day=next_day))
    rotation.transition("deployed", at(0, 2, day=next_day))
    rotation.transition("claim", at(0, 3, day=next_day))
    assert not rotation.read(rotation.PENDING, {})["notify"]
    assert rotation.state_for(START)["status"] == "deployed"
