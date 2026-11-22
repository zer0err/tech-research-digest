from __future__ import annotations

import html
import json
import re
from datetime import datetime
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring

from .schedule import ZONE

DAILY = "daily_report"


def canonical_entries(entries: list[dict[str, object]]) -> list[dict[str, object]]:
    chosen = [
        entry for entry in entries
        if entry.get("topic") == DAILY and entry.get("status") == "published" and int(entry.get("count") or 0) > 0
    ]
    return sorted(chosen, key=lambda entry: str(entry.get("date") or ""), reverse=True)


_DIGEST_PATH = re.compile(r"posts/[0-9]{8}-daily\.html")
_CONCLUSIONS = re.compile(r"<h[2-6]>\s*(?:本期结论|本时段要点)\s*</h[2-6]>\s*<(?:ol|ul)>(.*?)</(?:ol|ul)>", re.DOTALL)
_ITEM_TITLE = re.compile(r"<li>\s*<strong>([^<>]+)</strong>")


def _issue_preview(entry: dict[str, object]) -> tuple[str, str, str]:
    day = str(entry["date"])[:10]
    url = html.escape(str(entry["url"]), quote=True)
    sections = entry.get("sections")
    heading = sections[0].get("title") if isinstance(sections, list) and sections and isinstance(sections[0], dict) else None
    label = str(heading or entry["title"]).removesuffix(f"（{day}）")
    return day, url, html.escape(label)


def _takeaways(url: str) -> list[str]:
    # Use short headings already published in the issue, never invented by the homepage.
    if not _DIGEST_PATH.fullmatch(url):
        return []
    try:
        source = Path("docs", url).read_text(encoding="utf-8")
    except OSError:
        return []
    titles = [html.escape(html.unescape(title)) for block in _CONCLUSIONS.findall(source) for title in _ITEM_TITLE.findall(block)]
    return list(dict.fromkeys(titles))[:3]


def _recent_headline(entry: dict[str, object], takeaways: list[str]) -> str:
    summary = re.sub(r"^(本期结论|本时段要点)\s*", "", str(entry.get("summary") or ""))
    # Only use a complete sentence; the publication index may cut off its final sentence.
    first_sentence = re.match(r"([^。！？]{6,88})[。！？]", summary)
    if first_sentence:
        return html.escape(first_sentence.group(1).strip())
    return takeaways[0] if takeaways else html.escape(str(entry["title"]))


def _lead_and_recent(reports: list[dict[str, object]], today: str) -> str:
    if not reports:
        return '<section class="digest-lead"><h1>VORASIO AI 日报</h1><p>暂无已发布日报。</p></section>'
    day, url, headline = _issue_preview(reports[0])
    takeaways = _takeaways(str(reports[0]["url"]))
    details = (
        '<ul class="digest-takeaways">' + "".join(f"<li>{point}</li>" for point in takeaways) + "</ul>"
        if takeaways else f'<p>{html.escape(str(reports[0].get("summary") or "查看当日来源与分析。"))}</p>'
    )
    status_link = '<p class="digest-status">今日尚无已发布日报 · <a href="#latest">查看发布状态</a></p>' if day < today else ""
    lead = (
        '<section class="digest-lead" aria-labelledby="digest-lead-title">'
        f'<p class="digest-label">最新一期 <span aria-hidden="true">/</span> <time datetime="{day}">{day}</time></p>'
        f'<h1 id="digest-lead-title">{headline}</h1>'
        f'<a class="digest-read" href="{url}">阅读本期</a>{status_link}{details}</section>'
    )
    if len(reports) == 1:
        return lead
    recent = []
    for entry in reports[1:5]:
        day, url, _ = _issue_preview(entry)
        points = _takeaways(str(entry["url"]))
        headline = _recent_headline(entry, points)
        recent.append(
            f'<article><time datetime="{day}">{day}</time><h3><a href="{url}">{headline}</a></h3></article>'
        )
    return (
        lead + '<section class="digest-recent" aria-labelledby="digest-recent-title">'
        '<h2 id="digest-recent-title">近期日报</h2>'
        '<div class="digest-recent-grid">' + "".join(recent) + '</div></section>'
    )


