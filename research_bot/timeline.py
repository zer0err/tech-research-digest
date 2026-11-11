from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring
from zoneinfo import ZoneInfo

from .schedule import EDITORIAL

SLOTS = [
    (name, str(slot["time"]), str(slot["label"]), str(slot["category"]))
    for name, slot in EDITORIAL["slots"].items()
]


def render_timeline(entries: list[dict[str, object]]) -> None:
    from .featured import render_featured
    from .public_status import export
    from .site import base_url, shell

    receipts = export()
    today = datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()
    days = sorted({today, *(str(e.get("execution_date", e["date"]))[:10] for e in entries), *(key[:10] for key in receipts)}, reverse=True)
    sections = []
    for day in days:
        day_entries = [e for e in entries if str(e.get("execution_date", e["date"]))[:10] == day]
        rows = []
        for key, time, label, category in SLOTS:
            entry = next((e for e in day_entries if e["topic"] == key), None)
            status = str(entry.get("status", "published")) if entry else "pending"
            title = html.escape(str(entry["title"])) if entry else label
            summary = html.escape(str(entry.get("summary", "查看完整简报及原始来源。"))) if entry else "按计划更新，实际发布可能延迟。"
            badge = {
                "published": "已发布", "empty": "暂无新内容", "fallback": "来源摘要",
                "pending": "等待更新", "source_error": "来源访问异常",
            }.get(status, "已发布")
            link = f'<a class="read-link" href="{html.escape(str(entry["url"]), quote=True)}">阅读全文 <span>↗</span></a>' if entry else ""
            actual = ""
            published_iso = ""
            if entry:
                published_at = datetime.fromisoformat(str(entry["date"])).astimezone(ZoneInfo("Asia/Shanghai"))
                published_iso = published_at.isoformat()
                actual = f'<p class="publication-time">实际发布：{published_at:%Y-%m-%d %H:%M} · UTC+8</p>'
            rows.append(
                f'<li class="timeline-row {status}" data-category="{category}" data-time="{time}" '
                f'data-slot="{key}" data-label="{html.escape(label, quote=True)}" '
                f'data-replayed="{str(bool(entry and entry.get("execution_date"))).lower()}" '
                f'data-execution-date="{day}" data-execution-time="{time}" '
                f'data-planned-at="{day}T{time}:00+08:00" data-published-at="{published_iso}">'
                f'<div class="time-rail"><time datetime="{day}T{time}:00+08:00">{time}</time><span class="node"></span></div>'
                f'<article class="timeline-card"><div class="card-top"><span>{category}</span><span class="status">{badge}</span></div>'
                f'<h2>{title}</h2><p>{summary}</p>{actual}{link}</article></li>'
            )
        completed = sum(e.get("topic") in {s[0] for s in SLOTS} for e in day_entries)
        sections.append(
            f'<section class="day-section" data-date="{day}" {"" if day == today else "hidden"}>'
            f'<div class="day-heading"><h2>{day}</h2><span>已更新 {completed} / 10 个时段 · 北京时间</span></div>'
            f'<div class="progress-track"><span style="width:{min(completed, 10) * 10}%"></span></div>'
            f'<ol class="timeline">{"".join(rows)}</ol></section>'
        )
    options = "".join(f'<option value="{day}">{day}{" · 今天" if day == today else ""}</option>' for day in days)
    body = (
        '<section class="editorial-hero"><h1>VORASIO</h1>'
        '<p class="hero-note">为 AI 软件与智能硬件开发者挑选值得读的进展。</p>'
        '<p>查看模型、工具和应用的新进展。想用于自己的项目时，先核对来源和适用条件。</p>'
        '<div class="growth-actions"><a class="growth-primary" href="subscribe.html">订阅 AI 精选</a>'
        '<a href="domains/index.html">按领域阅读</a><a href="services.html">聊聊你的项目</a></div></section>'
        + render_featured(entries)
        + '<section class="section-gateways" aria-label="专题入口">'
        '<article><p class="eyebrow">系统学习</p><h2>AI 学习路线</h2>'
        '<p>从第一行 Python 代码开始，完成一套可验证的 AI 应用。</p>'
        '<a class="read-link" href="courses/index.html">进入课程 →</a></article>'
        '<article><p class="eyebrow">生态导航</p><h2>AI 工具目录</h2>'
        '<p>查找 AI 工具，了解官方说明、使用方式和费用条件。</p>'
        '<a class="read-link" href="tools/index.html">浏览工具 →</a></article>'
        '<article><p class="eyebrow">概念入门</p><h2>AI 知识科普</h2>'
        '<p>从常见场景入手，了解模型、智能体和工具怎样配合。</p>'
        '<a class="read-link" href="knowledge/index.html">阅读科普 →</a></article></section>'
        '<section id="latest"><div class="timeline-toolbar"><div><p class="eyebrow">每日出版</p>'
        '<h2 id="timeline-heading">今日技术时间线</h2></div>'
        f'<label>浏览日期 <select id="date-picker">{options}</select></label></div>'
        '<label class="timeline-search">搜索当前日期 <input id="timeline-search" type="search" placeholder="标题或摘要关键词"></label>'
        '<div class="filters" role="group" aria-label="筛选内容">'
        + "".join(
            f'<button type="button" data-filter="{v}" aria-pressed="{str(v == "全部").lower()}">{v}</button>'
            for v in ("全部", "研究", "开发", "快讯", "生态")
        )
        + '</div><p class="schedule-note" id="timezone-note">任务固定按北京时间（UTC+8）执行；'
        '启用 JavaScript 后，日期及时间按浏览器时区显示。</p>'
        + "".join(sections)
        + '</section><p class="archive-links"><a href="feed.xml">订阅 RSS</a> · <a href="about.html">关于本站</a></p>'
        '<script type="module" src="assets/timeline.js?v=replay-6"></script>'
    )
    Path("docs").mkdir(exist_ok=True)
    Path("docs/index.html").write_text(shell("VORASIO · AI 技术时间线", "每日 AI 研究、开发实践与智能硬件技术时间线", body))
    about = (
        '<article class="about-page article-body"><h1>关于 VORASIO</h1>'
        '<p>本站整理 AI 研究、开发工具和智能硬件相关资料，按时间线发布。</p>'
        '<h2>内容说明</h2><p>内容由自动化系统与 AI 辅助整理，原始资料链接见各篇简报。'
        '分析可能存在错误，关键结论请回查来源。</p>'
        '<p>新文章只标已发布或暂无新内容。较早页面上的“来源摘要”“来源访问异常”是旧状态，'
        '不代表当天又发布了一篇兜底稿。开发实践未经实际运行时会明确标注。'
        '免费资源线索未经官方页面核验。</p>'
        '<p><a href="index.html">返回时间线</a> · <a href="feed.xml">订阅 RSS</a></p></article>'
    )
    Path("docs/about.html").write_text(shell("关于 VORASIO", "站点与内容说明", about))
    Path("docs/posts.json").write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n")
    rss = Element("rss", {"version": "2.0"})
    channel = SubElement(rss, "channel")
    for tag, text in (("title", "VORASIO 技术简报"), ("link", base_url()), ("description", "AI 研究、开发与智能硬件相关简报")):
        SubElement(channel, tag).text = text
    for entry in entries[:100]:
        item = SubElement(channel, "item")
        for tag, text in (
            ("title", str(entry["title"])), ("link", base_url() + "/" + str(entry["url"])),
            ("guid", base_url() + "/" + str(entry["url"])), ("description", str(entry.get("summary", ""))),
        ):
            SubElement(item, tag).text = text
    Path("docs/feed.xml").write_bytes(tostring(rss, encoding="utf-8", xml_declaration=True))
