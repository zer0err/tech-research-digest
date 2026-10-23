import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

import research_bot.main as runner
from research_bot.core import Item, SourceUnavailable, fallback_report
from research_bot.editorial import prepare_daily_digest


@pytest.fixture
def setup_run(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("work").mkdir()
    Path("work/pending.json").write_text('{"stale":true}')
    return {"title": "Test", "analysis_focus": "Test", "max_items": 6}, datetime(2026, 10, 23, tzinfo=UTC)


def test_no_items_even_allow_empty_does_not_publish(setup_run, monkeypatch):
    config, now = setup_run
    monkeypatch.setattr(runner, "collect", lambda *args: [])
    assert not runner.prepare_topic("test", config, Path("state.json"), now, allow_empty=True)
    assert not Path("work/pending.json").exists()
    assert not Path("docs").exists()


def test_source_failure_does_not_publish(setup_run, monkeypatch):
    config, now = setup_run
    def fail(*args):
        raise SourceUnavailable()
    monkeypatch.setattr(runner, "collect", fail)
    assert not runner.prepare_topic("test", config, Path("state.json"), now)
    assert not Path("work/pending.json").exists()


def test_rejected_analysis_never_becomes_public_fallback(setup_run, monkeypatch):
    config, now = setup_run
    item = Item("a", "Paper", "https://example.com/paper", now.isoformat(), "real evidence " * 20, "source")
    monkeypatch.setattr(runner, "collect", lambda *args: [item])
    calls = []
    def analyse(*args):
        calls.append(1)
        return fallback_report([item], "research")
    monkeypatch.setattr(runner, "groq_analyse", analyse)
    assert not runner.prepare_topic("test", config, Path("state.json"), now)
    assert len(calls) == 2
    assert not Path("docs").exists()
    assert not Path("work/pending.json").exists()
    assert len(list(Path("reports").glob("rejected-*.md"))) == 2


def test_empty_or_failed_posts_do_not_make_digest(setup_run):
    _, now = setup_run
    Path("docs").mkdir()
    Path("docs/posts.json").write_text(json.dumps([
        {"date": now.isoformat(), "topic": "test", "count": 0, "status": "empty"},
        {"date": now.isoformat(), "topic": "test", "count": 3, "status": "fallback"},
    ]))
    assert not prepare_daily_digest(now)
    assert not Path("work/pending.json").exists()


def test_valid_analysis_publishes(setup_run, monkeypatch):
    config, now = setup_run
    item = Item("a", "Paper", "https://example.com/paper", now.isoformat(), "real evidence " * 20, "source")
    monkeypatch.setattr(runner, "collect", lambda *args: [item])
    report = ("## 本期结论\n- 根据来源提供的方法验证。[1]\n## 逐项分析\n" + "来源明确提供方法，实际适用性仍需实验验证。[1]" * 20
              + "\n## 工程行动建议\n验证数据与测试条件。[1]\n## 参考资料\n[1] https://example.com/paper")
    monkeypatch.setattr(runner, "groq_analyse", lambda *args: report)
    assert runner.prepare_topic("test", config, Path("state.json"), now)
    assert Path("work/pending.json").exists()
    assert len(list(Path("docs/posts").glob("*.html"))) == 1


def test_test_mode_ignores_production_history_and_never_publishes(setup_run, monkeypatch):
    from research_bot.core import update_state
    config, now = setup_run
    item = Item("a", "Paper", "https://example.com/paper", now.isoformat(), "real evidence " * 20, "source")
    state = {"version": 1, "topics": {}}
    update_state(state, "test", [item], now)
    Path("state.json").write_text(json.dumps(state))
    before = Path("state.json").read_text()
    monkeypatch.setenv("PUBLICATION_MODE", "test")
    monkeypatch.setattr(runner, "collect", lambda *args: [item])
    report = ("## 本期结论\n- 来源支持这一信号。[1]\n## 逐项分析\n" + "来源明确提供方法，适用性需实验验证。[1]" * 25
              + "\n## 工程行动建议\n验证测试条件。[1]\n## 参考资料\n[1] https://example.com/paper")
    monkeypatch.setattr(runner, "groq_analyse", lambda *args: report)
    assert not runner.prepare_topic("test", config, Path("state.json"), now)
    assert Path("reports/test-test.md").exists()
    assert not Path("work/pending.json").exists()
    assert not Path("docs").exists()
    assert Path("state.json").read_text() == before


def test_test_digest_never_publishes(setup_run, monkeypatch):
    _, now = setup_run
    monkeypatch.setenv("PUBLICATION_MODE", "test")
    assert not prepare_daily_digest(now)
    assert not Path("work/pending.json").exists()
