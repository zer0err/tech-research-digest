from __future__ import annotations

import html
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from markdown_it import MarkdownIt

from .navigation import CHROME_CSS, render_footer, render_header
from .schedule import EDITORIAL, ZONE

if TYPE_CHECKING:
    from .core import Item

SITE_DIR = Path("docs")
POSTS_DIR = SITE_DIR / "posts"
INDEX_DATA = SITE_DIR / "posts.json"

TOPICS = {
    name: (str(slot["page_title"]), str(slot["cadence"]))
    for name, slot in EDITORIAL["slots"].items()
}
TOPICS.update({
    "efficient_ai": ("高效 AI、模型压缩与端侧适配", "周一、周四 14:00"),
    "inference_systems": ("推理引擎、编译器与嵌入式系统", "周二 14:00"),
    "ai_hardware": ("AI 芯片、计算架构与硬件平台", "周三 14:00"),
    "multimodal": ("多模态感知、音视频与人机交互", "周五 14:00"),
    "embodied": ("Agent、机器人与具身智能", "周二、周六 16:00"),
    "product_safety": ("智能硬件产品化、可靠性与安全", "周日 14:00"),
    "ai_papers": ("AI 最新论文（历史）", "已归档"),
    "audio": ("音频技术研究（历史）", "已归档"),
})

EDITORIAL_SLOTS = [TOPICS[name] for name in EDITORIAL["slots"]]


def base_url() -> str:
    explicit = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
    if explicit:
        return explicit
    repository = os.getenv("GITHUB_REPOSITORY", "local/tech-research")
    owner, name = repository.split("/", 1)
    return f"https://{owner}.github.io" + ("" if name.lower() == f"{owner.lower()}.github.io" else f"/{name}")


def shell(
    title: str, description: str, body: str, relative_root: str = "", extra_head: str = "", *,
    digest_home: bool = False, article_asset_version: str = "replay-6",
    section: str | None = None, current_page: bool = False, footer_note: str | None = None,
) -> str:
    if digest_home:
        section, current_page = "daily", True
    page_class = ' class="digest-home"' if digest_home else ''
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><meta name="description" content="{html.escape(description, quote=True)}">
<link rel="alternate" type="application/rss+xml" title="VORASIO" href="{relative_root}feed.xml">{extra_head}
<link rel="stylesheet" href="{relative_root}assets/style.css">
<link rel="stylesheet" href="{relative_root}assets/growth.css">
<link rel="stylesheet" href="{relative_root}assets/editorial.css?v=presentation-1">
<link rel="stylesheet" href="{relative_root}assets/{CHROME_CSS}">
<script type="module" src="{relative_root}assets/article.js?v={html.escape(article_asset_version, quote=True)}"></script></head>
<body{page_class}><a class="reading-skip" href="#main">跳到正文</a>
{render_header(relative_root, section=section, current_page=current_page)}
<main id="main" tabindex="-1">{body}</main>{render_footer(relative_root, editorial_credit=digest_home, note=footer_note)}</body></html>"""


def linkify_bare_urls(markdown: str) -> str:
    return re.sub(r"(?<![\(<])(?P<url>https?://[^\s<>)，。；,;]+)", r"<\g<url>>", markdown)


def publish_post(topic: str, title: str, now: datetime, report: str, items: list[Item], *,
                 analysis: dict | None = None, source_topic: str | None = None) -> str:
    from .growth import article_callout
    from .provenance import metadata, render
    default_analysis = {"provider": "程序汇总（未调用 AI）", "model": "不适用"} if topic == 'daily_digest' else None
    provenance = metadata(items, analysis or default_analysis)
    now = now.astimezone(ZONE)
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    (SITE_DIR / "assets").mkdir(parents=True, exist_ok=True)
    slug = f"{now:%Y%m%d}-{topic}.html"
    url = f"{base_url()}/posts/{slug}"
    md = MarkdownIt("commonmark", {"html": False}).enable("table")
    title_match = re.match(r"^\s*\*\*(.+?)\*\*\s*(?:\n+|$)", report)
    display_title = title_match.group(1).strip() if title_match else (
        title if f"{now:%Y-%m-%d}" in title else f"{title}（{now:%Y-%m-%d}）"
    )
    report_body = report[title_match.end() :].lstrip() if title_match else report
    report_body = linkify_bare_urls(report_body)
    topic_name = TOPICS.get(topic, (title, "定期更新"))[0]
    status = "empty" if not items else "published"
    summary = re.sub(r"\s+", " ", re.sub(r"[#*\[\]`]+", "", report)).strip()[:160]
    disclosure = "实践参考，未经运行验证。" if topic == "dev_practice" else "依据公开来源自动整理，请核对证据边界。"
    edition_date = os.getenv("REPLAY_EDITION_DATE")
    published_at = datetime.now(ZONE) if edition_date else now
    if edition_date:
        disclosure += f" 本文为 {edition_date} 期补发，实际发布时间见侧栏；按历史日期筛选当前仍可访问的来源，不是历史网页快照。"
    article = (
        '<div class="article-layout"><aside class="article-meta">'
        f'<p class="eyebrow">{html.escape(topic_name)}</p><dl><dt>发布时间</dt>'
        f'<dd data-published-at="{published_at.isoformat()}">{published_at:%Y-%m-%d %H:%M} · UTC+8</dd>'
        f'<dt>研究条目</dt><dd>{len(items)} 项</dd><dt>阅读提示</dt><dd>关键结论请回查原始资料</dd></dl>'
        '<a class="back-link" href="../index.html">← 返回全部简报</a></aside>'
        f'<article><p class="kicker">RESEARCH BRIEF · {html.escape(topic_name)}</p>'
        f'<h1>{html.escape(display_title)}</h1>{render(provenance)}<p class="disclosure">{disclosure}</p>'
        f'<div class="article-body">{md.render(report_body)}</div>'
        f'{article_callout("../", "/posts/" + slug)}</article></div>'
    )
    (POSTS_DIR / slug).write_text(shell(display_title, f"{display_title}：{len(items)} 项最新研究", article, "../", section="daily"))
    entries = json.loads(INDEX_DATA.read_text()) if INDEX_DATA.exists() else []
    entries = [entry for entry in entries if entry.get("url") != f"posts/{slug}"]
    entries.insert(
        0,
        {
            "title": display_title,
            "date": published_at.isoformat(),
            **({"execution_date": edition_date} if edition_date else {}),
            "count": len(items),
            "url": f"posts/{slug}",
            "topic": topic,
            **({"source_topic": source_topic} if source_topic else {}),
            "status": status,
            "summary": summary,
            "provenance": provenance,
        },
    )
    INDEX_DATA.write_text(json.dumps(entries[:365], ensure_ascii=False, indent=2) + "\n")
    render_index(entries[:365])
    return url


def render_index(entries: list[dict[str, object]]) -> None:
    from .timeline import render_timeline

    render_timeline(entries)
    from .domain_hub import render_domain_hub
    from .growth import render_growth_pages

    render_domain_hub()
    render_growth_pages()
