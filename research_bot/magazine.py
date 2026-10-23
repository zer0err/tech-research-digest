"""Magazine layout, with all publishing claims derived from stored entries."""
from __future__ import annotations

import html
from datetime import datetime


def excerpt(entry: dict[str, object]) -> str:
    count = int(entry.get("count", 0))
    status = entry.get("status", "published")
    if status == "fallback":
        return f"收录 {count} 项原始资料。当前提供来源摘要与原始链接，自动分析未通过发布校验。"
    if status == "source_error":
        return "本时段来源暂时不可用，尚无法判断是否存在新资料；后续按计划重试。"
    if status == "empty":
        return "本时段未发现符合日期、相关性与去重条件的新资料。"
    if entry.get("topic") == "daily_digest":
        return f"汇总今日 {count} 个时段的出版记录；包含暂无新内容与来源访问异常的状态说明。"
    return str(entry.get("summary", "查看本期简报与原始来源。"))[:160]


def opening(entries: list[dict[str, object]], now: datetime, valid_topics: set[str] | None = None) -> str:
    day = now.date().isoformat()
    todays = [
        entry for entry in entries
        if str(entry["date"])[:10] == day and (valid_topics is None or entry.get("topic") in valid_topics)
    ]
    completed = len({entry["topic"] for entry in todays})
    content = sum(int(entry.get("count", 0)) > 0 for entry in todays)
    failures = sum(entry.get("status") == "source_error" for entry in todays)
    weekday = "一二三四五六日"[now.weekday()]
    return (
        '<section class="magazine-hero"><div class="edition">'
        f'<span>NO. {now.year}—{now:%j}</span><span>北京 · {now:%Y.%m.%d} · 星期{weekday}</span></div>'
        '<div class="hero-grid"><div class="hero-copy"><p class="eyebrow">AI 技术情报与智能硬件研究</p>'
        '<h1>以求证<br>理解智能，<br><i>以实践</i><br>创造价值。</h1>'
        '<p class="slogan-en" lang="en">Understand AI through evidence.<br>Create value through practice.</p></div>'
        '<div class="hero-side"><p class="deck">从模型研究、开发工具到智能硬件，建立一份可回查、可行动的中文技术记录。</p>'
        '<div class="signal-card"><div class="radar" aria-hidden="true"><span></span><span></span><b></b></div>'
        f'<div><strong>{completed} / 10</strong><small>今日时段已处理</small></div></div>'
        f'<p class="publication-note">{content} 期内容 · {failures} 个来源异常时段</p>'
        '<p class="hero-note"><span class="live-dot"></span>每周七天 · 每日十个编辑时段 · 有据可查</p></div></div>'
        '<div class="ticker"><span>持续关注</span><div>开源工具更新</div><div>上下文工程</div><div>智能硬件</div><div>产业生态</div></div>'
        '</section>'
    )


def selections(entries: list[dict[str, object]], day: str) -> str:
    candidates = [
        entry for entry in entries
        if str(entry["date"])[:10] == day and int(entry.get("count", 0)) > 0
        and entry.get("status", "published") in {"published", "fallback"} and entry.get("topic") != "daily_digest"
    ]
    priority = {"open_source": 0, "model_research": 1, "prompt_engineering": 2, "dev_practice": 3}
    candidates.sort(key=lambda entry: (entry.get("status") == "fallback", priority.get(str(entry["topic"]), 4)))
    if not candidates:
        return (
            f'<section class="magazine-lead" data-date="{day}" hidden><div class="section-head">'
            '<p>本期选读</p><h2>等待可靠的新内容</h2></div>'
            '<p class="selection-note">暂无适合选读的内容，完整出版状态见下方时间线。</p></section>'
        )

    def story(entry: dict[str, object], featured: bool = False) -> str:
        title = html.escape(str(entry["title"]))
        url = html.escape(str(entry["url"]), quote=True)
        status = "来源摘要 · 自动分析暂缓" if entry.get("status") == "fallback" else "已发布"
        visual = (
            '<a class="story-visual" tabindex="-1" aria-hidden="true" href="' + url + '">'
            '<span class="orb orb-a"></span><span class="orb orb-b"></span><span class="grid-lines"></span>'
            '<span class="visual-word">技术<br>有据可查</span></a>' if featured else ""
        )
        return (
            f'<article class="{"lead-story" if featured else "side-story"}">{visual}<div class="story-text">'
            f'<p class="tag">{status}</p><h3><a href="{url}">{title}</a></h3>'
            f'<p class="story-excerpt">{html.escape(excerpt(entry))}</p>'
            f'<a class="story-link" href="{url}">阅读简报 <span aria-hidden="true">↗</span></a></div></article>'
        )

    return (
        f'<section class="magazine-lead" id="briefing-{day}" data-date="{day}" hidden>'
        f'<div class="section-head"><p>本期选读</p><h2>从证据出发</h2><span>{day}</span></div>'
        '<p class="selection-note">根据发布状态与栏目优先级自动编排；来源异常与空档不会进入选读。</p>'
        f'<div class="lead-grid">{story(candidates[0], True)}<div class="side-stories">'
        + "".join(story(entry) for entry in candidates[1:3])
        + '<blockquote>真正有价值的技术情报，是更清楚地说明：什么改变了，证据在哪里，接下来能做什么。'
        '<cite>VORASIO 编辑约定</cite></blockquote></div></div></section>'
    )
