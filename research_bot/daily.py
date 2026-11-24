"""Shared daily report rendering, identity rules, and archive migration helpers."""
from __future__ import annotations

import html
import json
import os
import re
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from .core import arxiv_base, canonical_url, normalize_doi
from .provenance import render

ZONE = ZoneInfo("Asia/Taipei")
TOPIC = "daily_report"
ORIGIN = "https://vorasio.com"
EDITION_TIME = "09:00"
REDIRECT_MARKER = 'data-legacy-redirect="daily"'
HISTORICAL_ORDER = (
    "morning_radar", "model_research", "open_source", "paper_brief", "prompt_engineering",
    "core_research", "dev_practice", "applied_ai", "ecosystem", "efficient_ai",
    "inference_systems", "ai_hardware", "multimodal", "embodied", "product_safety",
    "ai_papers", "audio", "daily_digest",
)
EMPTY_MARKERS = (
    "截至本次汇总，今日没有成功发布的新内容",
    "今日没有成功发布",
    "暂无资料",
    "来源暂时不可用",
    "本时段状态",
)
MIGRATION_ANALYSIS = {"provider": "历史简报整合（未重新调用 AI）", "model": "不适用"}
RULES = (
    "按 execution_date，否则按存储时间的 Asia/Taipei 日历日归并；文件名日期不同时记入映射，不另开一天。",
    "发布时间一律写成该日 09:00+08:00。没有条目的日期不生成日报。",
    "日报索引页只保留正文与站外来源。同一规范 URL、DOI 或 arXiv 编号只出现一次。",
    "标题相同但链接不同的条目都保留。正文不同的栏目都保留，即使部分来源重复。",
    "仅指向当日站内旧稿的日报索引不重复贴出；若索引里有未出现过的站外链接，则保留那些链接原文。",
    "不调用模型，不补写当时没有的句子。迁移不发送 Telegram。",
)


def edition_stamp(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, 9, 0, tzinfo=ZONE)


def canonical_name(day: str) -> str:
    return f"posts/{day.replace('-', '')}-daily.html"


def identity_keys(url: str = "", doi: str = "") -> set[str]:
    keys: set[str] = set()
    doi_value = normalize_doi(doi or url)
    if doi_value and (doi or "doi.org/" in url.lower()):
        keys.add("doi:" + doi_value)
    arxiv = arxiv_base(url)
    if arxiv:
        keys.add("arxiv:" + arxiv)
    canon = canonical_url(url)
    if canon.startswith("https://"):
        keys.add("url:" + canon)
    return keys


def site_post_url(url: str) -> bool:
    parts = urlsplit(url)
    host = parts.netloc.lower()
    return host in {"vorasio.com", "www.vorasio.com"} and "/posts/" in parts.path


def visible_text(fragment: str) -> str:
    text = re.sub(r"<[^>]+>", " ", fragment)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def article_body(page: str) -> str:
    marker = '<div class="article-body">'
    start = page.find(marker)
    if start < 0:
        return ""
    start += len(marker)
    for closer in ('</div><section class="growth-card"', "</div></article>"):
        end = page.find(closer, start)
        if end >= 0:
            return page[start:end].strip()
    return ""


def external_hrefs(fragment: str) -> list[str]:
    found = []
    for url in re.findall(r'href="(https?://[^"]+)"', fragment):
        if site_post_url(url):
            continue
        if urlsplit(url).path.endswith((".css", ".js")):
            continue
        found.append(url)
    return found


def edition_day(entry: dict) -> str:
    execution = str(entry.get("execution_date") or "")[:10]
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", execution):
        return execution
    raw = str(entry.get("date") or "")
    try:
        return datetime.fromisoformat(raw).astimezone(ZONE).date().isoformat()
    except ValueError:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw[:10]):
            return raw[:10]
    match = re.search(r"(\d{4})(\d{2})(\d{2})", str(entry.get("url") or ""))
    if match:
        return "-".join(match.groups())
    raise ValueError(f"Cannot date {entry.get('url')}")


def file_day(url: str) -> str:
    match = re.search(r"(\d{4})(\d{2})(\d{2})", url)
    if not match:
        return ""
    return "-".join(match.groups())


def fragment_rank(entry: dict) -> tuple[int, str]:
    topic = str(entry.get("topic") or "")
    try:
        order = HISTORICAL_ORDER.index(topic)
    except ValueError:
        order = len(HISTORICAL_ORDER)
    return order, str(entry.get("url") or "")


def is_redirect(page: str) -> bool:
    return REDIRECT_MARKER in page


