from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring
from zoneinfo import ZoneInfo

from markdown_it import MarkdownIt

from .charter import charter_text
from .magazine import excerpt, opening, selections

SLOTS = [
    ("morning_radar", "09:07", "晨间雷达与免费资源", "快讯"),
    ("model_research", "10:17", "模型、训练与基础研究", "研究"),
    ("open_source", "11:27", "开源项目与工具更新", "开发"),
    ("paper_brief", "12:37", "论文午间速览", "研究"),
    ("prompt_engineering", "13:47", "Prompt、上下文与评测", "开发"),
    ("core_research", "14:07", "智能硬件技术专题", "研究"),
    ("dev_practice", "15:17", "开发实践与部署", "开发"),
    ("applied_ai", "16:27", "AI 应用与落地专题", "研究"),
    ("ecosystem", "17:37", "人物、机构与产业生态", "生态"),
    ("daily_digest", "18:47", "VORASIO AI 日报", "快讯"),
]


def render_timeline(entries: list[dict[str, object]]) -> None:
    from .site import base_url, shell

    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    today = now.date().isoformat()
    days = sorted({today, *(str(e["date"])[:10] for e in entries)}, reverse=True)
    sections = []
    for day in days:
        day_entries = [e for e in entries if str(e["date"])[:10] == day]
        rows = []
        for key, time, label, category in SLOTS:
            entry = next((e for e in day_entries if e["topic"] == key), None)
            status = str(entry.get("status", "published")) if entry else "pending"
            title = html.escape(str(entry["title"])) if entry else label
            summary = html.escape(excerpt(entry)) if entry else "按计划更新，实际发布可能延迟。"
            badge = {
                "published": "已发布", "empty": "暂无新内容", "fallback": "来源摘要",
                "pending": "等待更新", "source_error": "来源访问异常",
            }[status]
            link = f'<a class="read-link" href="{html.escape(str(entry["url"]), quote=True)}">阅读全文 <span>↗</span></a>' if entry else ""
            rows.append(
                f'<li class="timeline-row {status}" data-category="{category}" data-time="{time}">'
                f'<div class="time-rail"><time>{time}</time><span class="node"></span></div>'
                f'<article class="timeline-card"><div class="card-top"><span>{category}</span><span class="status">{badge}</span></div>'
                f'<h2>{title}</h2><p>{summary}</p>{link}</article></li>'
            )
        completed = sum(e.get("topic") in {s[0] for s in SLOTS} for e in day_entries)
        sections.append(
            f'<section class="day-section" data-date="{day}" {"" if day == today else "hidden"}>'
            f'<div class="day-heading"><h2>{day}</h2><span>已处理 {completed} / 10 个时段 · 北京时间</span></div>'
            f'<div class="progress-track"><span style="width:{min(completed, 10) * 10}%"></span></div>'
            f'<ol class="timeline">{"".join(rows)}</ol></section>'
        )
    options = "".join(f'<option value="{day}">{day}{" · 今天" if day == today else ""}</option>' for day in days)
    lead = '<div id="briefing">' + "".join(
        selections(entries, day).replace(' hidden>', '>') if day == today else selections(entries, day) for day in days
    ) + '</div>'
    body = (
        opening(entries, now, {slot[0] for slot in SLOTS}) + lead +
        '<section id="latest"><div class="timeline-toolbar"><div><p class="eyebrow">每日出版</p><h2>今日技术时间线</h2></div>'
        f'<label>浏览日期 <select id="date-picker">{options}</select></label></div>'
        '<label class="timeline-search">搜索当前日期 <input id="timeline-search" type="search" placeholder="标题或摘要关键词"></label>'
        '<div class="filters" role="group" aria-label="筛选内容">'
        + "".join(
            f'<button type="button" data-filter="{v}" aria-pressed="{str(v == "全部").lower()}">{v}</button>'
            for v in ("全部", "研究", "开发", "快讯", "生态")
        )
        + '</div><p class="schedule-note">时间为计划出版时间。到时尚无内容表示等待更新，不能据此判断任务失败。</p>'
        + "".join(sections)
        + '</section><section id="topics" class="principle-strip"><p class="eyebrow">我们的约定</p>'
        '<h2>求真 · 独立 · 实用 · 克制 · 尊重 · 可纠正</h2>'
        '<p>从模型研究到产品落地，让技术信息成为可以回查、能够行动的知识。</p>'
        '<div class="principle-links"><a href="about.html">阅读使命与编辑章程 ↗</a>'
        '<a href="feed.xml">订阅 RSS ↗</a></div></section>'
        '<script src="assets/timeline.js?v=magazine-1" defer></script>'
    )
    Path("docs").mkdir(exist_ok=True)
    page = shell("VORASIO · AI 技术时间线", "每日 AI 研究、开发实践与智能硬件技术时间线", body, page_class="magazine")
    Path("docs/index.html").write_text(page)
    md = MarkdownIt("commonmark", {"html": False}).enable("table")
    about = '<article class="about-page article-body">' + md.render(charter_text()) + '</article>'
    Path("docs/about.html").write_text(shell("VORASIO · 使命与编辑章程", "品牌使命与自动编辑原则", about))
    Path("docs/posts.json").write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n")
    rss = Element("rss", {"version": "2.0"})
    channel = SubElement(rss, "channel")
    for tag, text in (("title", "VORASIO 技术简报"), ("link", base_url()), ("description", "以求证理解智能，以实践创造价值。")):
        SubElement(channel, tag).text = text
    for entry in entries[:100]:
        item = SubElement(channel, "item")
        for tag, text in (
            ("title", str(entry["title"])), ("link", base_url() + "/" + str(entry["url"])),
            ("guid", base_url() + "/" + str(entry["url"])), ("description", str(entry.get("summary", ""))),
        ):
            SubElement(item, tag).text = text
    Path("docs/feed.xml").write_bytes(tostring(rss, encoding="utf-8", xml_declaration=True))
