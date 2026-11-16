import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from research_bot.core import Item, in_lookback
from research_bot.daily import (
    COLLECTION_GRACE,
    ZONE,
    edition_cutoff,
    edition_day,
    edition_stamp,
    migrate,
    prepare_daily_report,
)


def long_page(title: str, paragraph: str, link: str) -> str:
    return (
        "<!doctype html><html><head><title>x</title></head><body><article>"
        f"<h1>{title}</h1><div class=\"article-body\"><h2>{title}</h2><p>{paragraph} "
        f"<a href=\"{link}\">{link}</a></p></div></article></body></html>"
    )


def entry(day: str, topic: str, url: str, **extra):
    return {
        "title": extra.pop("title", f"{topic}（{day}）"),
        "date": f"{day}T12:00:00+08:00",
        "count": 1,
        "url": url,
        "topic": topic,
        "status": "published",
        "summary": "摘要",
        "provenance": {"analysis": {"provider": "Groq", "model": "test"}, "sources": extra.pop("sources", [])},
        **extra,
    }


def test_morning_cutoff_excludes_later_instants_and_uses_taipei():
    late = datetime(2026, 11, 16, 7, tzinfo=UTC)  # 15:00 in Taipei
    cutoff = edition_cutoff(late)
    assert cutoff == datetime(2026, 11, 16, 9, tzinfo=ZONE)
    assert cutoff.utcoffset() == timedelta(hours=8)
    assert edition_cutoff(datetime(2026, 11, 16, 0, 59, tzinfo=UTC)) is None
    assert edition_cutoff(datetime(2026, 11, 16, 1, tzinfo=UTC)) == cutoff.replace(minute=0)
    collect_at = cutoff - COLLECTION_GRACE
    lookback = collect_at - timedelta(hours=72)
    assert in_lookback(datetime(2026, 11, 16, 8, 59, tzinfo=ZONE), "instant", lookback, collect_at)
    assert not in_lookback(datetime(2026, 11, 16, 9, 1, tzinfo=ZONE), "instant", lookback, collect_at)
    assert in_lookback(datetime(2026, 11, 16, tzinfo=ZONE), "day", lookback, collect_at)
    assert not in_lookback(datetime(2026, 11, 17, tzinfo=ZONE), "day", lookback, collect_at)
    shanghai = datetime(2026, 11, 16, 9, tzinfo=ZoneInfo("Asia/Shanghai"))
    assert shanghai.utcoffset() == cutoff.utcoffset()
    assert shanghai.hour == cutoff.hour


