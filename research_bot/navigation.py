"""Shared, server-rendered navigation for the VORASIO website."""
from __future__ import annotations

import re
from html import escape, unescape
from pathlib import PurePosixPath

CHROME_CSS = 'site-chrome.css?v=reading-1'
ARTICLE_NOTE = '由 GitHub Actions 定时采集，Groq 辅助分析。重要结论请核对原始来源。'
COURSE_NOTE = '学习记录仅保存在你的浏览器，不上传。'
LINKS = (
    ('daily', '日报', 'index.html'),
    ('domains', '领域', 'domains/index.html'),
    ('learning', '学习', 'courses/index.html'),
    ('tools', '工具', 'tools/index.html'),
)
_CREDIT = (
    '<p class="reading-footer-credit">版式改编自 <a href="https://html5up.net/editorial">HTML5 UP Editorial</a>，'
    '<a href="https://creativecommons.org/licenses/by/3.0/">CC BY 3.0</a>。</p>'
)


def render_header(root: str = '', *, section: str | None = None, current_page: bool = False) -> str:
    links = []
    for key, label, destination in LINKS:
        active = f' aria-current="{"page" if current_page else "location"}"' if key == section else ''
        links.append(f'<a href="{root}{destination}"{active}>{label}</a>')
    return (
        '<header class="site-header reading-header">'
        f'<a class="reading-brand" href="{root}index.html" aria-label="VORASIO 首页">'
        '<span class="reading-brand-mark" aria-hidden="true">V</span><span>VORASIO</span></a>'
        '<nav class="reading-nav" aria-label="主导航">' + ''.join(links) + '</nav></header>'
    )


def render_footer(
    root: str = '', *, privacy: bool = False, editorial_credit: bool = False, note: str | None = None,
) -> str:
    note = note if note is not None else (COURSE_NOTE if privacy else ARTICLE_NOTE)
    extra = f'<a href="{root}privacy.html">隐私</a>' if privacy else ''
    sitemap = f'<a href="{root}sitemap.xml">站点地图</a>' if editorial_credit else ''
    return (
        '<footer class="reading-footer"><span>VORASIO</span><nav aria-label="页脚">'
        f'<a href="{root}subscribe.html">RSS 订阅</a>'
        f'<a href="{root}about.html">关于</a><a href="{root}services.html">开发咨询</a>{extra}{sitemap}</nav>'
        + (f'<p class="reading-footer-note">{escape(note)}</p>' if note else '')
        + (_CREDIT if editorial_credit else '') + '</footer>'
    )


def render_learning_choices(root: str, *, knowledge: bool = False) -> str:
    courses_active = '' if knowledge else ' aria-current="page"'
    knowledge_active = ' aria-current="page"' if knowledge else ''
    return (
        '<nav class="learning-entry-pills" aria-label="学习分类">'
        f'<a href="{root}courses/index.html"{courses_active}>课程</a>'
        f'<a href="{root}knowledge/index.html"{knowledge_active}>知识科普</a></nav>'
    )


def section_for_path(page: PurePosixPath) -> str | None:
    if page.as_posix() == 'index.html' or page.parts[0] == 'posts':
        return 'daily'
    if page.parts[0] == 'domains':
        return 'domains'
    if page.parts[0] in {'courses', 'knowledge'}:
        return 'learning'
    if page.parts[0] == 'tools':
        return 'tools'
    return None


_SITE_HEADER = re.compile(
    r"""<header\b[^>]*class=["'][^"']*\bsite-header\b[^"']*["'][^>]*>.*?</header>""", re.I | re.S,
)
_FOOTER = re.compile(r'<footer\b[^>]*>.*?</footer>', re.I | re.S)


def update_document_chrome(document: str, page_path: str) -> str:
    """Upgrade legacy generated chrome at build time; never rewrite an article body or redirect."""
    if 'reading-header' in document or '<main' not in document or not _SITE_HEADER.search(document):
        return document
    page = PurePosixPath(page_path)
    root = '../' * (len(page.parts) - 1)
    section = section_for_path(page)
    active = any(page.as_posix() == destination for _, _, destination in LINKS)
    main = re.search(r'<main\b[^>]*>', document, flags=re.I)
    if not main:
        return document
    target_id = re.search(r"""\sid=["']([^"']+)["']""", main[0])
    target = escape(target_id[1], quote=True) if target_id else 'main'
    if not target_id:
        document = document[:main.start()] + '<main id="main" tabindex="-1"' + main[0][5:] + document[main.end():]
    skip = ''
    if not re.search(r'<a\b[^>]*class="[^"]*\b(?:skip-link|knowledge-skip|issue-skip|reading-skip)\b', document):
        skip = f'<a class="reading-skip" href="#{target}">跳到正文</a>'
    document = _SITE_HEADER.sub(
        lambda _: skip + render_header(root, section=section, current_page=active), document, count=1,
    )
    end_main = document.lower().rfind('</main>') + len('</main>')
    def replace_footer(match: re.Match[str]) -> str:
        note = re.search(r'<span[^>]*>([^<]*)</span>', match[0])
        return render_footer(
            root, privacy=page.parts[0] == 'courses', editorial_credit=page.as_posix() == 'index.html',
            note=unescape(note[1]) if note else None,
        )

    tail = _FOOTER.sub(replace_footer, document[end_main:], count=1)
    document = document[:end_main] + tail
    sheet = f'<link rel="stylesheet" href="{root}assets/{CHROME_CSS}">'
    return document.replace('</head>', sheet + '</head>', 1)
