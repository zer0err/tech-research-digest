"""Deterministic, local-only course UI preview. This is not a publication gate."""
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

from markdown_it import MarkdownIt

REPO = Path(__file__).resolve().parents[1]
ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
VERSION = re.compile(r"^\d+\.\d+\.\d+$")
CSP = (
    "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; "
    "font-src 'self'; connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'"
)
SUPPORT_PAGES = {"SOURCES": "来源与使用记录", "REVIEW": "AI 自查记录", "VALIDATION": "运行验证记录"}


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def read_manifest(draft: Path) -> dict:
    """UI metadata is deliberately separate from release evidence."""
    metadata_path = draft / "preview.json"
    if metadata_path.is_symlink():
        raise ValueError("Preview metadata must not be a symlink")
    data = json.loads(metadata_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Preview metadata must be an object")
    if data.get("preview_only") is not True or not isinstance(data.get("series_id"), str) or not ID.fullmatch(data["series_id"]):
        raise ValueError("Preview requires preview_only=true and a safe series ID")
    if not isinstance(data.get("content_version"), str) or not VERSION.fullmatch(data["content_version"]):
        raise ValueError("Invalid content version")
    for field in ("title", "description", "environment", "author_model", "review_model", "validation"):
        if not isinstance(data.get(field), str) or not data[field].strip():
            raise ValueError(f"Missing preview field: {field}")
    lessons = data.get("lessons", [])
    if not isinstance(lessons, list) or not 1 <= len(lessons) <= 30:
        raise ValueError("Preview must contain 1–30 lessons")
    ids = set()
    for lesson in lessons:
        if not isinstance(lesson, dict):
            raise ValueError("Lesson metadata must be an object")
        lesson_id = lesson.get("id", "")
        if (
            not isinstance(lesson_id, str) or not ID.fullmatch(lesson_id) or lesson_id in ids
            or lesson_id in {"index", "readme", "sources", "review", "validation"}
        ):
            raise ValueError("Unsafe or duplicate lesson ID")
        ids.add(lesson_id)
        for field in ("title", "summary"):
            if not isinstance(lesson.get(field), str) or not lesson[field].strip():
                raise ValueError(f"Missing lesson field: {field}")
        if type(lesson.get("minutes")) is not int or not 90 <= lesson["minutes"] <= 150:
            raise ValueError("Invalid lesson duration")
        compatible = lesson.get("compatible_versions", [])
        if not isinstance(compatible, list) or not all(isinstance(v, str) and VERSION.fullmatch(v) for v in compatible):
            raise ValueError("Invalid compatible versions")
        exercises = lesson.get("exercises", [])
        if not isinstance(exercises, list) or not exercises:
            raise ValueError("Each lesson needs at least one trackable exercise")
        exercise_ids = set()
        for exercise in exercises:
            if not isinstance(exercise, dict) or not isinstance(exercise.get("id"), str) or not ID.fullmatch(exercise["id"]):
                raise ValueError("Unsafe exercise ID")
            if exercise["id"] in exercise_ids or not isinstance(exercise.get("title"), str) or not exercise["title"].strip():
                raise ValueError("Duplicate exercise ID or empty title")
            exercise_ids.add(exercise["id"])
        source_path = draft / (lesson_id + ".md")
        if source_path.is_symlink() or source_path.resolve().parent != draft.resolve() or not source_path.is_file():
            raise ValueError("Lesson source must be a local Markdown file")
    return data


def render_markdown(source: str, *, remove_title: bool = True) -> tuple[str, str]:
    md = MarkdownIt("commonmark", {"html": False}).enable("table")
    tokens = md.parse(source)
    if remove_title and tokens and tokens[0].type == "heading_open" and tokens[0].tag == "h1":
        tokens = tokens[3:]
    toc = []
    section_number = 0
    for index, token in enumerate(tokens):
        if token.type == "heading_open" and token.tag in ("h2", "h3"):
            section_number += 1
            anchor = f"section-{section_number}"
            token.attrSet("id", anchor)
            label = tokens[index + 1].content
            toc.append(f'<li class="toc-{token.tag}"><a href="#{anchor}">{esc(label)}</a></li>')
        for child in token.children or []:
            if child.type == "link_open":
                href = child.attrGet("href") or ""
                parts = urlsplit(href)
                # Rewrite only local Markdown destinations, never external documentation URLs.
                if not parts.scheme and not parts.netloc and parts.path.endswith(".md"):
                    path = "index.html" if parts.path == "README.md" else parts.path[:-3] + ".html"
                    child.attrSet("href", urlunsplit(("", "", path, parts.query, parts.fragment)))
            elif child.type == "image":
                # Draft images must not create third-party requests or tracking pixels.
                child.type = "text"
                child.content = "[图片：" + child.content + "]"
    for token in tokens:
        if token.type == "fence":
            language = token.info.strip().split()[0] if token.info.strip() else "text"
            copy_label = "复制文本" if language in ("text", "plaintext", "output") else "复制代码"
            display_language = "输出 / 文本" if language in ("text", "plaintext", "output") else language
            token.type = "html_block"
            token.content = (
                '<figure class="code-example"><figcaption>'
                f'<span>{esc(display_language)}</span><button type="button" data-copy-code disabled>{copy_label}</button>'
                '</figcaption><pre tabindex="0" aria-label="代码或预期输出"><code>'
                + esc(token.content) + '</code></pre><span class="copy-status" role="status"></span></figure>'
            )
    return md.renderer.render(tokens, md.options, {}), '<ol>' + "".join(toc) + '</ol>'


def shell(title: str, body: str, *, root: str, script: bool = True, preview: bool = True) -> str:
    scripts = (
        f'<script defer src="{root}assets/course-progress.js"></script>'
        f'<script defer src="{root}assets/course-reader.js"></script>'
    ) if script else ""
    return (
        '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<meta http-equiv="Content-Security-Policy" content="{esc(CSP)}">'
        + ('<meta name="robots" content="noindex,nofollow">' if preview else '<meta name="robots" content="index,follow">')
        + '<meta name="referrer" content="no-referrer">'
        f'<title>{esc(title)} · VORASIO</title>'
        f'<link rel="stylesheet" href="{root}assets/course.css">{scripts}</head><body>'
        '<a class="skip-link" href="#main">跳到正文</a>'
        '<header class="site-header"><a class="brand" href="' + root + 'index.html">VORASIO</a>'
        f'<nav aria-label="主导航"><a href="{root}index.html#latest">时间线</a>'
        f'<a aria-current="page" href="{root}courses/index.html">AI 学习</a>'
        + (f'<a href="{root}knowledge/index.html">AI 知识科普</a>' if not preview else '')
        + '</nav></header>'
        + ('<div class="preview-banner">本地预览 · 课程草稿，尚未公开发布</div>' if preview else '')
        + f'<main id="main">{body}</main>'
        '<footer>VORASIO · AI 学习 <span>学习记录仅保存在你的浏览器，不上传。</span></footer></body></html>'
    )


def progress_root(data: dict) -> str:
    return f'data-course-progress data-series-id="{esc(data["series_id"])}" data-content-version="{esc(data["content_version"])}"'


def lesson_attrs(data: dict, lesson: dict) -> str:
    return (
        f'data-course-lesson data-lesson-id="{esc(lesson["id"])}" '
        f'data-content-version="{esc(data["content_version"])}" '
        f'data-compatible-versions="{esc(",".join(lesson.get("compatible_versions", [])))}"'
    )


def lesson_list(data: dict, *, current: str = "", compact: bool = False) -> str:
    rows = []
    for index, lesson in enumerate(data["lessons"], 1):
        selected = ' aria-current="page"' if lesson["id"] == current else ""
        summary = "" if compact else f'<p>{esc(lesson["summary"])}</p>'
        rows.append(
            f'<li {lesson_attrs(data, lesson)}><span class="unit-number">{index:02}</span><div>'
            f'<a href="{esc(lesson["id"])}.html"{selected}>{esc(lesson["title"])}</a>{summary}'
            f'<span class="lesson-detail">约 {lesson["minutes"]} 分钟 · <span data-lesson-status>尚未标记</span></span>'
            '</div></li>'
        )
    return '<ol class="lesson-list">' + "".join(rows) + '</ol>'


def progress_panel(data: dict, *, controls: bool = False) -> str:
    buttons = (
        '<div class="progress-actions"><button type="button" data-progress-export disabled>导出进度</button>'
        '<button type="button" data-progress-import disabled>导入进度</button>'
        '<input type="file" data-progress-file accept="application/json,.json" hidden aria-label="选择进度文件">'
        '<button type="button" data-progress-clear disabled>清除本系列进度</button></div>'
        '<button type="button" data-progress-export-raw hidden disabled>导出损坏的原始数据</button>'
    ) if controls else ""
    return (
        '<section class="progress-panel" aria-label="本地学习进度"><h2>你的学习进度</h2>'
        '<p data-progress-summary aria-live="polite">启用 JavaScript 后显示本地进度</p>'
        f'<progress data-progress-meter value="0" max="{len(data["lessons"])}" aria-label="已完成单元"></progress>'
        '<p class="small-note">仅手动勾选才记为完成。进度按域名与浏览器隔离；换设备或清理数据后不会自动恢复。</p>'
        '<p class="small-note">进度不会上传；公开站点的托管服务仍可能保留常规访问日志。</p>'
        '<p data-progress-notice role="status"></p>' + buttons +
        '<noscript><p>当前未启用 JavaScript。仍可阅读全部课程，但无法记录进度或复制代码。</p></noscript></section>'
    )


def metadata(data: dict, *, preview: bool = True) -> str:
    fields = [
        ("学习环境", data["environment"]), ("创作 AI", data["author_model"]),
        ("自查 AI", data["review_model"]), ("代码验证", data["validation"]),
    ]
    return (
        '<dl class="course-facts">'
        + "".join(f'<div><dt>{esc(k)}</dt><dd>{esc(v)}</dd></div>' for k, v in fields)
        + '<div><dt>参考来源</dt><dd><a href="SOURCES.html">官方文档与使用说明</a></dd></div>'
        + ('<div><dt>检查记录</dt><dd><a href="REVIEW.html">AI 自查</a> · '
           '<a href="VALIDATION.html">运行验证</a></dd></div>' if preview else '')
        + '</dl>'
    )


def series_page(data: dict, *, preview: bool = True) -> str:
    return shell(data["title"], (
        f'<div class="course-container" {progress_root(data)}><p class="breadcrumb"><a href="../index.html">AI 学习</a> / 入门系列</p>'
        '<header class="series-heading"><p class="eyebrow">PYTHON · AI 应用开发 · 从零开始</p>'
        f'<h1>{esc(data["title"])}</h1><p class="lead">{esc(data["description"])}</p>'
        f'<p class="small-note">{len(data["lessons"])} 个单元 · 每课约 2 小时（估计） · 绝大多数练习可离线完成</p></header>'
        '<div class="series-grid"><section aria-labelledby="route-heading"><h2 id="route-heading">学习路线</h2>'
        + lesson_list(data) + '</section><aside>' + progress_panel(data, controls=True) + '</aside></div>'
        '<section class="source-summary"><h2>环境、来源与验证</h2>' + metadata(data, preview=preview) +
        '<p class="small-note">路线从 Python 基础延伸到模型 API、检索、引用、评测和本地网页应用。'
        '发布前须完成全部代码与页面验证；未实测的平台不会标记为已验证。</p></section></div>'
    ), root="../../", preview=preview)


def lesson_page(data: dict, lesson: dict, source: str, *, preview: bool = True) -> str:
    index = data["lessons"].index(lesson)
    body, toc = render_markdown(source)
    neighbors = []
    for position, label in ((index - 1, "上一课"), (index + 1, "下一课")):
        if 0 <= position < len(data["lessons"]):
            other = data["lessons"][position]
            neighbors.append(f'<a href="{esc(other["id"])}.html">{label} · {esc(other["title"])}</a>')
    if index == len(data["lessons"]) - 1:
        neighbors.append('<a href="index.html">返回系列 · 查看学习进度</a>')
    exercises = ''.join(
        '<div class="exercise-check" data-course-exercise data-exercise-id="' + esc(exercise["id"]) + '">'
        '<label class="completion-label"><input type="checkbox" data-exercise-complete disabled> '
        + esc(exercise["title"]) + '</label><span data-exercise-status class="small-note">尚未标记</span></div>'
        for exercise in lesson["exercises"]
    )
    return shell(lesson["title"], (
        f'<div class="course-container" {progress_root(data)}><p class="breadcrumb">'
        '<a href="../index.html">AI 学习</a> / <a href="index.html">系列目录</a></p>'
        '<div class="lesson-layout"><aside class="lesson-sidebar"><details class="series-directory">'
        '<summary>系列目录</summary>' + lesson_list(data, current=lesson["id"], compact=True) + '</details>'
        + progress_panel(data) + '</aside><article class="lesson-article"><header><p class="eyebrow">'
        f'单元 {index + 1:02} / {len(data["lessons"]):02} · 零基础 · 约 {lesson["minutes"]} 分钟</p>'
        f'<h1>{esc(lesson["title"])}</h1>' + metadata(data, preview=preview) + '</header>'
        '<details class="chapter-directory"><summary>本课章节</summary>' + toc + '</details>'
        '<div class="lesson-body">' + body + '</div>'
        f'<section class="completion-panel" {lesson_attrs(data, lesson)} aria-labelledby="completion-heading">'
        '<h2 id="completion-heading">学完这一课了吗？</h2>'
        '<p>请运行正文代码、完成练习并核对结果，再分别勾选。记录由你确认，不是系统评分。</p>'
        '<div class="exercise-checklist" aria-label="逐项练习进度"><h3>本课练习</h3>' + exercises +
        '<p data-exercise-summary class="small-note"></p></div>'
        '<label class="completion-label"><input type="checkbox" data-course-complete disabled> 我已完成本单元的阅读与练习</label>'
        '<p data-lesson-status class="small-note">尚未标记</p><p data-progress-notice role="status"></p>'
        '<p class="small-note">可以随时取消；进度仅保存在当前浏览器。<a href="index.html">管理或导出进度</a></p></section>'
        '<nav class="lesson-neighbors" aria-label="前后单元">' + "".join(neighbors) + '</nav>'
        '<!-- Reserved extension points only; no advertising or discussion scripts are loaded. -->'
        '<div data-course-discussion-slot hidden></div><div data-course-ad-slot hidden></div>'
        '</article></div></div>'
    ), root="../../", preview=preview)


def build_preview(draft: Path, output: Path, *, repo: Path = REPO) -> Path:
    """Never write under docs/. Drafts and output must remain in ignored course_work/."""
    if any(path.is_symlink() for path in (output, *output.parents)) or (repo / 'course_work').is_symlink():
        raise ValueError("Preview path must not traverse symlinks")
    draft, output, repo = draft.resolve(), output.resolve(), repo.resolve()
    private_root = (repo / "course_work").resolve()
    if not draft.is_relative_to(private_root) or not output.is_relative_to(draft) or output == draft:
        raise ValueError("Draft and preview must remain under the ignored course_work directory")
    data = read_manifest(draft)
    # Reject symlinks throughout the existing output before writing any file.
    if output.exists() and any(path.is_symlink() for path in output.rglob("*")):
        raise ValueError("Preview output must not contain symlinks")
    if any(path.is_symlink() for path in (repo / "docs").rglob("*")):
        raise ValueError("Site snapshot must not contain symlinks")
    for name in SUPPORT_PAGES:
        source_path = draft / (name + '.md')
        if source_path.is_symlink() or not source_path.is_file():
            raise ValueError("Support pages must be local Markdown files")
    output.mkdir(parents=True, exist_ok=True)
    shutil.copytree(repo / "docs", output, dirs_exist_ok=True)
    series_dir = output / "courses" / data["series_id"]
    series_dir.mkdir(parents=True, exist_ok=True)
    (series_dir / "index.html").write_text(series_page(data), encoding="utf-8")
    for lesson in data["lessons"]:
        rendered = lesson_page(data, lesson, (draft / (lesson["id"] + ".md")).read_text(encoding="utf-8"))
        (series_dir / (lesson["id"] + ".html")).write_text(rendered, encoding="utf-8")
    for name, title in SUPPORT_PAGES.items():
        body, _ = render_markdown((draft / (name + ".md")).read_text(encoding="utf-8"))
        rendered = shell(title, '<article class="support-page"><a href="index.html">← 返回系列</a>'
                         f'<h1>{esc(title)}</h1><div class="lesson-body">{body}</div></article>', root="../../")
        (series_dir / (name + ".html")).write_text(rendered, encoding="utf-8")
    hub = (
        '<section class="course-container"><header class="series-heading"><p class="eyebrow">LEARNING</p>'
        '<h1>AI 学习路线</h1><p class="lead">按系列学习，按自己的节奏练习。这里的课程与每日资讯分开。</p></header>'
        f'<article class="series-card"><p class="eyebrow">零基础 · {len(data["lessons"])} 个单元</p>'
        f'<h2><a href="{esc(data["series_id"])}/index.html">{esc(data["title"])}</a></h2>'
        f'<p>{esc(data["description"])}</p><a class="primary-link" href="{esc(data["series_id"])}/index.html">查看学习路线 →</a>'
        '</article></section>'
    )
    (output / "courses/index.html").write_text(shell("AI 学习路线", hub, root="../", script=False), encoding="utf-8")
    home = (output / "index.html").read_text(encoding="utf-8")
    home = home.replace('</head>', '<meta name="robots" content="noindex,nofollow"></head>')
    home = home.replace('<nav>', '<nav><a href="courses/index.html">AI 学习</a>', 1)
    home = home.replace('<section id="latest">', (
        '<section class="timeline-card" aria-labelledby="learning-heading"><p class="eyebrow">本地预览 · AI 学习</p>'
        '<h2 id="learning-heading">从第一行代码开始</h2>'
        '<p>18 课完整路线：从第一行 Python 代码到可验证的本地 AI 说明书助手。</p>'
        '<a class="read-link" href="courses/index.html">进入学习路线 →</a></section><section id="latest">'
    ), 1)
    (output / "index.html").write_text(home, encoding="utf-8")
    # Preserve the already-open local lesson URLs without redirects or duplicate lesson content.
    for name in [*(lesson["id"] for lesson in data["lessons"]), *SUPPORT_PAGES]:
        canonical = series_dir / (name + ".html")
        # Legacy local pages remain usable; their navigation leads into the canonical course tree.
        base = f'courses/{data["series_id"]}/{name}.html'

        def rewrite(match: re.Match, base: str = base) -> str:
            value = html.unescape(match[2])
            if value.startswith('#') or urlsplit(value).scheme:
                return match[0]
            return f'{match[1]}="{esc(urljoin(base, value))}"'

        legacy = re.sub(r'(href|src)="([^"]+)"', rewrite, canonical.read_text(encoding="utf-8"))
        (output / (name + '.html')).write_text(legacy, encoding="utf-8")
    return output / "courses/index.html"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("draft", type=Path)
    args = parser.parse_args()
    result = build_preview(args.draft, args.draft / "preview")
    print(f"Local course preview: {result}")


if __name__ == "__main__":
    main()
