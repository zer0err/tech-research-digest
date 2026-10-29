from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring
from zoneinfo import ZoneInfo

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
            }[status]
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
        '<p class="hero-note">AI 技术简报 · 研究、开发与智能硬件</p></section>'
        '<section class="section-gateways" aria-label="专题入口">'
        '<article><p class="eyebrow">系统学习</p><h2>AI 学习路线</h2>'
        '<p>从第一行 Python 代码开始，完成一套可验证的 AI 应用。</p>'
        '<a class="read-link" href="courses/index.html">进入课程 →</a></article>'
        '<article><p class="eyebrow">生态导航</p><h2>AI 工具目录</h2>'
        '<p>查看已核验官方来源、费用边界与使用方式的工具。</p>'
        '<a class="read-link" href="tools/index.html">浏览工具 →</a></article></section>'
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
        '<p>“来源摘要”表示自动分析未通过发布校验；“来源访问异常”表示本次未能成功获取资料。'
        '开发实践未经实际运行时会明确标注。免费资源的条件以服务方当前说明为准。</p>'
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
