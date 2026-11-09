"""Render explicit editorial reading selections without claiming fact verification."""
from __future__ import annotations

import html
import json
from datetime import date
from pathlib import Path

from .domain_hub import eligible_post

DEFAULT_CONFIG = Path('config/featured.json')


def render_featured(entries: list[dict], config_path: Path = DEFAULT_CONFIG,
                    *, site_dir: Path = Path('docs')) -> str:
    if not config_path.exists():
        return ''
    try:
        config = json.loads(config_path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return ''
    if not isinstance(config, dict) or not isinstance(config.get('selections'), list):
        return ''
    available = {post['url']: post for post in entries if eligible_post(post, site_dir)}
    cards = []
    seen = set()
    for selection in config['selections']:
        if not isinstance(selection, dict):
            continue
        url = selection.get('url')
        if not isinstance(url, str) or url not in available or url in seen:
            continue
        required = ('reason', 'development_question', 'audience', 'selection_date')
        if any(not isinstance(selection.get(key), str) or not selection[key].strip() for key in required):
            continue
        try:
            date.fromisoformat(selection['selection_date'])
        except ValueError:
            continue
        seen.add(url)
        post = available[url]
        esc = html.escape
        cards.append(
            '<article class="growth-card featured-card">'
            f'<p class="eyebrow">{esc(selection["audience"])} · '
            f'选入日期 {esc(selection["selection_date"])}</p>'
            f'<h3><a href="{esc(url, quote=True)}">{esc(post["title"])}</a></h3>'
            f'<p>{esc(selection["reason"])}</p>'
            f'<p><strong>开发前要问：</strong>{esc(selection["development_question"])}</p>'
            f'<a href="{esc(url, quote=True)}">阅读与回查来源 →</a></article>'
        )
        if len(cards) == 3:
            break
    if not cards:
        return ''
    return (
        '<section class="featured-section" aria-labelledby="featured-title">'
        '<h2 id="featured-title">编辑精选 · 开发决策阅读</h2>'
        '<p>按阅读价值选取，包含历史资料；不代表事实已核实或实践已验证。'
        '采用前请回查来源并在自己的环境验证。</p>'
        '<div class="growth-grid">' + ''.join(cards) + '</div></section>'
    )