def preserve_unlisted(page: str) -> str:
    """Keep an unmerged page's text, but keep it out of search indexes."""
    if 'name="robots"' in page:
        return page
    marker = "<head>"
    if marker in page:
        return page.replace(marker, marker + '<meta name="robots" content="noindex,follow">', 1)
    return '<!doctype html><html><head><meta name="robots" content="noindex,follow"></head><body>' + page + "</body></html>"


def redirect_page(day: str, target_name: str) -> str:
    canonical = f"{ORIGIN}/{target_name}"
    relative = Path(target_name).name
    return (
        "<!doctype html>\n<html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
        f"<title>已并入 {day} 日报</title>"
        f"<link rel=\"canonical\" href=\"{html.escape(canonical, quote=True)}\">"
        "<meta name=\"robots\" content=\"noindex,follow\">"
        f"<meta http-equiv=\"refresh\" content=\"0; url={html.escape(relative, quote=True)}\">"
        f"<meta name=\"description\" content=\"此页已并入 {day} 的 VORASIO AI 日报。\">"
        f"</head><body {REDIRECT_MARKER}>"
        f"<p>此页已并入 <a href=\"{html.escape(relative, quote=True)}\">{day} 日报</a>。</p>"
        "</body></html>\n"
    )


def _source_dicts(entry: dict, body: str) -> list[dict]:
    stored = list((entry.get("provenance") or {}).get("sources") or [])
    known = {key for source in stored for key in identity_keys(str(source.get("url", "")), str(source.get("doi", "")))}
    for url in external_hrefs(body):
        keys = identity_keys(url)
        if not keys or keys & known:
            continue
        known.update(keys)
        host = urlsplit(url).hostname or ""
        stored.append({
            "title": url, "url": canonical_url(url) or url, "publisher": host, "host": host,
            "family": "博客/公开网页", "published": "未记录", "date_precision": "未记录",
            "doi": normalize_doi(url) if "doi.org/" in url else "", "kind": "未记录",
        })
    return [source for source in stored if isinstance(source, dict)]


def _digest_link_html(body: str, urls: list[str]) -> str:
    kept = [item for item in re.findall(r"<li>.*?</li>", body, flags=re.S) if any(url in item for url in urls)]
    if not kept:
        links = "".join(
            f"<li><a href=\"{html.escape(url, quote=True)}\">{html.escape(url)}</a></li>" for url in urls
        )
        return f"<ul>{links}</ul>"
    return "<ul>" + "".join(kept) + "</ul>"


def plan_day(day: str, entries: list[dict], pages: dict[str, str]) -> dict | None:
    seen_keys: set[str] = set()
    seen_text: set[str] = set()
    kept_text: list[str] = []
    sections: list[dict] = []
    sources: list[dict] = []
    decisions = []
    for entry in sorted(entries, key=fragment_rank):
        url = str(entry.get("url") or "")
        page = pages.get(url, "")
        if is_redirect(page):
            decisions.append({"url": url, "topic": entry.get("topic"), "action": "already_redirect"})
            continue
        body = article_body(page)
        text = visible_text(body)
        links = external_hrefs(body)
        digest = entry.get("topic") == "daily_digest" or ("今天共发布" in text and "今日内容" in text)
        if digest and not links:
            decisions.append({"url": url, "topic": entry.get("topic"), "action": "folded_index"})
            continue
        if digest and links:
            body = _digest_link_html(body, links)
            text = visible_text(body)
        keys = {key for source in _source_dicts(entry, body) for key in identity_keys(
            str(source.get("url", "")), str(source.get("doi", "")))}
        keys.update(key for link in links for key in identity_keys(link))
        novel = keys - seen_keys
        contained = bool(text) and any(text in earlier for earlier in kept_text)
        status_only = not links and (len(text) < 80 or any(marker in text and len(text) < 180 for marker in EMPTY_MARKERS))
        if not text or status_only:
            decisions.append({"url": url, "topic": entry.get("topic"), "action": "dropped_empty"})
            continue
        if text in seen_text or (keys and not novel and contained):
            decisions.append({"url": url, "topic": entry.get("topic"), "action": "dropped_duplicate",
                              "source_keys": sorted(keys)})
            continue
        anchor = f"edition-{len(sections) + 1}"
        label = str(entry.get("title") or entry.get("topic") or "栏目")
        kicker = str(entry.get("topic") or "")
        sections.append({
            "anchor": anchor,
            "heading": label,
            "kicker": kicker,
            "html": body,
            "topic": kicker,
            "source_topic": str(entry.get("source_topic") or kicker),
            "title": label,
        })
        for source in _source_dicts(entry, body):
            source_keys = identity_keys(str(source.get("url", "")), str(source.get("doi", "")))
            if source_keys and source_keys & seen_keys:
                continue
            if site_post_url(str(source.get("url", ""))):
                continue
            sources.append(source)
            seen_keys.update(source_keys)
        seen_keys.update(keys)
        seen_text.add(text)
        kept_text.append(text)
        decision_row = {"url": url, "topic": entry.get("topic"), "action": "merged",
                        "anchor": anchor, "source_keys": sorted(keys)}
        filename_day = file_day(url)
        if filename_day and filename_day != day:
            decision_row["filename_day"] = filename_day
        decisions.append(decision_row)
    if not sections:
        return None
    stamp = edition_stamp(date.fromisoformat(day))
    title = f"VORASIO AI 日报（{day}）"
    summary = visible_text(" ".join(section["html"] for section in sections))[:160]
    count = len(sources) or len(sections)
    record = {
        "title": title,
        "date": stamp.isoformat(),
        "count": count,
        "url": canonical_name(day),
        "topic": TOPIC,
        "status": "published",
        "summary": summary,
        "provenance": {"analysis": dict(MIGRATION_ANALYSIS), "sources": sources},
        "sections": [
            {"topic": section["topic"], "source_topic": section["source_topic"], "title": section["title"],
             "anchor": section["anchor"]}
            for section in sections
        ],
    }
    disclosure = (
        "本页由当日已发布简报原文合并而成，保留原有表述和来源链接，没有重新调用模型，也没有补写当时没有的内容。"
        "开发实践部分若出现，仍是实践参考，未经运行验证。"
    )
    return {
        "day": day,
        "published_at": stamp.isoformat(),
        "canonical": canonical_name(day),
        "fragments": decisions,
        "source_count": len(sources),
        "section_count": len(sections),
        "html": render_daily_page(title, stamp, sections, sources, MIGRATION_ANALYSIS, disclosure, canonical_name(day)),
        "entry": record,
    }


