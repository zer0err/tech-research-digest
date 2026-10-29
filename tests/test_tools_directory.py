from __future__ import annotations

import json
import re
import copy
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

from research_bot.tool_directory import render_tools_page


ROOT = Path(__file__).parents[1]
CATALOG = json.loads((ROOT / "config/tools.json").read_text(encoding="utf-8"))
PAGE = ROOT / "docs/tools/index.html"
SCRIPT = ROOT / "docs/assets/tool-directory.js"
CSS = ROOT / "docs/assets/editorial.css"


class DirectoryParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.cards: list[dict[str, object]] = []
        self.links: list[str] = []
        self._card: dict[str, object] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if "data-tool-card" in values:
            self._card = {"attrs": values, "text": []}
            self.cards.append(self._card)
        if tag == "a" and values.get("href"):
            self.links.append(values["href"] or "")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"article", "li"}:
            self._card = None

    def handle_data(self, data: str) -> None:
        if self._card is not None:
            text = self._card["text"]
            assert isinstance(text, list)
            text.append(data)


def page_text() -> str:
    assert PAGE.is_file(), "工具目录尚未生成"
    return PAGE.read_text(encoding="utf-8")


def parsed_page() -> DirectoryParser:
    parser = DirectoryParser()
    parser.feed(page_text())
    return parser


def test_directory_renders_every_verified_record_once_without_empty_cards() -> None:
    parser = parsed_page()
    expected = {tool["id"] for tool in CATALOG["tools"] if tool["status"] == "active"}
    rendered = [str(card["attrs"]["data-tool-id"]) for card in parser.cards]  # type: ignore[index]

    assert len(expected) == 14
    assert len(rendered) == len(expected)
    assert set(rendered) == expected
    assert len(rendered) == len(set(rendered))
    assert all("".join(card["text"]).strip() for card in parser.cards)  # type: ignore[arg-type]


def test_cards_keep_official_links_and_filterable_category_and_access() -> None:
    parser = parsed_page()
    by_id = {
        str(card["attrs"]["data-tool-id"]): card["attrs"]  # type: ignore[index]
        for card in parser.cards
    }
    for tool in CATALOG["tools"]:
        attrs = by_id[tool["id"]]
        assert attrs["data-category"] == tool["primary_category"]
        rendered_access = set(str(attrs["data-access"]).split())
        assert rendered_access == set(tool["access"])
        assert tool["official_url"] in parser.links
        assert all(urlsplit(url).scheme == "https" for url in parser.links if url.startswith("http"))


def test_static_html_is_complete_without_javascript_and_describes_scope() -> None:
    html = page_text()
    visible = re.sub(r"<[^>]+>", " ", html)
    assert "14" in visible
    assert "首批" in visible
    assert "本地" in visible and "注册" in visible
    for tool in CATALOG["tools"]:
        assert tool["name"] in visible
        assert tool["summary_zh"] in visible


def test_directory_has_search_category_access_and_clear_controls() -> None:
    html = page_text()
    assert "data-tool-search" in html
    assert 'data-tool-filter="category"' in html
    assert 'data-tool-filter="access"' in html
    assert "data-tool-reset" in html
    assert "data-tool-empty" in html


def test_filter_script_restores_url_state_and_can_clear_empty_result() -> None:
    assert SCRIPT.is_file(), "缺少工具目录交互脚本"
    script = SCRIPT.read_text(encoding="utf-8")
    assert "URLSearchParams" in script
    assert "history.replaceState" in script or "history.pushState" in script
    assert "data-tool-reset" in script
    assert "data-tool-empty" in script
    assert "textContent" in script
    assert ".innerHTML" not in script


def test_generated_page_has_no_executable_catalog_content_or_unsafe_urls() -> None:
    html = page_text().lower()
    assert "javascript:" not in html
    assert "<iframe" not in html
    assert "<object" not in html
    assert "<embed" not in html
    assert "<script>alert" not in html


def test_renderer_escapes_untrusted_catalog_text(tmp_path: Path) -> None:
    catalog = copy.deepcopy(CATALOG)
    catalog["tools"][0]["name"] = '<script>alert("name")</script>'
    catalog["tools"][0]["summary_zh"] = '<img src=x onerror="alert(1)">'
    source = tmp_path / "tools.json"
    output = tmp_path / "index.html"
    source.write_text(json.dumps(catalog, ensure_ascii=False), encoding="utf-8")

    render_tools_page(source, output)
    html = output.read_text(encoding="utf-8")
    assert '<script>alert("name")</script>' not in html
    assert '<img src=x onerror="alert(1)">' not in html
    assert "&lt;script&gt;" in html
    assert "&lt;img src=x onerror=" in html


def test_home_and_about_navigation_link_to_directory() -> None:
    for relative in ("docs/index.html", "docs/about.html"):
        html = (ROOT / relative).read_text(encoding="utf-8")
        assert "AI 工具" in html
        assert "tools/index.html" in html


def test_mobile_css_collapses_directory_at_phone_width() -> None:
    css = CSS.read_text(encoding="utf-8")
    assert ".directory-grid" in css
    assert "@media(max-width:600px)" in css
    assert ".section-gateways,.directory-grid,.tool-filters{grid-template-columns:1fr}" in css
    assert "overflow-wrap:anywhere" in css
