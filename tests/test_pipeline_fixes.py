"""Regression coverage for the pipeline fixes approved from the investigation."""
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import yaml

from research_bot import core, finalize
from research_bot.core import Item, canonical_url, contains_term, in_lookback, normalize_report, report_is_complete, unseen, update_state
from research_bot.finalize import remember_publication
from research_bot.sources import stable_release_tag


def long_summary(text: str = "A transformer neural network training method with public evidence.") -> str:
    return text if len(text) >= 40 else text + " " + ("evidence " * 8)


def test_schedule_file_is_the_only_clock_and_matches_utc_crons():
    project = Path(__file__).resolve().parents[1]
    editorial = yaml.safe_load((project / "config/editorial.yml").read_text())
    workflow = yaml.safe_load((project / ".github/workflows/editorial-day.yml").read_text())
    triggers = workflow.get("on", workflow.get(True))
    crons = [entry["cron"] for entry in triggers["schedule"]]

    def beijing_cron(value: str) -> str:
        hour, minute = (int(part) for part in value.split(":"))
        return f"{minute} {(hour - 8) % 24} * * *"

    assert crons == [beijing_cron(slot["time"]) for slot in editorial["slots"].values()]
    assert editorial["analysis_item_limit"] == 3


def test_rotating_topics_are_unique_within_each_weekday():
    editorial = yaml.safe_load((Path(__file__).resolve().parents[1] / "config/editorial.yml").read_text())
    slots = editorial["slots"]
    for day in "1234567":
        chosen = []
        for _name, slot in slots.items():
            if slot.get("special") == "daily_digest":
                continue
            chosen.append(slot.get("topic") or slot["topic_by_weekday"][day])
        assert len(chosen) == len(set(chosen))
        assert chosen.count("model_research") == 1


def test_same_title_with_different_ids_is_kept_and_arxiv_versions_collapse():
    now = datetime.now(UTC)
    state = {"version": 1, "topics": {}}
    first = Item("a", "Shared title", "https://example.com/a", now.isoformat(), "abstract", "src")
    second = Item("b", "Shared title", "https://example.com/b", now.isoformat(), "abstract", "src")
    update_state(state, "model_research", [first], now)
    assert unseen([second], state, "other") == [second]
    assert canonical_url("https://arxiv.org/abs/2611.13512v2") == "https://arxiv.org/abs/2611.13512"
    seen = {"version": 1, "topics": {}, "all_urls": ["https://arxiv.org/abs/2611.13512v1"]}
    revised = Item("new", "Paper", "https://arxiv.org/abs/2611.13512v2", now.isoformat(), "abstract", "src",
                   aliases=("arxiv:2611.13512", "url:https://arxiv.org/abs/2611.13512"))
    assert unseen([revised], seen, "model_research") == []


def test_canonical_url_keeps_identity_query_and_upgrades_http():
    assert canonical_url("http://Example.com/a?id=123&utm_source=x#part") == "https://example.com/a?id=123"
    assert contains_term("language models and robots", "model")
    assert contains_term("language models", "language model")
    assert not contains_term("documentation is available", "ai")


def test_day_dates_cover_the_calendar_day_and_months_must_fit_entirely():
    now = datetime(2026, 11, 11, 6, tzinfo=UTC)
    cutoff = now - timedelta(hours=72)
    boundary = datetime(2026, 11, 8, tzinfo=UTC)
    assert in_lookback(boundary, "day", cutoff, now)
    assert not in_lookback(boundary, "instant", cutoff, now)
    november = datetime(2026, 11, 1, tzinfo=UTC)
    assert not in_lookback(november, "month", cutoff, now)


