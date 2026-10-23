from datetime import UTC, datetime

from research_bot.core import Item, canonical_url, contains_term, fallback_report, report_is_complete, split_message, unseen, update_state
from research_bot.editorial import resolve_slot
from research_bot.site import base_url, linkify_bare_urls, publish_post


def sample(uid: str) -> Item:
    return Item(uid, "title", f"https://example.com/{uid}", "2026-01-01T00:00:00+00:00", "abstract", "test")


def test_canonical_url_removes_tracking_query_and_fragment():
    assert canonical_url("HTTPS://Example.COM/a/?utm_source=x#part") == "https://example.com/a"


def test_state_deduplicates_and_is_bounded():
    state = {"version": 1, "topics": {}}
    now = datetime.now(UTC)
    update_state(state, "ai_papers", [sample("a")], now)
    assert unseen([sample("a"), sample("b")], state, "ai_papers") == [sample("b")]
    assert "a" in state["all_ids"]


def test_state_deduplicates_across_topics():
    state = {"version": 1, "topics": {}}
    now = datetime.now(UTC)
    update_state(state, "model_research", [sample("shared")], now)
    assert unseen([sample("shared")], state, "efficient_ai") == []


def test_split_message_preserves_text_and_limits_chunks():
    text = ("段落内容。" * 900) + "\n\n结尾"
    chunks = split_message(text, 500)
    assert all(len(chunk) <= 500 for chunk in chunks)
    assert "".join(chunks).replace("\n", "") == text.strip().replace("\n", "")


def test_pages_url_for_project_repository(monkeypatch):
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    monkeypatch.setenv("GITHUB_REPOSITORY", "alice/research")
    assert base_url() == "https://alice.github.io/research"


def test_publish_post_escapes_raw_html(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://example.com/research")
    url = publish_post("ai_papers", "AI 最新论文", datetime.now(UTC), "# 结论\n<script>alert(1)</script>", [sample("a")])
    page = next((tmp_path / "docs" / "posts").glob("*.html")).read_text()
    assert url.startswith("https://example.com/research/posts/")
    assert "<script>" not in page
    assert "&lt;script&gt;" in page


def test_publish_post_renders_markdown_tables(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://example.com/research")
    report = "| # | 趋势 |\n|---|---|\n| 1 | 自监督学习 |"
    publish_post("ai_papers", "AI 最新论文", datetime.now(UTC), report, [sample("a")])
    page = next((tmp_path / "docs" / "posts").glob("*.html")).read_text()
    assert "<table>" in page
    assert "<th>趋势</th>" in page


def test_publish_post_promotes_leading_bold_title(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://example.com/research")
    report = "**AI 最新论文深度简报（2026‑10‑21）**\n\n## 趋势\n正文"
    publish_post("ai_papers", "AI 最新论文", datetime.now(UTC), report, [sample("a")])
    page = next((tmp_path / "docs" / "posts").glob("*.html")).read_text()
    assert "<h1>AI 最新论文深度简报（2026‑10‑21）</h1>" in page
    assert "<p><strong>AI 最新论文深度简报" not in page


def test_bare_urls_are_clickable_without_breaking_markdown_links():
    text = "来源：https://example.com/a\n[已有链接](https://example.com/b)"
    converted = linkify_bare_urls(text)
    assert "<https://example.com/a>" in converted
    assert "[已有链接](https://example.com/b)" in converted


def test_report_completeness_requires_all_sections_and_citations():
    items = [sample("a"), sample("b")]
    report = "## 本期要点\n[1] [2]\n## 逐项速览\n内容\n## 值得采取的行动\n内容\n## 参考资料\n内容"
    assert report_is_complete(report, items, "brief")
    assert not report_is_complete(report.replace("## 参考资料", "参考资料"), items, "brief")
    assert not report_is_complete(report.replace("[1] [2]", "- 未标注来源的确定性结论"), items, "brief")


def test_fallback_report_keeps_sources_and_resource_boundary():
    resource = Item("r", "Free service", "https://example.com/free", "2026-01-01T00:00:00+00:00", "可能免费", "search", "resource")
    report = fallback_report([resource], "radar")
    assert "## 今日免费 VPS 与 AI 资源" in report
    assert "免费条件须打开原始页面核验" in report
    assert "https://example.com/free" in report


def test_editorial_weekday_topic_resolution():
    now = datetime(2026, 10, 23, 6, tzinfo=UTC)  # Friday in Beijing
    editorial = {"slots": {"paper": {"topic_by_weekday": {"5": "multimodal"}, "title": "午间速览"}}}
    topics = {"multimodal": {"title": "多模态", "max_items": 8}}
    topic, config = resolve_slot("paper", now, editorial, topics)
    assert topic == "multimodal"
    assert config["title"] == "午间速览"


def test_source_specific_filters_reject_unrelated_free_result(monkeypatch):
    import research_bot.core as core

    feed = b"""<rss><channel><item><title>Free game downloads</title><link>https://example.com/game</link>
    <pubDate>Fri, 23 Oct 2026 00:00:00 GMT</pubDate><description>Free mods</description></item></channel></rss>"""

    class Response:
        content = feed

        def raise_for_status(self):
            return None

    monkeypatch.setattr(core.httpx.Client, "get", lambda *args, **kwargs: Response())
    topic = {
        "lookback_hours": 48,
        "sources": [{"name": "search", "url": "https://example.com/rss", "required_all": ["free"], "required_any": ["vps"]}],
    }
    assert core.collect(topic, datetime(2026, 10, 23, 1, tzinfo=UTC)) == []


def test_topic_can_require_nonempty_source_summary(monkeypatch):
    import research_bot.core as core

    feed = b"""<rss><channel><item><title>AI release</title><link>https://example.com/release</link>
    <pubDate>Fri, 23 Oct 2026 00:00:00 GMT</pubDate><description></description></item></channel></rss>"""

    class Response:
        content = feed

        def raise_for_status(self):
            return None

    monkeypatch.setattr(core.httpx.Client, "get", lambda *args, **kwargs: Response())
    topic = {"lookback_hours": 48, "require_summary": True, "sources": [{"name": "official", "url": "https://example.com/rss"}]}
    assert core.collect(topic, datetime(2026, 10, 23, 1, tzinfo=UTC)) == []


def test_short_filter_terms_use_word_boundaries():
    assert contains_term("a free ai api", "ai")
    assert not contains_term("documentation is available", "ai")


def test_charter_and_timeline_publish_states(tmp_path, monkeypatch):
    from research_bot.charter import charter_text

    assert "求真" in charter_text()
    monkeypatch.chdir(tmp_path)
    publish_post("dev_practice", "开发实践", datetime.now(UTC), "## 本时段状态\n暂无资料", [])
    page = next((tmp_path / "docs/posts").glob("*.html")).read_text()
    index = (tmp_path / "docs/index.html").read_text()
    assert "未经运行验证" in page
    assert "暂无新内容" in index
    assert "<h1>VORASIO</h1>" in index
    assert "以求证理解智能" not in index
    assert (tmp_path / "docs/about.html").exists()
    publish_post("model_research", "模型研究", datetime.now(UTC), "## 来源访问异常\n来源暂时不可用", [])
    assert "来源访问异常" in (tmp_path / "docs/index.html").read_text()


def test_url_dedup_survives_changed_feed_id():
    from dataclasses import replace

    state = {"version": 1, "topics": {}}
    update_state(state, "one", [sample("old")], datetime.now(UTC))
    assert unseen([replace(sample("old"), uid="new-id")], state, "two") == []
