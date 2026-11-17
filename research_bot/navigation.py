"""One fixed primary navigation for every public page.

The order does not change when the current section changes. "日报" opens the
daily-report list at index.html#latest. That anchor is not a feed of courses,
tools, or knowledge pages.
"""
from __future__ import annotations

import html
import re
from pathlib import Path

ASSET_VERSION = "nav-1"
NAV_ITEMS = (
    ("domains", "领域导航", "domains/index.html"),
    ("daily", "日报", "index.html#latest"),
    ("knowledge", "AI 知识科普", "knowledge/index.html"),
    ("courses", "AI 学习", "courses/index.html"),
    ("tools", "AI 工具", "tools/index.html"),
    ("subscribe", "订阅精选", "subscribe.html"),
    ("services", "开发咨询", "services.html"),
    ("about", "关于", "about.html"),
)
NAV_LABELS = tuple(label for _, label, _ in NAV_ITEMS)
_HEADER = re.compile(r"<header\b[^>]*>.*?</header>", re.S)
_NAV = re.compile(r"<nav\b[^>]*>.*?</nav>", re.S)
_ASSET = re.compile(r"(assets/(?:style|editorial|course|knowledge)\.css)(?:\?v=[^\"']*)?")


def relative_root_for(page: Path, site_dir: Path) -> str:
    return "../" * (len(page.resolve().relative_to(site_dir.resolve()).parts) - 1)


def section_for_site_path(site_path: str) -> str:
    """Map a site-relative path, including a child page or #latest, to one nav item."""
    path = site_path.replace("\\", "/").split("?", 1)[0]
    path = path.split("#", 1)[0].lstrip("./")
    name = path.rsplit("/", 1)[-1]
    if path.startswith("domains/"):
        return "domains"
    if path.startswith("knowledge/"):
        return "knowledge"
    if path.startswith("courses/"):
        return "courses"
    if path.startswith("tools/"):
        return "tools"
    if path.startswith("posts/") or name in {"index.html", ""}:
        return "daily"
    if name == "subscribe.html":
        return "subscribe"
    if name in {"services.html", "consult.html"}:
        return "services"
    if name in {"about.html", "privacy.html"}:
        return "about"
    return ""


def render_nav(relative_root: str, current: str) -> str:
    if current and current not in {key for key, _, _ in NAV_ITEMS}:
        raise ValueError(f"Unknown navigation section: {current}")
    links = []
    for key, label, href in NAV_ITEMS:
        current_attr = ' aria-current="page"' if key == current else ""
        links.append(
            f'<a{current_attr} data-label="{html.escape(label, quote=True)}" '
            f'href="{html.escape(relative_root + href, quote=True)}">{html.escape(label)}</a>'
        )
    return '<nav aria-label="主导航">' + "".join(links) + "</nav>"


def apply_header_nav(page: str, relative_root: str, current: str) -> str:
    """Replace only the header navigation. In-page navs and article text stay put."""

    def replace_header(match: re.Match[str]) -> str:
        header = match.group(0)
        if not _NAV.search(header):
            return header
        return _NAV.sub(render_nav(relative_root, current), header, count=1)

    updated = _HEADER.sub(replace_header, page, count=1)
    return _ASSET.sub(rf"\1?v={ASSET_VERSION}", updated)


def apply_site_navigation(site_dir: Path = Path("docs")) -> int:
    changed = 0
    for page in sorted(site_dir.rglob("*.html")):
        if not page.is_file() or page.is_symlink():
            continue
        original = page.read_text(encoding="utf-8")
        if "<header" not in original:
            continue
        relative = page.relative_to(site_dir).as_posix()
        updated = apply_header_nav(original, relative_root_for(page, site_dir), section_for_site_path(relative))
        if updated != original:
            page.write_text(updated, encoding="utf-8")
            changed += 1
    return changed