def test_short_newest_release_does_not_consume_the_source_slot(monkeypatch):
    monkeypatch.setattr(core, "fetch_entries", lambda *args: [
        {"id": "new", "title": "New", "published": "2026-10-23T12:00:00Z", "summary": "tiny",
         "link": "https://example.com/new"},
        {"id": "old", "title": "Older notes", "published": "2026-10-22T12:00:00Z",
         "summary": long_summary(), "link": "https://example.com/old"},
    ])
    records = core.collect(
        {"lookback_hours": 72, "max_per_source": 1, "sources": [{"name": "Repo", "url": "https://example.com/rss"}]},
        datetime(2026, 10, 23, 18, tzinfo=UTC),
    )
    assert [item.title for item in records] == ["Older notes"]


def test_bibliographic_search_drops_clinical_multimodal_papers(monkeypatch):
    clinical = long_summary("Patients with pulmonary disease were diagnosed using a multimodal deep learning CT model.")
    vision = long_summary("A transformer model for speech recognition and vision.")
    monkeypatch.setattr(core, "fetch_entries", lambda *args: [
        {"id": "clinical", "title": "Clinical multimodal diagnosis", "published": "2026-10-23",
         "summary": clinical, "link": "https://example.com/clinical"},
        {"id": "vision", "title": "Audio visual speech", "published": "2026-10-23",
         "summary": vision, "link": "https://example.com/vision"},
    ])
    records = core.collect(
        {"lookback_hours": 72, "keywords": ["multimodal", "vision", "speech"],
         "sources": [{"name": "Crossref", "type": "crossref", "url": "https://api.crossref.org/works"}]},
        datetime(2026, 10, 23, 12, tzinfo=UTC),
    )
    assert [item.title for item in records] == ["Audio visual speech"]


def test_partial_source_failure_is_not_reported_as_no_news(tmp_path, monkeypatch):
    import research_bot.main as runner

    monkeypatch.chdir(tmp_path)
    found = core.Collected([], {"failed": 1, "short_summary": 0, "sources": [{"name": "arXiv", "ok": False, "error": "ReadTimeout"}]})
    monkeypatch.setattr(runner, "collect", lambda *args: found)
    config = {"title": "T", "analysis_focus": "F", "max_items": 3}
    assert not runner.prepare_topic("model_research", config, Path("state.json"), datetime(2026, 10, 23, tzinfo=UTC))
    decision = json.loads(Path("reports/decision-model_research.json").read_text())
    assert decision["reason"] == "source_failure"
    assert decision["sources_failed"] == 1


def test_analysis_item_limit_overrides_a_larger_max_items(tmp_path, monkeypatch):
    import research_bot.main as runner

    monkeypatch.chdir(tmp_path)
    now = datetime(2026, 10, 23, tzinfo=UTC)
    items = [
        Item(str(i), f"Paper {i}", f"https://example.com/{i}", now.isoformat(), long_summary(), "src")
        for i in range(4)
    ]
    monkeypatch.setattr(runner, "collect", lambda *args: items)
    seen = []

    def analyse(_title, _focus, selected, _content_type):
        seen.append(len(selected))
        cites = range(1, len(selected) + 1)
        bullets = "\n".join(f"- 来源支持这一信号。[{i}]" for i in cites)
        detail = "\n".join(f"来源明确提供方法，适用性需实验验证。[{i}]" for i in cites)
        refs = "\n".join(f"[{i}] https://example.com/{i}" for i in cites)
        pad = "来源明确提供方法，适用性需实验验证。\n" * 12
        return f"## 本期结论\n{bullets}\n## 逐项分析\n{detail}\n{pad}\n## 工程行动建议\n验证测试条件。\n## 参考资料\n{refs}"

    monkeypatch.setattr(runner, "groq_analyse", analyse)
    config = {"title": "T", "analysis_focus": "F", "max_items": 6}
    assert runner.prepare_topic("model_research", config, Path("state.json"), now)
    config["analysis_item_limit"] = 4
    assert runner.prepare_topic("model_research", config, Path("state.json"), now)
    assert seen == [3, 4]