def render_daily_page(title: str, stamp: datetime, sections: list[dict], sources: list[dict],
                      analysis: dict, disclosure: str, canonical_path: str, *,
                      scheduled_at: datetime | None = None) -> str:
    from .growth import article_callout
    from .site import shell

    stamp = stamp.astimezone(ZONE)
    canonical = f"{ORIGIN}/{canonical_path}"
    payload = {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": title,
        "datePublished": stamp.isoformat(),
        "dateModified": stamp.isoformat(),
        "inLanguage": "zh-CN",
        "mainEntityOfPage": canonical,
        "publisher": {"@type": "Organization", "name": "VORASIO"},
    }
    extra = (
        f'<link rel="canonical" href="{html.escape(canonical, quote=True)}">'
        f'<meta property="article:published_time" content="{html.escape(stamp.isoformat(), quote=True)}">'
        f'<script type="application/ld+json">{json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")}</script>'
    )
    blocks = []
    for section in sections:
        section_body = section.get("reading_html", section["html"]) if scheduled_at is not None else section["html"]
        blocks.append(
            f'<section id="{html.escape(section["anchor"], quote=True)}">'
            f'<p class="kicker">{html.escape(section.get("kicker") or "栏目")}</p>'
            f'<h2>{html.escape(section["heading"])}</h2>{section_body}</section>'
        )
    provenance = render({"analysis": analysis, "sources": sources})
    clock_label = "发布时间"
    planned = ""
    if scheduled_at is not None:
        scheduled_at = scheduled_at.astimezone(ZONE)
        clock_label = "实际合成时间"
        planned = (f'<dt>计划合成时间</dt><dd><time datetime="{html.escape(scheduled_at.isoformat(), quote=True)}">'
                   f'{scheduled_at:%Y-%m-%d %H:%M} · Asia/Taipei（UTC+8）</time></dd>')
    article = (
        '<div class="article-layout"><aside class="article-meta"><p class="eyebrow">VORASIO AI 日报</p><dl>'
        f'<dt>{clock_label}</dt><dd data-published-at="{html.escape(stamp.isoformat(), quote=True)}">'
        f'{stamp:%Y-%m-%d %H:%M} · Asia/Taipei（UTC+8）</dd>'
        f'{planned}<dt>来源</dt><dd>{len(sources)} 条</dd><dt>阅读提示</dt><dd>关键结论请回查原始资料</dd></dl>'
        '<a class="back-link" href="../index.html">← 返回全部日报</a></aside>'
        '<article><p class="kicker">DAILY REPORT · VORASIO AI 日报</p>'
        f'<h1>{html.escape(title)}</h1>{provenance}<p class="disclosure">{html.escape(disclosure)}</p>'
        f'<div class="article-body">{"".join(blocks)}</div>'
        f'{article_callout("../", "/" + canonical_path)}</article></div>'
    )
    clock_verb = "合成于" if scheduled_at is not None else "发布于"
    description = f"{title}：{len(sources)} 条来源，{clock_verb} {stamp:%Y-%m-%d %H:%M}（Asia/Taipei）。"
    return shell(title, description, article, "../", extra_head=extra, article_asset_version="reading-1", section="daily")


