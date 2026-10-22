from __future__ import annotations

import html
import json
import os
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from markdown_it import MarkdownIt

if TYPE_CHECKING:
    from .core import Item

SITE_DIR = Path("docs")
POSTS_DIR = SITE_DIR / "posts"
INDEX_DATA = SITE_DIR / "posts.json"


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
<link rel="stylesheet" href="{relative_root}assets/style.css"></head>
<body><header><a href="{relative_root}index.html">自动化技术研究</a></header><main>{body}</main>
<footer>由 GitHub Actions 定时采集，Groq 辅助分析。重要结论请核对原论文。</footer></body></html>"""


def publish_post(topic: str, title: str, now: datetime, report: str, items: list[Item]) -> str:
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    (SITE_DIR / "assets").mkdir(parents=True, exist_ok=True)
    slug = f"{now:%Y%m%d}-{topic}.html"
    url = f"{base_url()}/posts/{slug}"
    md = MarkdownIt("commonmark", {"html": False}).enable("table")
    article = (
        f'<article><p class="eyebrow">{html.escape(now.strftime("%Y-%m-%d %H:%M UTC"))} · {len(items)} 项</p>'
        f"<h1>{html.escape(title)}</h1>{md.render(report)}</article>"
    )
    (POSTS_DIR / slug).write_text(shell(title, f"{title}：{len(items)} 项最新研究", article, "../"))
    entries = json.loads(INDEX_DATA.read_text()) if INDEX_DATA.exists() else []
    entries = [entry for entry in entries if entry.get("url") != f"posts/{slug}"]
    entries.insert(0, {"title": title, "date": now.isoformat(), "count": len(items), "url": f"posts/{slug}", "topic": topic})
    INDEX_DATA.write_text(json.dumps(entries[:365], ensure_ascii=False, indent=2) + "\n")
    render_index(entries[:365])
    return url


def render_index(entries: list[dict[str, object]]) -> None:
    cards = []
    for entry in entries:
        date = str(entry["date"])[:10]
        cards.append(
            f'<li><a href="{html.escape(str(entry["url"]), quote=True)}"><span>{html.escape(str(entry["title"]))}</span>'
            f"<small>{html.escape(date)} · {int(entry['count'])} 项</small></a></li>"
        )
    body = (
        '<section class="hero"><p class="eyebrow">RESEARCH DIGEST</p><h1>自动化技术研究</h1>'
        '<p>AI、Agent、音频与端侧智能的中文深度简报。</p></section><ul class="posts">' + "".join(cards) + "</ul>"
    )
    (SITE_DIR / "index.html").write_text(shell("自动化技术研究", "定时更新的中文技术研究简报", body))
