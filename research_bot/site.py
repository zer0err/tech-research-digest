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
<link rel="stylesheet" href="{relative_root}assets/editorial.css"></head>
<body><header class="site-header"><a class="brand" href="{relative_root}index.html"><span>VORASIO</span> 研究简报</a>
<nav><a href="{relative_root}index.html#latest">最新研究</a><a href="{relative_root}index.html#topics">研究栏目</a></nav></header>
<main>{body}</main><footer><strong>VORASIO 研究简报</strong>
<span>由 GitHub Actions 定时采集，Groq 辅助分析。重要结论请核对原论文。</span></footer></body></html>"""


def linkify_bare_urls(markdown: str) -> str:
    return re.sub(r"(?<!\()(?P<url>https?://[^\s<>)，。；,;]+)", r"<\g<url>>", markdown)


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
    article = (
        '<div class="article-layout"><aside class="article-meta">'
        f'<p class="eyebrow">{html.escape(topic_name)}</p><dl><dt>发布日期</dt><dd>{now:%Y-%m-%d}</dd>'
        f'<dt>研究条目</dt><dd>{len(items)} 项</dd><dt>阅读提示</dt><dd>关键结论请回查原始资料</dd></dl>'
        '<a class="back-link" href="../index.html">← 返回全部简报</a></aside>'
        f'<article><p class="kicker">RESEARCH BRIEF · {html.escape(topic_name)}</p>'
        f"<h1>{html.escape(display_title)}</h1><div class=\"article-body\">{md.render(report_body)}</div></article></div>"
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
        },
    )
    INDEX_DATA.write_text(json.dumps(entries[:365], ensure_ascii=False, indent=2) + "\n")
    render_index(entries[:365])
    return url


def render_index(entries: list[dict[str, object]]) -> None:
    cards = []
    descriptions = {
        "morning_radar": "最新 AI 动态，以及当天新发现的免费 VPS 与免费 AI 服务线索。",
        "open_source": "开源项目正式版本、兼容性与迁移风险速览。",
        "prompt_engineering": "提示词、上下文工程、RAG 与评测方法更新。",
        "dev_practice": "依据官方资料整理的开发与部署实践。",
        "ecosystem": "人物、机构、实验室与开发者生态的可核验动态。",
        "daily_digest": "汇总今天已经发布的全部站内内容。",
    }
    for index, entry in enumerate(entries):
        date = str(entry["date"])[:10]
        topic_name = TOPICS.get(str(entry["topic"]), (str(entry["topic"]), ""))[0]
        card_class = "post-card featured" if index == 0 else "post-card"
        summary = descriptions.get(str(entry["topic"]), f"基于 {int(entry['count'])} 项最新资料整理的中文技术简报。")
        cards.append(
            f'<article class="{card_class}"><a href="{html.escape(str(entry["url"]), quote=True)}">'
            f'<p class="card-topic">{html.escape(topic_name)}</p><h2>{html.escape(str(entry["title"]))}</h2>'
            f'<p class="card-summary">{html.escape(summary)}</p>'
            f'<p class="card-meta"><time>{html.escape(date)}</time><span>阅读全文 →</span></p></a></article>'
        )
    topics = "".join(
        f'<article><p>{html.escape(schedule)}</p><h3>{html.escape(name)}</h3><span>持续追踪、筛选与深度分析</span></article>'
        for name, schedule in EDITORIAL_SLOTS
    )
    body = (
        '<section class="hero"><div><p class="eyebrow">VORASIO · RESEARCH DIGEST</p>'
        '<h1>追踪 AI 模型，<br>直到智能硬件落地。</h1></div>'
        '<p class="hero-intro">覆盖模型训练、高效化、推理系统、芯片、感知交互、具身智能与产品可靠性的完整技术链。</p></section>'
        f'<section id="topics" class="topic-section"><div class="section-heading"><p>研究版图</p>'
        f'<h2>每天十个自动编辑时段</h2></div><div class="topic-grid">{topics}</div></section>'
        '<section id="latest" class="latest-section"><div class="section-heading"><p>最新发布</p>'
        '<h2>研究简报</h2></div><div class="post-grid">'
        + "".join(cards)
        + "</div></section>"
    )
    (SITE_DIR / "index.html").write_text(shell("VORASIO 研究简报", "AI、Agent、音频与端侧智能的中文深度研究简报", body))
