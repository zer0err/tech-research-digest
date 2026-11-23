"""Build a conservative AI-domain reading directory from published local posts."""
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

from .domain_report import MODULES
from .site import shell

# Explicit editorial mapping, not inferred from titles or model-generated summaries.
# Rotating slots record the underlying topic in source_topic. The slot name alone is not a domain.
from .domain_report import MODULES as DAILY_DOMAINS

TOPIC_MODULES = {
    **{key: (key,) for key in DAILY_DOMAINS},
    'model_research': ('models',),
    'training': ('training',),
    'inference_systems': ('inference',),
    'efficient_ai': ('inference',),
    'agents': ('agents',),
    'knowledge': ('knowledge',),
    'multimodal': ('multimodal',),
    'audio': ('multimodal',),
    'embodied': ('robotics',),
    'product_safety': ('evaluation',),
    'prompt_engineering': ('evaluation',),
    'open_source': ('infrastructure',),
    'dev_practice': ('infrastructure',),
    'ecosystem': ('infrastructure',),
    'ai_hardware': ('infrastructure',),
}


def eligible_post(post: object, site_dir: Path) -> bool:
    if not isinstance(post, dict) or post.get('status') != 'published':
        return False
    title, url, count = post.get('title'), post.get('url'), post.get('count')
    if not isinstance(title, str) or not title.strip():
        return False
    if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
        return False
    # Restrict to single, literal HTML filenames; no schemes, traversal or encoding.
    if not isinstance(url, str) or not re.fullmatch(r'posts/[A-Za-z0-9][A-Za-z0-9_-]*\.html', url):
        return False
    path = site_dir / url
    if not path.is_file() or path.resolve().parent != (site_dir / 'posts').resolve():
        return False
    return 'data-legacy-redirect="daily"' not in path.read_text(encoding='utf-8')[:800]


def render_domain_hub(site_dir: Path = Path('docs')) -> Path:
    index_path = site_dir / 'posts.json'
    posts = json.loads(index_path.read_text(encoding='utf-8')) if index_path.exists() else []
    if not isinstance(posts, list):
        raise ValueError('posts.json must contain a list')
    groups: dict[str, list[dict]] = {key: [] for key in MODULES}
    seen_urls: set[str] = set()
    for post in posts:
        if not eligible_post(post, site_dir) or post['url'] in seen_urls:
            continue
        seen_urls.add(post['url'])
        targets = []
        sections = post.get('sections')
        if isinstance(sections, list) and sections:
            for section in sections:
                if isinstance(section, dict):
                    targets.append(section.get('source_topic') or section.get('topic') or '')
        else:
            targets.append(post.get('source_topic') or post.get('topic', ''))
        filed: set[str] = set()
        for mapped in targets:
            for key in TOPIC_MODULES.get(mapped, ()):
                if key in filed:
                    continue
                filed.add(key)
                anchor = ''
                if isinstance(sections, list):
                    match = next((section for section in sections if isinstance(section, dict)
                                  and (section.get('source_topic') or section.get('topic')) == mapped
                                  and key in TOPIC_MODULES.get(section.get('source_topic') or section.get('topic'), ())), None)
                    if match and match.get('anchor'):
                        anchor = '#' + str(match['anchor'])
                groups[key].append({**post, 'url': post['url'] + anchor})
    sections = []
    links = []
    for key, title in MODULES.items():
        links.append(f'<a href="#{key}">{html.escape(title)}</a>')
        articles = sorted(groups[key], key=lambda post: str(post.get('date', '')), reverse=True)
        if articles:
            entries = ''.join(
                f'<li><a href="../{html.escape(post["url"], quote=True)}">'
                f'{html.escape(post["title"])}</a></li>' for post in articles
            )
            body = f'<p>栏目关联文章：{len(articles)} 篇</p><ul>{entries}</ul>'
        else:
            body = '<p>待补充：目前没有可按栏目明确关联的已发布文章。</p>'
        sections.append(f'<section id="{key}"><h2>{html.escape(title)}</h2>{body}</section>')
    body = (
        '<article class="about-page article-body"><h1>AI 十领域阅读导航</h1>'
        '<p>从基础模型到软件应用与智能硬件，按领域查找站内资料。</p>'
        '<p>本页基于明确的栏目映射整理，不是全文语义核实，也不代表已完整覆盖各领域。'
        '关联文章可能涉及其他方向；具体证据和适用条件请查看正文及原始来源。'
        '一份日报可以按其中各节原来源栏目出现在多个领域，链接仍指向同一篇日报。</p>'
        '<nav aria-label="领域导航">' + ' · '.join(links) + '</nav>'
        + ''.join(sections)
        + '<p><a href="../index.html#latest">浏览全部时间线</a> · '
        '<a href="../feed.xml">订阅 RSS</a></p></article>'
    )
    output = site_dir / 'domains' / 'index.html'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(shell('AI 十领域阅读导航 · VORASIO',
                            '按十个 AI 领域组织的站内已发布资料导航；基于栏目映射。',
                            body, relative_root='../', section='domains', current_page=True), encoding='utf-8')
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site-dir', type=Path, default=Path('docs'))
    print(render_domain_hub(parser.parse_args().site_dir))


if __name__ == '__main__':
    main()
