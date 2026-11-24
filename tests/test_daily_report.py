import json
from datetime import date
from pathlib import Path

import yaml

from research_bot.daily import edition_day, edition_stamp, migrate


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


def test_rotation_is_only_daily_publisher_and_callers_exist():
    project = Path(__file__).resolve().parents[1]
    workflows = project / ".github/workflows"
    retired = {"_editorial.yml", "preview-day.yml", "replay-day.yml", "run-all.yml", "efficient-ai.yml", "embodied.yml",
               "product-safety.yml"}
    assert not (retired & {path.name for path in workflows.glob("*.yml")})
    docs = (project / "README.md").read_text()
    assert all(name not in docs for name in retired)
    for path in workflows.glob("*.yml"):
        config = yaml.load(path.read_text(), Loader=yaml.BaseLoader)
        for job in config.get("jobs", {}).values():
            call = job.get("uses", "")
            if call.startswith("./.github/workflows/"):
                assert (project / call).is_file(), f"{path.name}: missing {call}"
            if call.endswith("/_rotation.yml"):
                assert path.name in {"editorial-day.yml", "catchup.yml"}
                assert "default_branch" in job["if"]
    for name in ("editorial-day.yml", "catchup.yml"):
        assert "./.github/workflows/_rotation.yml" in (workflows / name).read_text()
    assert "catchup.yml/dispatches" in (project / "infrastructure/cloudflare/worker.mjs").read_text()
    loaded = yaml.safe_load((project / "config/editorial.yml").read_text())
    assert list(loaded["slots"]) == ["daily_report"]
    assert loaded["rotation_batch_hours"] == [9, 13, 17] and loaded["rotation_assembly_hour"] == 18


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
