"""Build public discovery and conversion pages without publishing or notifying."""
from __future__ import annotations

import html
import json
import os
import re
from pathlib import Path

from .growth import article_callout
from .site import render_index


def release_id() -> str:
    path = Path('config/platform-launch.json')
    if not path.exists():
        return ''
    value = json.loads(path.read_text()).get('campaign_id', '')
    return str(value)


def build_platform() -> None:
    config_path = Path('config/platform-launch.json')
    config = json.loads(config_path.read_text()) if config_path.exists() else {}
    if config.get('base_url') and not os.getenv('PUBLIC_BASE_URL'):
        os.environ['PUBLIC_BASE_URL'] = str(config['base_url']).rstrip('/')
    entries = json.loads(Path('docs/posts.json').read_text())
    render_index(entries)
    release = html.escape(release_id(), quote=True)
    for page in Path('docs').rglob('*.html'):
        content = page.read_text()
        root = '../' * (len(page.relative_to('docs').parts) - 1)
        if 'assets/growth.css' not in content:
            content = content.replace('</head>', f'<link rel="stylesheet" href="{root}assets/growth.css"></head>')
        if 'rel="alternate"' not in content:
            content = content.replace('</head>', f'<link rel="alternate" type="application/rss+xml" title="VORASIO" '
                                      f'href="{root}feed.xml"></head>')
        if 'href="' + root + 'subscribe.html"' not in content.split('</header>')[0]:
            content = content.replace('</nav></header>', f'<a href="{root}domains/index.html">领域导航</a>'
                                      f'<a href="{root}subscribe.html">订阅精选</a>'
                                      f'<a href="{root}services.html">开发咨询</a></nav></header>', 1)
        if page.parent.name == 'posts':
            cta = article_callout(root, '/posts/' + page.name)
            if 'data-growth-cta' in content:
                content = re.sub(r'<section class="growth-card" data-growth-cta>.*?</section>', lambda _, replacement=cta: replacement,
                                 content, count=1, flags=re.S)
            else:
                content = content.replace('</main>', cta + '</main>', 1)
        if release:
            content = re.sub(r' data-platform-release="[^"]*"', '', content)
            content = content.replace('<body', f'<body data-platform-release="{release}"', 1)
        page.write_text(content)


if __name__ == '__main__':
    build_platform()