def test_validation_retry_asks_groq_again_before_mimo(tmp_path, monkeypatch):
    import research_bot.main as runner

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MIMO_FALLBACK_ENABLED", "true")
    monkeypatch.setenv("MIMO_API_KEY", "not-used")
    now = datetime(2026, 10, 23, tzinfo=UTC)
    item = Item("a", "Paper", "https://example.com/paper", now.isoformat(), long_summary(), "src")
    monkeypatch.setattr(runner, "collect", lambda *args: [item])
    calls = []

    def groq(*args):
        calls.append("groq")
        if len(calls) == 1:
            return "too short"
        return ("## 本期结论\n- 来源支持这一信号。[1]\n## 逐项分析\n" + "来源明确提供方法，适用性需实验验证。[1]" * 20
                + "\n## 工程行动建议\n验证测试条件。[1]\n## 参考资料\n[1] https://example.com/paper")

    monkeypatch.setattr(runner, "groq_analyse", groq)
    monkeypatch.setattr(runner, "mimo_analyse", lambda *args: calls.append("mimo"))
    assert runner.prepare_topic("model_research", {"title": "T", "analysis_focus": "F", "max_items": 3},
                                Path("state.json"), now)
    assert calls == ["groq", "groq"]


def test_numbers_anywhere_in_the_analysis_must_be_grounded_and_commands_can_be_removed():
    item = Item("a", "Paper", "https://example.com/a", "2026-01-01T00:00:00+00:00", long_summary("no figures here"), "src")
    report = ("## 本期要点\n- 更新。[1]\n## 逐项速览\n性能提升 50%。[1]\n## 值得采取的行动\n验证\n## 参考资料\n[1] URL")
    assert not report_is_complete(report, [item], "brief")
    invented = ("## 本期要点\n- 更新。[1]\n## 逐项速览\n来源没有给出安装步骤。[1]\n## 值得采取的行动\n"
                "```bash\npip install invented-package\n```\n## 参考资料\n[1] https://example.com/a")
    cleaned = normalize_report(invented, "brief", [item])
    assert "invented-package" not in cleaned
    assert "已省略" in cleaned
    assert report_is_complete(cleaned, [item], "brief")


