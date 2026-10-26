from __future__ import annotations

import html
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from markdown_it import MarkdownIt

if TYPE_CHECKING:
    from .core import Item

SITE_DIR = Path("docs")
POSTS_DIR = SITE_DIR / "posts"
INDEX_DATA = SITE_DIR / "posts.json"

TOPICS = {
    "morning_radar": ("AI 晨间雷达与免费资源", "每日 09:07"),
    "model_research": ("AI 模型、训练与基础研究", "每日 10:17"),
    "open_source": ("AI 开源项目与工具更新", "每日 11:27"),
    "paper_brief": ("AI 论文午间速览", "每日 12:37"),
    "prompt_engineering": ("Prompt、上下文工程与评测", "每日 13:47"),
    "core_research": ("智能硬件技术专题", "每日 14:07"),
    "dev_practice": ("AI 开发实践与部署", "每日 15:17"),
    "applied_ai": ("AI 应用与落地专题", "每日 16:27"),
    "ecosystem": ("AI 人物、机构与产业生态", "每日 17:37"),
    "daily_digest": ("VORASIO AI 日报", "每日 18:47"),
    "efficient_ai": ("高效 AI、模型压缩与端侧适配", "周一、周四 14:00"),
    "inference_systems": ("推理引擎、编译器与嵌入式系统", "周二 14:00"),
    "ai_hardware": ("AI 芯片、计算架构与硬件平台", "周三 14:00"),
    "multimodal": ("多模态感知、音视频与人机交互", "周五 14:00"),
    "embodied": ("Agent、机器人与具身智能", "周二、周六 16:00"),
    "product_safety": ("智能硬件产品化、可靠性与安全", "周日 14:00"),
    "ai_papers": ("AI 最新论文（历史）", "已归档"),
    "audio": ("音频技术研究（历史）", "已归档"),
}

EDITORIAL_SLOTS = [
    TOPICS[key]
    for key in (
        "morning_radar",
        "model_research",
        "open_source",
        "paper_brief",
        "prompt_engineering",
        "core_research",
        "dev_practice",
        "applied_ai",
        "ecosystem",
        "daily_digest",
    )
]


def base_url() -> str:
    explicit = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
    if explicit:
        return explicit
    repository = os.getenv("GITHUB_REPOSITORY", "local/tech-research")
    owner, name = repository.split("/", 1)
    return f"https://{owner}.github.io" + ("" if name.lower() == f"{owner.lower()}.github.io" else f"/{name}")


def shell(title: str, description: str, body: str, relative_root: str = "") -> str:
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><meta name="description" content="{html.escape(description, quote=True)}">
<link rel="stylesheet" href="{relative_root}assets/style.css">
<link rel="stylesheet" href="{relative_root}assets/editorial.css?v=timeline-2">
<script type="module" src="{relative_root}assets/article.js?v=visitor-time-4"></script></head>
<body><header class="site-header"><a class="brand" href="{relative_root}index.html"><span>VORASIO</span> 研究简报</a>
<nav><a href="{relative_root}index.html#latest">时间线</a><a href="{relative_root}about.html">关于</a></nav></header>
<main>{body}</main><footer><strong>VORASIO 研究简报</strong>
<span>由 GitHub Actions 定时采集，Groq 辅助分析。重要结论请核对原论文。</span></footer></body></html>"""


def linkify_bare_urls(markdown: str) -> str:
    return re.sub(r"(?<![\(<])(?P<url>https?://[^\s<>)，。；,;]+)", r"<\g<url>>", markdown)


def publish_post(topic: str, title: str, now: datetime, report: str, items: list[Item]) -> str:
    now = now.astimezone(ZoneInfo("Asia/Shanghai"))
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
    status = "empty" if not items else ("fallback" if "降级为" in report else "published")
    if "## 来源访问异常" in report:
        status = "source_error"
    summary = re.sub(r"\s+", " ", re.sub(r"[#*\[\]`]+", "", report)).strip()[:160]
    disclosure = "实践参考，未经运行验证。" if topic == "dev_practice" else "依据公开来源自动整理，请核对证据边界。"
    article = (
        '<div class="article-layout"><aside class="article-meta">'
        f'<p class="eyebrow">{html.escape(topic_name)}</p><dl><dt>发布时间</dt>'
        f'<dd data-published-at="{now.isoformat()}">{now:%Y-%m-%d %H:%M} · UTC+8</dd>'
        f'<dt>研究条目</dt><dd>{len(items)} 项</dd><dt>阅读提示</dt><dd>关键结论请回查原始资料</dd></dl>'
        '<a class="back-link" href="../index.html">← 返回全部简报</a></aside>'
        f'<article><p class="kicker">RESEARCH BRIEF · {html.escape(topic_name)}</p>'
        f'<h1>{html.escape(display_title)}</h1><p class="disclosure">{disclosure}</p>'
        f'<div class="article-body">{md.render(report_body)}</div></article></div>'
    )
    (POSTS_DIR / slug).write_text(shell(display_title, f"{display_title}：{len(items)} 项最新研究", article, "../"))
    entries = json.loads(INDEX_DATA.read_text()) if INDEX_DATA.exists() else []
    entries = [entry for entry in entries if entry.get("url") != f"posts/{slug}"]
    entries.insert(
        0,
        {
            "title": display_title,
            "date": now.isoformat(),
            "count": len(items),
            "url": f"posts/{slug}",
            "topic": topic,
            "status": status,
            "summary": summary,
        },
    )
    INDEX_DATA.write_text(json.dumps(entries[:365], ensure_ascii=False, indent=2) + "\n")
    render_index(entries[:365])
    return url


def render_index(entries: list[dict[str, object]]) -> None:
    from .timeline import render_timeline

    render_timeline(entries)
