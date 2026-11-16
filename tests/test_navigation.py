import re
from pathlib import Path

from research_bot.navigation import (
    NAV_LABELS,
    apply_header_nav,
    render_nav,
    section_for_site_path,
)
from research_bot.site import shell
from tests.test_theme_contrast import _tokens, contrast

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
LABELS = list(NAV_LABELS)


def header_nav(page: str) -> str:
    header = re.search(r"<header\b[^>]*>.*?</header>", page, re.S)
    assert header, "missing header"
    nav = re.search(r"<nav\b[^>]*>.*?</nav>", header.group(0), re.S)
    assert nav, "missing header nav"
    return nav.group(0)


def labels(nav: str) -> list[str]:
    return re.findall(r"<a\b[^>]*>([^<]+)</a>", nav)


def current_label(nav: str) -> str:
    found = re.findall(r'<a\b(?=[^>]*aria-current="page")[^>]*>([^<]+)</a>', nav)
    assert len(found) == 1
    return found[0]


def test_nav_order_is_fixed_for_every_current_section():
    orders = {tuple(labels(render_nav("../", key))) for key, _, _ in (
        ("domains", "", ""), ("daily", "", ""), ("knowledge", "", ""), ("courses", "", ""),
        ("tools", "", ""), ("subscribe", "", ""), ("services", "", ""), ("about", "", ""),
    )}
    assert orders == {tuple(LABELS)}
    assert LABELS == ["领域导航", "日报", "AI 知识科普", "AI 学习", "AI 工具", "订阅精选", "开发咨询", "关于"]
    assert "全部更新" not in render_nav("", "daily")
    assert 'href="index.html#latest"' in render_nav("", "daily")


def test_current_section_is_marked_without_moving_it():
    for key, label, href in (
        ("domains", "领域导航", "domains/index.html"),
        ("daily", "日报", "index.html#latest"),
        ("courses", "AI 学习", "../../courses/index.html"),
    ):
        root = "../../" if key == "courses" else ""
        nav = render_nav(root, key)
        assert labels(nav) == LABELS
        assert current_label(nav) == label
        assert f'href="{href}"' in nav or (key != "courses" and f'href="{href}"' in nav)
    child = render_nav("../../", "courses")
    assert 'href="../../courses/index.html"' in child
    assert 'href="../../index.html#latest"' in child
    assert child.count('aria-current="page"') == 1


def test_section_mapping_covers_children_and_hash():
    assert section_for_site_path("index.html") == "daily"
    assert section_for_site_path("index.html#latest") == "daily"
    assert section_for_site_path("posts/20261116-daily.html") == "daily"
    assert section_for_site_path("domains/index.html") == "domains"
    assert section_for_site_path("knowledge/ai-ecosystem-guide.html") == "knowledge"
    assert section_for_site_path("courses/agent-engineering/01-agent-foundations.html") == "courses"
    assert section_for_site_path("tools/index.html") == "tools"
    assert section_for_site_path("subscribe.html") == "subscribe"
    assert section_for_site_path("services.html") == "services"
    assert section_for_site_path("consult.html") == "services"
    assert section_for_site_path("about.html") == "about"
    assert section_for_site_path("privacy.html") == "about"


def test_old_nav_is_replaced_in_place_and_stays_idempotent():
    old = (
        '<header class="site-header"><nav aria-label="主导航">'
        '<a href="../index.html#latest">时间线</a>'
        '<a aria-current="page" href="../courses/index.html">AI 学习</a>'
        '<a href="../domains/index.html">领域导航</a>'
        '</nav></header><main><nav aria-label="领域导航"><a href="#models">基础模型</a></nav>'
        '<p>全部更新这个词只应留在正文测试里。</p></main>'
    )
    updated = apply_header_nav(old, "../", "courses")
    assert labels(header_nav(updated)) == LABELS
    assert current_label(header_nav(updated)) == "AI 学习"
    assert '<nav aria-label="领域导航"><a href="#models">基础模型</a></nav>' in updated
    assert "全部更新这个词只应留在正文测试里。" in updated
    assert apply_header_nav(updated, "../", "courses") == updated


def test_shell_and_styles_keep_one_order_and_readable_current_item():
    page = shell("标题", "说明", "<p>正文</p>", "../", current="knowledge")
    nav = header_nav(page)
    assert labels(nav) == LABELS
    assert current_label(nav) == "AI 知识科普"
    assert "全部更新" not in nav
    assert "style.css?v=nav-1" in page and "editorial.css?v=nav-1" in page
    style = (DOCS / "assets/style.css").read_text()
    course = (DOCS / "assets/course.css").read_text()
    for css in (style, course):
        assert "flex-wrap: wrap" in css or "flex-wrap:wrap" in css
        assert "white-space: nowrap" in css or "white-space:nowrap" in css
        assert "max-width: 100%" in css or "max-width:100%" in css
        assert 'a[aria-current="page"]' in css
        assert "font-weight: 700" in css or "font-weight:700" in css
        assert "text-decoration: underline" in css or "text-decoration:underline" in css
        assert "justify-content: flex-start" in css or "justify-content:flex-start" in css
    light, dark = _tokens(style)
    for theme in (light, dark):
        assert contrast(theme["ink"], theme["paper"]) >= 4.5
        assert contrast(theme["muted"], theme["paper"]) >= 4.5


def test_committed_pages_share_the_nav_and_current_section():
    checked = 0
    for path in sorted(DOCS.rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        if "<header" not in text:
            continue
        relative = path.relative_to(DOCS).as_posix()
        nav = header_nav(text)
        assert labels(nav) == LABELS, relative
        assert "全部更新" not in nav, relative
        assert "时间线</a>" not in nav, relative
        expected = dict(zip(
            ("domains", "daily", "knowledge", "courses", "tools", "subscribe", "services", "about"),
            LABELS, strict=True,
        ))[section_for_site_path(relative)]
        assert current_label(nav) == expected, relative
        root = "../" * (len(path.relative_to(DOCS).parts) - 1)
        assert f'href="{root}index.html#latest"' in nav, relative
        assert not re.search(r'href="/(?!/)', nav)
        checked += 1
    assert checked >= 40
