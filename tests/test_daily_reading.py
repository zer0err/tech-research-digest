from datetime import datetime
from zoneinfo import ZoneInfo

from research_bot.daily import markdown_sections, render_daily_page

ZONE = ZoneInfo("Asia/Taipei")
ISSUE = datetime(2026, 11, 24, 18, 15, tzinfo=ZONE)
PLANNED = ISSUE.replace(minute=0)


def row(topic, report, items):
    return {"topic": topic, "title": topic, "report": report, "items": items}


def render(parts, rotation=True):
    return render_daily_page(
        "VORASIO AI 日报", ISSUE, markdown_sections(parts), [], {}, "说明文字", "posts/20261124-daily.html",
        scheduled_at=PLANNED if rotation else None,
    )


def test_rotation_reference_ids_follow_validated_order_per_section():
    content = "## 本期结论\n- 原始要点 [2]\n\n`字面 [2]`\n\n## 参考资料\n不采用模型的出处顺序。"
    groups = [
        row("models", content, [{"title": "一", "url": "https://one.example/a"},
                                {"title": "<二>", "url": "https://two.example/b"}]),
        row("inference", content, [{"title": "二", "url": "https://two.example/b"},
                                   {"title": "三", "url": "https://three.example/c"}]),
        row("other", "- 人工核验条目 [1]", [{"title": "其他", "url": "https://other.example"}]),
    ]
    page = render(groups)
    assert 'id="edition-1-source-2"><a href="https://two.example/b">&lt;二&gt;</a>' in page
    assert 'id="edition-2-source-2"><a href="https://three.example/c">三</a>' in page
    assert 'id="edition-3-source-1"><a href="https://other.example">其他</a>' in page
    assert page.count("原始要点 [2]") == 2 and page.count("<code>字面 [2]</code>") == 2
    assert "不采用模型的出处顺序" not in page
    assert 'href="https://vorasio.com/posts/20261124-daily.html"' in page
    assert 'assets/article.js?v=reading-1' in page


def test_legacy_editorial_copy_and_ambiguous_future_references_fail_closed():
    sample = row("inference", "## 参考资料\n旧原稿 [1]。\n", [{"title": "一", "url": "https://one.example"}])
    legacy = render([sample], rotation=False)
    assert "旧原稿 [1]" in legacy and "edition-1-source-1" not in legacy
    bad = row("inference", "## 本期结论\n正文 [1]\n\n## 参考资料\n出处。", [{"url": "javascript:void(0)"}])
    assert "edition-1-source-1" not in render([bad])
    fenced = row("other", "```text\n## 参考资料\n字面语句\n```\n\n列表 [1]",
                 [{"title": "一", "url": "https://one.example"}])
    assert "字面语句" in render([fenced]) and "edition-1-source-1" in render([fenced])


def test_ambiguous_generated_reference_block_is_not_replaced():
    item = {"title": "原始来源", "url": "https://one.example"}
    missing = row("models", "## 本期结论\n旧稿没有参考资料 [1]。", [item])
    repeated = row("models", "## 参考资料\n第一份。\n\n## 参考资料\n第二份。", [item])
    result = render([missing, repeated])
    assert "edition-1-source-1" not in result and "edition-2-source-1" not in result
    assert "旧稿没有参考资料 [1]" in result and "第一份。" in result and "第二份。" in result