def render_timeline(entries: list[dict[str, object]]) -> None:
    from email.utils import format_datetime

    from .public_status import export
    from .site import base_url, shell

    export()
    reports = canonical_entries(entries)
    today = datetime.now(ZONE).date().isoformat()
    days = [str(entry["date"])[:10] for entry in reports]
    if today not in days:
        days = [today, *days]
    sections = []
    for day in days:
        entry = next((item for item in reports if str(item["date"])[:10] == day), None)
        if entry:
            published_at = datetime.fromisoformat(str(entry["date"])).astimezone(ZONE)
            row = (
                f'<li class="timeline-row published" data-date="{day}" data-slot="daily_report" '
                f'data-published-at="{published_at.isoformat()}">'
                f'<div class="time-rail"><time datetime="{published_at.isoformat()}">09:00</time><span class="node"></span></div>'
                '<article class="timeline-card"><div class="card-top"><span>日报</span><span class="status">已发布</span></div>'
                f'<h2>{html.escape(str(entry["title"]))}</h2>'
                f'<p>{html.escape(str(entry.get("summary") or "查看当日来源与原文。"))}</p>'
                f'<p class="publication-time">发布时间：{published_at:%Y-%m-%d} 09:00 · Asia/Taipei（UTC+8）</p>'
                f'<a class="read-link" href="{html.escape(str(entry["url"]), quote=True)}">阅读全文 <span>↗</span></a>'
                '</article></li>'
            )
            heading = f'<div class="day-heading"><h2>{day}</h2><span>已发布 · Asia/Taipei 09:00</span></div>'
        else:
            row = (
                f'<li class="timeline-row pending" data-date="{day}" data-slot="daily_report" data-published-at="">'
                f'<div class="time-rail"><time datetime="{day}T09:00:00+08:00">09:00</time><span class="node"></span></div>'
                '<article class="timeline-card"><div class="card-top"><span>日报</span><span class="status">尚未发布</span></div>'
                '<h2>VORASIO AI 日报</h2>'
                '<p>今日日报在 09:00（Asia/Taipei）之后发布。没有合格来源时不编造一期。</p>'
                '</article></li>'
            )
            heading = f'<div class="day-heading"><h2>{day}</h2><span>计划 09:00 · Asia/Taipei</span></div>'
        sections.append(
            f'<section class="day-section" data-date="{day}" {"" if day == today else "hidden"}>'
            f'{heading}<ol class="timeline">{row}</ol></section>'
        )
    options = "".join(f'<option value="{day}">{day}{" · 今天" if day == today else ""}</option>' for day in days)
    body = (
        _lead_and_recent(reports, today)
        + '<section id="latest"><div class="timeline-toolbar"><div><p class="eyebrow">按日期查看</p>'
        '<h2 id="timeline-heading">日报归档</h2></div>'
        f'<label>浏览日期 <select id="date-picker">{options}</select></label></div>'
        '<label class="timeline-search">搜索所选日期 <input id="timeline-search" type="search" placeholder="标题或摘要关键词"></label>'
        '<p class="schedule-note" id="timezone-note">每期发布时刻固定为 Asia/Taipei（UTC+8）当天 09:00。'
        '页面不按阅读设备时区改写这一日期。</p>'
        + "".join(sections)
        + '</section>'
        '<script type="module" src="assets/timeline.js?v=daily-1"></script>'
    )
    Path("docs").mkdir(exist_ok=True)
    Path("docs/index.html").write_text(shell(
        "VORASIO · 每日日报", "AI 研究、开发工具与智能硬件日报", body,
        extra_head='\n<link rel="stylesheet" href="assets/digest-home.css">',
        digest_home=True,
    ))
    about = (
        '<article class="about-page article-body"><h1>关于 VORASIO</h1>'
        '<p>本站整理 AI 研究、开发工具和智能硬件相关资料。每个 Asia/Taipei 日期发布一篇日报，时刻为当天 09:00（UTC+8）。</p>'
        '<h2>内容说明</h2><p>内容由自动化系统与 AI 辅助整理，原始资料链接见各篇日报。'
        '分析可能存在错误，关键结论请回查来源。</p>'
        '<p>没有合格的新来源时，不为那天编造一期。旧的分栏地址会转到对应日期的日报。'
        '开发实践未经实际运行时会明确标注。免费资源线索未经官方页面核验。</p>'
        '<p><a href="index.html">返回日报</a> · <a href="feed.xml">订阅 RSS</a></p></article>'
    )
    Path("docs/about.html").write_text(shell("关于 VORASIO", "站点与内容说明", about))
    Path("docs/posts.json").write_text(json.dumps(reports, ensure_ascii=False, indent=2) + "\n")
    origin = base_url()
    rss = Element("rss", {"version": "2.0"})
    channel = SubElement(rss, "channel")
    for tag, text in (("title", "VORASIO AI 日报"), ("link", origin), ("description", "每个 Asia/Taipei 日期一篇 AI 日报")):
        SubElement(channel, tag).text = text
    for entry in reports[:100]:
        published_at = datetime.fromisoformat(str(entry["date"]))
        item = SubElement(channel, "item")
        for tag, text in (
            ("title", str(entry["title"])), ("link", origin + "/" + str(entry["url"])),
            ("guid", origin + "/" + str(entry["url"])), ("description", str(entry.get("summary", ""))),
            ("pubDate", format_datetime(published_at)),
        ):
            SubElement(item, tag).text = text
    Path("docs/feed.xml").write_bytes(tostring(rss, encoding="utf-8", xml_declaration=True))
    urlset = Element("urlset", {"xmlns": "http://www.sitemaps.org/schemas/sitemap/0.9"})
    for path in ("", "about.html", "subscribe.html", "courses/index.html", "tools/index.html",
                 "knowledge/index.html", "domains/index.html"):
        node = SubElement(urlset, "url")
        SubElement(node, "loc").text = origin + ("/" + path if path else "")
    for entry in reports:
        node = SubElement(urlset, "url")
        SubElement(node, "loc").text = origin + "/" + str(entry["url"])
        SubElement(node, "lastmod").text = str(entry["date"])
    Path("docs/sitemap.xml").write_bytes(tostring(urlset, encoding="utf-8", xml_declaration=True))