def test_migration_merges_one_day_and_keeps_distinct_links(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sent = []
    monkeypatch.setattr("research_bot.core.send_telegram", lambda text: sent.append(text))
    monkeypatch.setattr("research_bot.finalize.send_telegram", lambda text: sent.append(text))
    posts = Path("docs/posts")
    posts.mkdir(parents=True)
    shared = "https://example.com/shared-paper"
    other = "https://example.com/other-paper"
    external = "https://example.com/only-in-digest"
    pages = {
        "posts/20261101-model_research.html": long_page(
            "模型研究", "这是模型栏目的独立分析，讨论训练目标与评测限制，不能和硬件稿混成同一段。", shared),
        "posts/20261101-ai_hardware.html": long_page(
            "硬件研究", "这是硬件栏目的另一段分析，保留不同的实验条件与限制说明。", other),
        "posts/20261101-open_source.html": long_page(
            "同题不同链接", "开源稿标题可以和别的稿相同，但这条链接不同，所以正文要留下。", "https://example.com/third"),
        "posts/20261101-daily_digest.html": (
            "<html><head></head><body><article><div class=\"article-body\"><h2>今日概览</h2>"
            "<p>今天共发布 <strong>2</strong> 个内容更新。</p><h2>今日内容</h2><ul>"
            "<li><a href=\"https://vorasio.com/posts/20261101-model_research.html\">模型</a></li>"
            f"<li><a href=\"{external}\">索引里的站外链接</a></li></ul></div></article></body></html>"
        ),
    }
    # Same title as the hardware page, same link: duplicate prose must not be copied twice.
    pages["posts/20261101-core_research.html"] = pages["posts/20261101-ai_hardware.html"]
    for url, text in pages.items():
        Path("docs", url).write_text(text)
    sources = [
        {"title": "Shared", "url": shared, "doi": "", "publisher": "Example", "host": "example.com",
         "family": "博客/公开网页", "published": "2026-11-01", "date_precision": "day", "kind": "research"},
    ]
    entries = [
        entry("2026-11-01", "model_research", "posts/20261101-model_research.html", sources=sources),
        entry("2026-11-01", "ai_hardware", "posts/20261101-ai_hardware.html", source_topic="ai_hardware", sources=[
            {"title": "Shared", "url": shared, "doi": ""},
            {"title": "Other", "url": other, "doi": ""},
        ]),
        entry("2026-11-01", "open_source", "posts/20261101-open_source.html", title="硬件研究", sources=[
            {"title": "Third", "url": "https://example.com/third", "doi": ""},
        ]),
        entry("2026-11-01", "core_research", "posts/20261101-core_research.html", sources=[
            {"title": "Other", "url": other, "doi": ""},
        ]),
        entry("2026-11-01", "daily_digest", "posts/20261101-daily_digest.html", sources=[]),
        entry("2026-10-25", "paper_brief", "posts/20261025-paper_brief.html",
              date="2026-10-26T02:00:00+08:00", execution_date="2026-10-25",
              sources=[{"title": "Replay", "url": "https://example.com/replay", "doi": ""}]),
    ]
    Path("docs/posts/20261025-paper_brief.html").write_text(
        long_page("回放稿", "这是补发到 10 月 25 日的正文，不应并进 10 月 26 日。", "https://example.com/replay"))
    Path("docs/posts.json").write_text(json.dumps(entries))
    Path("state").mkdir()
    Path("state/seen.json").write_text(json.dumps({
        "version": 1, "topics": {},
        "daily_notifications": {"2026-11-01": {"sent_at": "2026-11-01T11:00:00+00:00", "url": "https://vorasio.com/old"}},
    }))
    mapping = migrate()
    assert sent == []
    assert mapping["counts"]["reports_after"] == 2
    assert mapping["counts"]["fragments_before"] == 6
    listed = json.loads(Path("docs/posts.json").read_text())
    assert [item["url"] for item in listed] == ["posts/20261101-daily.html", "posts/20261025-daily.html"]
    assert all(item["date"].endswith("T09:00:00+08:00") for item in listed)
    page = Path("docs/posts/20261101-daily.html").read_text()
    assert "2026-11-01 09:00 · Asia/Taipei" in page
    sources = listed[0]["provenance"]["sources"]
    source_urls = [item["url"] for item in sources]
    assert len(source_urls) == len(set(source_urls))
    assert "https://example.com/shared-paper" in source_urls
    assert "https://example.com/other-paper" in source_urls
    assert "https://example.com/third" in source_urls
    assert "https://example.com/only-in-digest" in source_urls
    assert "https://example.com/third" in page
    assert "https://example.com/only-in-digest" in page
    assert "模型栏目的独立分析" in page
    assert "硬件栏目的另一段分析" in page
    assert page.count("硬件栏目的另一段分析") == 1
    redirect = Path("docs/posts/20261101-model_research.html").read_text()
    assert 'rel="canonical" href="https://vorasio.com/posts/20261101-daily.html"' in redirect
    assert "noindex" in redirect
    assert "data-legacy-redirect" in redirect
    feed = Path("docs/feed.xml").read_text()
    sitemap = Path("docs/sitemap.xml").read_text()
    index = Path("docs/index.html").read_text()
    assert "20261101-daily.html" in feed and "model_research" not in feed
    assert "20261101-daily.html" in sitemap and "model_research" not in sitemap
    assert "model_research.html" not in index
    receipt = json.loads(Path("state/seen.json").read_text())["daily_notifications"]["2026-11-01"]
    assert receipt["sent_at"] == "2026-11-01T11:00:00+00:00"
    assert receipt["migrated"] is True
    assert receipt["telegram"] != "sent" if "telegram" in receipt else True
    replay = Path("docs/posts/20261025-daily.html").read_text()
    assert "2026-10-25 09:00 · Asia/Taipei" in replay
    assert "补发到 10 月 25 日" in replay
    before = Path("docs/posts/20261101-daily.html").read_bytes()
    again = migrate()
    assert again["counts"]["reports_after"] == 2
    assert Path("docs/posts/20261101-daily.html").read_bytes() == before
    assert sent == []


def test_plan_day_groups_replay_by_execution_date():
    fragment = entry("2026-10-25", "paper_brief", "posts/20261025-paper_brief.html",
                     date="2026-10-26T02:00:00+08:00", execution_date="2026-10-25")
    assert edition_day(fragment) == "2026-10-25"
    assert edition_stamp(date(2026, 10, 25)).isoformat() == "2026-10-25T09:00:00+08:00"


def test_new_edition_publishes_one_page_and_blocks_a_second_run(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("config").mkdir()
    Path("config/sources.yml").write_text("topics:\n  model_research:\n    title: 模型\n    max_items: 3\n"
                                          "  open_source:\n    title: 开源\n    max_items: 3\n")
    Path("docs/posts").mkdir(parents=True)
    Path("docs/posts.json").write_text("[]")
    observed = []

    def fake_prepare(topic, config, state_path, now, dry_run=False, publish_key=None, *,
                     capture=None, clock=None, blocked=None):
        observed.append(clock)
        if topic == "open_source":
            capture.append({"ok": False, "reason": "analysis_rejected", "topic": topic, "title": "开源",
                            "report": "", "items": [], "analysis": None})
            return False
        item = Item("a", "Paper", "https://example.com/paper", "2026-11-16T01:00:00+00:00",
                    "evidence " * 20, "src")
        capture.append({"ok": True, "reason": "prepared", "topic": topic, "title": "模型",
                        "report": "模型小节正文，带来源说明。", "items": [item],
                        "analysis": {"provider": "Groq", "model": "test"}})
        return True

    monkeypatch.setattr("research_bot.main.prepare_topic", fake_prepare)
    moment = datetime(2026, 11, 16, 7, tzinfo=UTC)
    assert prepare_daily_report(moment, sources_path=Path("config/sources.yml")) is False
    assert not Path("docs/posts/20261116-daily.html").exists()
    assert all(clock == edition_cutoff(moment) - COLLECTION_GRACE for clock in observed)

    def only_model(*args, **kwargs):
        capture = kwargs["capture"]
        if args[0] == "open_source":
            capture.append({"ok": False, "reason": "no_matching_in_window", "topic": "open_source", "title": "开源",
                            "report": "", "items": [], "analysis": None})
            return False
        return fake_prepare(*args, **kwargs)

    monkeypatch.setattr("research_bot.main.prepare_topic", only_model)
    assert prepare_daily_report(moment, sources_path=Path("config/sources.yml")) is True
    page = Path("docs/posts/20261116-daily.html").read_text()
    assert "2026-11-16 09:00 · Asia/Taipei" in page
    assert "模型小节正文" in page
    assert list(Path("docs/posts").glob("*.html")) == [Path("docs/posts/20261116-daily.html")]
    saved = json.loads(Path("docs/posts.json").read_text())
    assert len(saved) == 1
    assert saved[0]["date"] == "2026-11-16T09:00:00+08:00"
    pending = json.loads(Path("work/pending.json").read_text())
    assert pending["notify"] is True
    assert pending["topic"] == "daily_report"
    from research_bot import schedule
    assert schedule.due_slots(moment, schedule.load(), saved) == []


def test_retired_slot_and_workflows_cannot_publish_fragments():
    project = Path(__file__).resolve().parents[1]
    editorial = (project / ".github/workflows/editorial-day.yml").read_text()
    preview = (project / ".github/workflows/preview-day.yml").read_text()
    replay = (project / ".github/workflows/replay-day.yml").read_text()
    research = (project / ".github/workflows/_research.yml").read_text()
    assert "morning_radar" not in editorial
    assert "daily_digest" not in preview
    assert "daily_report" in preview
    assert "morning_radar" not in replay
    assert "--dry-run" in research
    loaded = yaml.safe_load((project / "config/editorial.yml").read_text())
    assert list(loaded["slots"]) == ["daily_report"]


def test_domain_hub_lists_one_daily_under_each_mapped_section(tmp_path):
    from research_bot.domain_hub import render_domain_hub

    posts = tmp_path / "posts"
    posts.mkdir()
    (posts / "20261101-daily.html").write_text("<html><body>daily</body></html>")
    (tmp_path / "posts.json").write_text(json.dumps([{
        "title": "日报", "url": "posts/20261101-daily.html", "status": "published", "count": 2,
        "topic": "daily_report", "date": "2026-11-01T09:00:00+08:00",
        "sections": [
            {"topic": "model_research", "source_topic": "model_research", "anchor": "edition-1", "title": "模型"},
            {"topic": "paper_brief", "source_topic": "efficient_ai", "anchor": "edition-2", "title": "高效"},
        ],
    }]))
    page = render_domain_hub(tmp_path).read_text()
    assert 'href="../posts/20261101-daily.html#edition-1"' in page
    assert 'href="../posts/20261101-daily.html#edition-2"' in page
    assert page.count("20261101-daily.html") == 2


def test_collect_clock_is_the_cutoff_not_the_wall_clock():
    moment = datetime(2026, 11, 16, 8, tzinfo=UTC)
    cutoff = edition_cutoff(moment)
    assert in_lookback(moment, "instant", moment - timedelta(hours=1), moment)
    assert not in_lookback(moment, "instant", cutoff - timedelta(hours=72), cutoff)
    assert cutoff < moment
