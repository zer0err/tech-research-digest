"""Publish a validated local course draft into the static docs site."""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from .preview import SUPPORT_PAGES, esc, lesson_page, read_manifest, render_markdown, series_page, shell

REPO = Path(__file__).resolve().parents[1]


def publish_course(draft: Path, *, repo: Path = REPO) -> Path:
    repo = repo.resolve()
    draft = draft.resolve()
    private_root = (repo / "course_work").resolve()
    docs = (repo / "docs").resolve()
    if not draft.is_relative_to(private_root):
        raise ValueError("Course source must remain under course_work")
    if draft.is_symlink() or docs.is_symlink():
        raise ValueError("Course publication does not follow symlinks")
    data = read_manifest(draft)
    publication_sources = [draft / "preview.json", draft / "SOURCES.md"] + [
        draft / f'{lesson["id"]}.md' for lesson in data["lessons"]
    ]
    if any(path.is_symlink() or path.resolve().parent != draft for path in publication_sources):
        raise ValueError("Course publication sources must be direct, non-symlink files")
    for asset in ("course.css", "course-progress.js", "course-reader.js"):
        if not (docs / "assets" / asset).is_file():
            raise ValueError(f"Missing public course asset: {asset}")
    if not (draft / "SOURCES.md").is_file():
        raise ValueError("Missing support page: SOURCES")

    series = docs / "courses" / data["series_id"]
    staging = docs / "courses" / ("." + data["series_id"] + "-staging")
    if series.is_symlink() or staging.is_symlink():
        raise ValueError("Course destination must not be a symlink")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    (staging / "index.html").write_text(series_page(data, preview=False), encoding="utf-8")
    for lesson in data["lessons"]:
        source = (draft / f'{lesson["id"]}.md').read_text(encoding="utf-8")
        (staging / f'{lesson["id"]}.html').write_text(
            lesson_page(data, lesson, source, preview=False), encoding="utf-8"
        )
    title = SUPPORT_PAGES["SOURCES"]
    body, _ = render_markdown((draft / "SOURCES.md").read_text(encoding="utf-8"))
    page = shell(
        title,
        f'<article class="support-page"><a href="index.html">← 返回系列</a><h1>{esc(title)}</h1>'
        f'<div class="lesson-body">{body}</div></article>',
        root="../../",
        preview=False,
    )
    (staging / "SOURCES.html").write_text(page, encoding="utf-8")
    if series.exists():
        shutil.rmtree(series)
    staging.rename(series)

    hub = (
        '<section class="course-container"><header class="series-heading"><p class="eyebrow">LEARNING</p>'
        '<h1>AI 学习路线</h1><p class="lead">按系列学习，按自己的节奏练习；课程与每日资讯分开。</p></header>'
        f'<article class="series-card"><p class="eyebrow">零基础 · {len(data["lessons"])} 个单元</p>'
        f'<h2><a href="{esc(data["series_id"])}/index.html">{esc(data["title"])}</a></h2>'
        f'<p>{esc(data["description"])}</p><a class="primary-link" href="{esc(data["series_id"])}/index.html">查看学习路线 →</a>'
        '</article></section>'
    )
    (docs / "courses").mkdir(exist_ok=True)
    (docs / "courses/index.html").write_text(shell("AI 学习路线", hub, root="../", script=False, preview=False), encoding="utf-8")
    return series / "index.html"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("draft", type=Path)
    args = parser.parse_args()
    result = publish_course(args.draft)
    print(f"Published course: {result}")


if __name__ == "__main__":
    main()