def _reading_references(markdown: str, items: list[dict], renderer, anchor: str, *,
                        allow_missing_heading: bool = False) -> str | None:
    """Render B references in the generator's source order, never the model's order."""
    from .site import linkify_bare_urls

    refs = []
    for index, item in enumerate(items, 1):
        if not isinstance(item, dict) or not isinstance(item.get("url"), str):
            return None
        url = item["url"]
        try:
            parts = urlsplit(url)
            if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
                return None
        except ValueError:
            return None
        if any(char.isspace() for char in url):
            return None
        title = html.escape(str(item.get("title") or url))
        refs.append(f'<li id="{anchor}-source-{index}"><a href="{html.escape(url, quote=True)}">{title}</a></li>')
    if not refs:
        return None

    # Markdown token maps distinguish the final References heading from fenced
    # code or blockquote text. Unexpected structure keeps the original report.
    tokens = renderer.parse(markdown)
    headings = [
        index for index, token in enumerate(tokens[:-1])
        if token.type == "heading_open" and token.tag == "h2" and token.level == 0
        and tokens[index + 1].content.strip() == "参考资料"
    ]
    if len(headings) > 1 or (not headings and not allow_missing_heading):
        return None
    if headings and any(token.type == "heading_open" and token.level == 0 for token in tokens[headings[0] + 1:]):
        return None
    if headings:
        start = tokens[headings[0]].map[0]
        markdown = "\n".join(markdown.splitlines()[:start])
    return (renderer.render(linkify_bare_urls(markdown))
            + '<h2>参考资料</h2><ol class="article-reference-list">' + "".join(refs) + "</ol>")


def markdown_sections(parts: list[dict]) -> list[dict]:
    from markdown_it import MarkdownIt

    from .site import linkify_bare_urls

    renderer = MarkdownIt("commonmark", {"html": False}).enable("table")
    sections = []
    for index, part in enumerate(parts, 1):
        markdown = str(part["report"])
        body = renderer.render(linkify_bare_urls(markdown))
        anchor = f"edition-{index}"
        reading_html = _reading_references(
            markdown, part.get("items") or [], renderer, anchor, allow_missing_heading=part["topic"] == "other",
        )
        sections.append({
            "anchor": anchor,
            **({"reading_html": reading_html} if reading_html is not None else {}),
            "heading": str(part["title"]),
            "kicker": str(part["topic"]),
            "html": body,
            "topic": str(part["topic"]),
            "source_topic": str(part["topic"]),
            "title": str(part["title"]),
        })
    return sections


