from datetime import UTC, datetime

from research_bot.core import Item, canonical_url, split_message, unseen, update_state
from research_bot.site import base_url, publish_post


def sample(uid: str) -> Item:
    return Item(uid, "title", "https://example.com/x", "2026-01-01T00:00:00+00:00", "abstract", "test")


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