def test_groq_caps_retry_after_and_retries_transport_errors(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test")
    monkeypatch.setattr(core.random, "random", lambda: 0)
    sleeps = []
    monkeypatch.setattr(core.time, "sleep", lambda seconds: sleeps.append(seconds))
    calls = {"n": 0}

    def post(self, url, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.ConnectError("down")
        if calls["n"] == 2:
            return httpx.Response(429, headers={"retry-after": "9999"}, json={},
                                  request=httpx.Request("POST", url))
        return httpx.Response(200, json={"usage": {}, "choices": [{"finish_reason": "stop", "message": {"content": "ok"}}]},
                              request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.Client, "post", post)
    assert core.groq_analyse("title", "focus", [], "brief") == "ok"
    assert sleeps[0] <= 45
    assert sleeps[1] <= 45


def test_radar_prompt_does_not_ask_the_model_to_certify_a_free_tier(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test")
    captured = {}

    def post(self, url, **kwargs):
        captured.update(kwargs["json"])
        return httpx.Response(200, json={"usage": {}, "choices": [{"finish_reason": "stop", "message": {"content": "ok"}}]},
                              request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.Client, "post", post)
    core.groq_analyse("雷达", "focus", [], "radar")
    instructions = captured["messages"][1]["content"]
    assert "永久免费层" not in instructions
    assert "未核验" in instructions


def test_release_tags_allow_post_and_four_parts_but_not_prereleases():
    assert stable_release_tag("v1.2.3.post1")
    assert stable_release_tag("v1.2.3.4")
    assert not stable_release_tag("v2.5.0-rc1")
    assert not stable_release_tag("v1.2.3-alpha.1")


def test_replay_does_not_pollute_production_seen_ids(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("work").mkdir()
    pending = {
        "topic": "model_research", "slot": "paper_brief", "title": "Replay",
        "url": "https://example.com/replay", "created_at": "2026-11-08T11:00:00+00:00",
        "replay_date": "2026-11-08", "notify": True, "published_count": 1,
        "items": [{
            "uid": "replay-item", "title": "Paper", "url": "https://example.com/paper",
            "published": "2026-11-08T00:00:00+00:00", "summary": "A long abstract that must not enter the dedup index.",
            "source": "arXiv",
        }],
    }
    Path("work/pending.json").write_text(json.dumps(pending))
    monkeypatch.setattr(finalize, "send_telegram", lambda text: (_ for _ in ()).throw(AssertionError(text)))
    monkeypatch.setattr("sys.argv", ["finalize"])

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 11, 9, 11, tzinfo=UTC).astimezone(tz)

    monkeypatch.setattr(finalize, "datetime", Clock)
    assert finalize.main() == 0
    state = json.loads(Path("state/seen.json").read_text())
    assert "replay-item" not in state.get("all_ids", [])
    stored = state["publications"]["https://example.com/replay"]["items"][0]
    assert "summary" not in stored
    assert stored["uid"] == "replay-item"


def test_publication_history_is_slim_and_bounded():
    state = {"version": 1, "topics": {}, "publications": {
        f"https://example.com/{i:04d}": {"created_at": f"{i:04d}", "items": [{"summary": "old abstract"}]}
        for i in range(400)
    }}
    remember_publication(state, {
        "url": "https://example.com/new", "topic": "model_research", "created_at": "9999",
        "items": [{"uid": "n", "title": "New", "url": "https://example.com/new", "published": "2026-11-11",
                   "summary": "fresh abstract", "source": "arXiv", "doi": "", "kind": "research", "date_precision": "day"}],
    })
    assert len(state["publications"]) == 400
    assert "https://example.com/0000" not in state["publications"]
    assert "summary" not in state["publications"]["https://example.com/new"]["items"][0]


def test_maintenance_flag_is_recorded_for_exhausted_slots(tmp_path, monkeypatch):
    from research_bot.public_status import notify_maintenance
    from research_bot.schedule import BEIJING

    monkeypatch.chdir(tmp_path)
    Path("state").mkdir()
    today = datetime.now(BEIJING).date().isoformat()
    Path("state/slots.json").write_text(json.dumps({"version": 1, "slots": {
        f"{today}:morning_radar": {
            "status": "analysis_api_failure", "attempts": 3,
            "updated_at": datetime.now(UTC).isoformat(),
        },
    }}))
    notify_maintenance()
    saved = json.loads(Path("state/slots.json").read_text())
    assert saved["slots"][f"{today}:morning_radar"]["maintenance_notified"] is True


def test_editorial_workflow_gates_deploy_preview_and_maintenance_alerts():
    project = Path(__file__).resolve().parents[1]
    editorial = (project / ".github/workflows/_editorial.yml").read_text()
    preview = (project / ".github/workflows/_research.yml").read_text()
    assert "git_push_with_retry" in editorial
    assert "steps.docs.outputs.changed == 'true'" in editorial
    assert 'NOTIFY_MAINTENANCE: "true"' in editorial
    assert "--dry-run" in editorial
    assert 'inputs.analyze' in editorial
    assert "--dry-run" in preview
    assert "deploy-pages" not in preview
    assert "cvf" not in (project / "config/sources.yml").read_text()


def test_source_topic_files_a_rotating_slot_into_its_domain(tmp_path):
    from research_bot.domain_hub import render_domain_hub

    posts = tmp_path / "posts"
    posts.mkdir()
    (posts / "20261111-paper_brief.html").write_text("article")
    (tmp_path / "posts.json").write_text(json.dumps([{
        "title": "高效模型", "url": "posts/20261111-paper_brief.html", "status": "published",
        "count": 1, "topic": "paper_brief", "source_topic": "efficient_ai", "date": "2026-11-11",
    }]))
    page = render_domain_hub(tmp_path).read_text()
    assert 'href="../posts/20261111-paper_brief.html"' in page