def _grouped(entries: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        groups.setdefault(edition_day(entry), []).append(entry)
    return groups


def site_is_migrated(site_dir: Path, entries: list[dict]) -> bool:
    if not entries or any(entry.get("topic") != TOPIC for entry in entries):
        return False
    for entry in entries:
        path = site_dir / str(entry.get("url") or "")
        if not path.is_file() or is_redirect(path.read_text(encoding="utf-8")):
            return False
    return True


def build_mapping(days: list[dict], fragments_before: int) -> dict:
    published = [day for day in days if day]
    return {
        "version": 1,
        "timezone": "Asia/Taipei",
        "published_at_local": EDITION_TIME,
        "offset": "+08:00",
        "rules": list(RULES),
        "counts": {
            "fragments_before": fragments_before,
            "dates_with_fragments": len(days),
            "reports_after": len(published),
            "empty_dates_skipped": len(days) - len(published),
            "redirects": sum(1 for day in published for fragment in day["fragments"]
                             if fragment["action"] != "already_redirect"),
            "merged_sections": sum(day["section_count"] for day in published),
            "folded_indexes": sum(1 for day in published for fragment in day["fragments"]
                                  if fragment["action"] == "folded_index"),
            "dropped_empty": sum(1 for day in published for fragment in day["fragments"]
                                 if fragment["action"] == "dropped_empty"),
            "dropped_duplicate": sum(1 for day in published for fragment in day["fragments"]
                                     if fragment["action"] == "dropped_duplicate"),
            "unique_sources": sum(day["source_count"] for day in published),
        },
        "days": [
            {"date": day["day"], "canonical": day["canonical"], "published_at": day["published_at"],
             "source_count": day["source_count"], "section_count": day["section_count"],
             "fragments": day["fragments"]}
            for day in published
        ],
    }


def suppress_notifications(state: dict, days: list[str]) -> dict:
    """Record migrated dates so a later finalize cannot treat them as unsent. Never sends."""
    receipts = state.setdefault("daily_notifications", {})
    for day in days:
        canonical = f"{ORIGIN}/{canonical_name(day)}"
        current = receipts.get(day)
        if isinstance(current, dict) and current.get("sent_at"):
            current["canonical_url"] = canonical
            current["migrated"] = True
        else:
            receipts[day] = {"migrated": True, "url": canonical, "sent_at": None, "telegram": "not_sent"}
    state["daily_notifications"] = dict(sorted(receipts.items(), reverse=True)[:400])
    return state


def mark_editions_published(days: list[str]) -> None:
    from . import schedule

    for day in days:
        schedule.record(TOPIC, edition_stamp(date.fromisoformat(day)), "published")


def migrate(site_dir: Path = Path("docs"), state_path: Path = Path("state/seen.json"),
            mapping_path: Path = Path("state/daily-migration.json")) -> dict:
    index_path = site_dir / "posts.json"
    entries = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else []
    if not isinstance(entries, list):
        raise ValueError("posts.json must contain a list")
    if site_is_migrated(site_dir, entries):
        if mapping_path.exists():
            return json.loads(mapping_path.read_text(encoding="utf-8"))
        mapping = {
            "version": 1, "timezone": "Asia/Taipei", "published_at_local": EDITION_TIME, "offset": "+08:00",
            "rules": list(RULES), "counts": {"reports_after": len(entries), "already_migrated": True},
            "days": [{"date": str(entry["date"])[:10], "canonical": entry["url"], "published_at": entry["date"]}
                     for entry in entries],
        }
        mapping_path.parent.mkdir(parents=True, exist_ok=True)
        mapping_path.write_text(json.dumps(mapping, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return mapping
    pages = {}
    for entry in entries:
        url = str(entry.get("url") or "")
        path = site_dir / url
        pages[url] = path.read_text(encoding="utf-8") if path.is_file() else ""
    groups = _grouped(entries)
    plans = []
    for day in sorted(groups):
        plan = plan_day(day, groups[day], pages)
        if plan is not None:
            plans.append(plan)
        else:
            plans.append({
                "day": day,
                "fragments": [
                    {"url": item.get("url"), "topic": item.get("topic"), "action": "date_without_report"}
                    for item in groups[day]
                ],
                "section_count": 0, "source_count": 0, "canonical": "", "published_at": "", "html": "", "entry": None,
            })
    published = [plan for plan in plans if plan.get("entry")]
    mapping = build_mapping(published, len(entries))
    skipped = [plan["day"] for plan in plans if not plan.get("entry")]
    mapping["counts"]["dates_with_fragments"] = len(groups)
    mapping["counts"]["empty_dates_skipped"] = len(skipped)
    mapping["skipped_dates"] = skipped
    posts = site_dir / "posts"
    posts.mkdir(parents=True, exist_ok=True)
    for plan in plans:
        if plan.get("entry"):
            continue
        for fragment in plan["fragments"]:
            target = site_dir / str(fragment["url"])
            original = pages.get(str(fragment["url"]), "")
            if target.is_file() and original and not is_redirect(original):
                target.write_text(preserve_unlisted(original), encoding="utf-8")
    for plan in published:
        (site_dir / plan["canonical"]).write_text(plan["html"], encoding="utf-8")
        for fragment in plan["fragments"]:
            if fragment["action"] == "already_redirect":
                continue
            target = site_dir / str(fragment["url"])
            if target.resolve() == (site_dir / plan["canonical"]).resolve():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(redirect_page(plan["day"], plan["canonical"]), encoding="utf-8")
    from .site import render_index

    render_index([plan["entry"] for plan in published])
    # render_index writes docs/ relative to the process, so tests pass an explicit site via chdir.
    if state_path.exists() or published:
        state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {"version": 1, "topics": {}}
        suppress_notifications(state, [plan["day"] for plan in published])
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        mark_editions_published([plan["day"] for plan in published])
    mapping_path.parent.mkdir(parents=True, exist_ok=True)
    mapping_path.write_text(json.dumps(mapping, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return mapping


def public_origin() -> str:
    explicit = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
    return explicit or ORIGIN
