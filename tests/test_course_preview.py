"""Preview boundary and rendering tests using synthetic, non-course content only."""
from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest

from course_system.preview import build_preview, lesson_page, read_manifest, render_markdown, series_page
from course_system.publish import publish_course


class Elements(HTMLParser):
    def __init__(self, source: str):
        super().__init__()
        self.tags: list[tuple[str, dict]] = []
        self.feed(source)

    def select(self, tag: str, attribute: str | None = None) -> list[dict]:
        return [attrs for name, attrs in self.tags if name == tag and (attribute is None or attribute in attrs)]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append((tag, dict(attrs)))


def metadata() -> dict:
    return {
        "preview_only": True,
        "series_id": "synthetic-basics",
        "content_version": "1.0.1",
        "title": "测试系列",
        "description": "合成夹具，不是真实课程。",
        "environment": "Python 3.12",
        "author_model": "Test author",
        "review_model": "Test reviewer",
        "validation": "Synthetic test only",
        "lessons": [
            {"id": "one", "title": "第一课", "summary": "第一条合成记录", "minutes": 120, "compatible_versions": ["1.0.0"],
             "exercises": [{"id": "ex-01", "title": "练习 1：合成任务甲"}, {"id": "ex-02", "title": "练习 2：合成任务乙"}]},
            {"id": "two", "title": "第二课", "summary": "第二条合成记录", "minutes": 120,
             "exercises": [{"id": "ex-01", "title": "练习 1：合成任务丙"}]},
        ],
    }


@pytest.fixture
def project(tmp_path: Path) -> tuple[Path, Path, Path]:
    repo = tmp_path / "repo"
    docs = repo / "docs"
    assets = docs / "assets"
    assets.mkdir(parents=True)
    (docs / "index.html").write_text(
        '<html><head><title>Fixture</title></head><body><nav></nav>'
        '<section id="latest">Existing timeline</section></body></html>'
    )
    (docs / "tools").mkdir()
    (docs / "tools" / "index.html").write_text(
        '<html><head><title>Tools fixture</title></head><body>Tools fixture</body></html>'
    )
    for name in ("course.css", "course-progress.js", "course-reader.js"):
        (assets / name).write_text("/* fixture asset */")
    draft = repo / "course_work" / "synthetic-basics"
    draft.mkdir(parents=True)
    (draft / "preview.json").write_text(json.dumps(metadata(), ensure_ascii=False), encoding="utf-8")
    for name in ("one", "two", "SOURCES", "REVIEW", "VALIDATION"):
        (draft / (name + ".md")).write_text(
            f"# {name}\n\n## Repeated\n\nSynthetic text.\n\n## Repeated\n"
            "\n[Series](README.md) [Other lesson](two.md#section-1) [Source](SOURCES.md)\n",
            encoding="utf-8",
        )
    return repo, draft, draft / "preview"


def files_under(directory: Path) -> dict[str, bytes]:
    return {str(path.relative_to(directory)): path.read_bytes() for path in directory.rglob("*") if path.is_file()}


def test_markdown_disables_html_script_images_and_unsafe_urls() -> None:
    rendered, toc = render_markdown('''# Title

<script>alert("unsafe")</script>
<img src="https://tracker.invalid/pixel" onerror="alert(1)">

[unsafe](javascript:alert%281%29)
![tracker](https://tracker.invalid/pixel)

## <img src=x onerror=alert(1)>
''')
    tags = Elements(rendered)
    assert not tags.select("script")
    assert not tags.select("img")
    assert all(not (link.get("href") or "").startswith("javascript:") for link in tags.select("a"))
    assert "&lt;script&gt;" in rendered
    assert "[图片：tracker]" in rendered
    assert not Elements(toc).select("img")


def test_markdown_rewrites_only_local_markdown_links() -> None:
    rendered, _ = render_markdown('''[home](README.md)
[lesson](two.md?view=compact#part)
[external](https://example.test/README.md)
[protocol relative](//example.test/two.md)
[html](two.html)
[heading](#part)
''')
    assert [item["href"] for item in Elements(rendered).select("a")] == [
        "index.html", "two.html?view=compact#part", "https://example.test/README.md",
        "//example.test/two.md", "two.html", "#part",
    ]


def test_code_is_escaped_and_copy_buttons_start_disabled() -> None:
    rendered, _ = render_markdown('```html\n</code><script>alert("x")</script>\n```\n')
    assert "&lt;/code&gt;&lt;script&gt;" in rendered
    assert not Elements(rendered).select("script")
    buttons = Elements(rendered).select("button", "data-copy-code")
    assert len(buttons) == 1 and "disabled" in buttons[0]
    assert Elements(rendered).select("pre")[0]["tabindex"] == "0"


def test_toc_anchors_are_unique_and_match_headings() -> None:
    rendered, toc = render_markdown("# Title\n\n## Same\n\n### Same\n\n## 中文\n\n## 中文\n")
    parsed = Elements(rendered)
    assert parsed.select("h1") == []
    ids = [attrs["id"] for tag, attrs in parsed.tags if tag in ("h2", "h3")]
    assert len(ids) == len(set(ids)) == 4
    assert [attrs["href"] for attrs in Elements(toc).select("a")] == ["#" + item for item in ids]


def test_series_metadata_and_inert_progress_controls() -> None:
    page = series_page(metadata())
    parsed = Elements(page)
    root = parsed.select("div", "data-course-progress")[0]
    assert root["data-series-id"] == "synthetic-basics"
    assert root["data-content-version"] == "1.0.1"
    lessons = parsed.select("li", "data-course-lesson")
    assert [item["data-lesson-id"] for item in lessons] == ["one", "two"]
    assert [item["data-compatible-versions"] for item in lessons] == ["1.0.0", ""]
    assert all(item["data-content-version"] == "1.0.1" for item in lessons)
    for attribute in ("data-progress-export", "data-progress-import", "data-progress-clear"):
        assert "disabled" in parsed.select("button", attribute)[0]
    assert "仅手动勾选才记为完成" in page


@pytest.mark.parametrize("index", [0, 1])
def test_lessons_have_manual_completion_at_end_and_correct_navigation(index: int) -> None:
    data = metadata()
    page = lesson_page(data, data["lessons"][index], "# Old title\n\n## Chapter\n\nBODY_END_MARKER\n")
    parsed = Elements(page)
    complete = parsed.select("input", "data-course-complete")
    assert len(complete) == 1
    assert complete[0]["type"] == "checkbox" and "disabled" in complete[0]
    assert "checked" not in complete[0]
    assert page.index("BODY_END_MARKER") < page.index('class="completion-panel"')
    assert "不是系统评分" in page
    assert "Old title" not in page
    current = [a for a in parsed.select("a") if a.get("aria-current") == "page" and a.get("href") == data["lessons"][index]["id"] + ".html"]
    assert len(current) == 1
    neighbors = re.search(r'<nav class="lesson-neighbors".*?</nav>', page).group()
    if index == 0:
        assert "下一课" in neighbors and "上一课" not in neighbors
        assert 'href="two.html"' in neighbors
    else:
        assert "上一课" in neighbors and "下一课" not in neighbors
        assert 'href="one.html"' in neighbors and "返回系列" in neighbors


@pytest.mark.parametrize("kind", ["series", "lesson"])
def test_pages_have_local_scripts_strict_csp_and_noindex(kind: str) -> None:
    data = metadata()
    page = series_page(data) if kind == "series" else lesson_page(data, data["lessons"][0], "Content")
    parsed = Elements(page)
    scripts = parsed.select("script")
    assert {item["src"] for item in scripts} == {"../../assets/course-progress.js", "../../assets/course-reader.js"}
    assert all("defer" in item for item in scripts)
    meta = parsed.select("meta")
    assert any(item.get("name") == "robots" and item.get("content") == "noindex,nofollow" for item in meta)
    csp = next(item["content"] for item in meta if item.get("http-equiv") == "Content-Security-Policy")
    for clause in (
        "default-src 'none'", "script-src 'self'", "connect-src 'none'", "object-src 'none'", "base-uri 'none'", "form-action 'none'"
    ):
        assert clause in csp
    assert "unsafe-inline" not in csp and "unsafe-eval" not in csp
    assert all(not key.startswith("on") for _, attrs in parsed.tags for key in attrs)


def test_metadata_is_escaped_in_all_html_contexts() -> None:
    data = metadata()
    for field in ("title", "description", "environment", "author_model", "review_model", "validation"):
        data[field] = '<script>alert("unsafe")</script>'
    data["lessons"][0]["title"] = '<img src=x onerror="unsafe">'
    data["lessons"][0]["summary"] = '<iframe src="https://unsafe.invalid">'
    for page in (series_page(data), lesson_page(data, data["lessons"][0], "## Section\nBody")):
        parsed = Elements(page)
        assert len(parsed.select("script")) == 2
        assert not parsed.select("img") and not parsed.select("iframe")
        assert "&lt;script&gt;" in page


def test_preview_build_preserves_public_files_and_original_drafts(project: tuple[Path, Path, Path]) -> None:
    repo, draft, output = project
    before_docs = files_under(repo / "docs")
    before_draft = files_under(draft)
    entry = build_preview(draft, output, repo=repo)
    assert entry == output / "courses/index.html"
    assert files_under(repo / "docs") == before_docs
    for name, contents in before_draft.items():
        assert (draft / name).read_bytes() == contents
    series_dir = output / "courses/synthetic-basics"
    for name in ("index", "one", "two", "SOURCES", "REVIEW", "VALIDATION"):
        assert (series_dir / (name + ".html")).is_file()
    assert 'href="courses/index.html"' in (output / "index.html").read_text()
    assert "Existing timeline" in (output / "index.html").read_text()
    assert "noindex,nofollow" in (output / "index.html").read_text()
    # Rebuilding should be stable and should not incorporate unrelated root content.
    first_build = files_under(output)
    build_preview(draft, output, repo=repo)
    assert files_under(output) == first_build
    assert not any(path.endswith(".md") for path in first_build)


def test_publication_writes_only_public_pages_without_preview_markers(project: tuple[Path, Path, Path]) -> None:
    repo, draft, _ = project
    unrelated = repo / "docs" / "keep.txt"
    unrelated.write_text("keep", encoding="utf-8")
    result = publish_course(draft, repo=repo)
    assert result == repo / "docs/courses/synthetic-basics/index.html"
    assert unrelated.read_text(encoding="utf-8") == "keep"
    assert (repo / "docs/courses/index.html").is_file()
    for name in ("index", "one", "two", "SOURCES"):
        page = repo / "docs/courses/synthetic-basics" / f"{name}.html"
        assert page.is_file()
        source = page.read_text(encoding="utf-8")
        assert "本地预览" not in source and "noindex,nofollow" not in source
        assert 'name="robots" content="index,follow"' in source
    assert not (repo / "docs/courses/synthetic-basics/REVIEW.html").exists()
    assert not (repo / "docs/courses/synthetic-basics/VALIDATION.html").exists()


def test_publication_rejects_symlinked_source_without_touching_existing_course(
    project: tuple[Path, Path, Path]
) -> None:
    repo, draft, _ = project
    publish_course(draft, repo=repo)
    before = files_under(repo / "docs")
    source = draft / "one.md"
    target = draft / "original-one.md"
    source.rename(target)
    source.symlink_to(target)
    with pytest.raises(ValueError):
        publish_course(draft, repo=repo)
    assert files_under(repo / "docs") == before


@pytest.mark.parametrize("destination", ["docs", "outside", "draft", "traversal"])
def test_output_boundary_blocks_public_or_external_writes(project: tuple[Path, Path, Path], destination: str) -> None:
    repo, draft, _ = project
    outputs = {"docs": repo / "docs", "outside": repo / "elsewhere", "draft": draft, "traversal": draft / ".." / ".." / "docs"}
    before = files_under(repo)
    with pytest.raises(ValueError):
        build_preview(draft, outputs[destination], repo=repo)
    assert files_under(repo) == before


def test_draft_outside_ignored_tree_is_rejected(project: tuple[Path, Path, Path]) -> None:
    repo, _, _ = project
    with pytest.raises(ValueError):
        build_preview(repo / "docs", repo / "docs/preview", repo=repo)


@pytest.mark.parametrize("which", ["output", "nested-output", "lesson", "support", "manifest", "private-root"])
def test_symlinks_are_rejected_before_writing(project: tuple[Path, Path, Path], which: str) -> None:
    repo, draft, output = project
    if which == "output":
        target = draft / "actual-output"
        target.mkdir()
        output.symlink_to(target, target_is_directory=True)
    elif which == "nested-output":
        output.mkdir()
        (output / "link").symlink_to(repo / "docs", target_is_directory=True)
    elif which in ("lesson", "support", "manifest"):
        source = draft / {"lesson": "one.md", "support": "SOURCES.md", "manifest": "preview.json"}[which]
        target = draft / ("original-" + source.name)
        source.rename(target)
        source.symlink_to(target)
    else:
        # Resolving the private root must not silently grant write access elsewhere.
        real_root = repo / "real-course-work"
        (repo / "course_work").rename(real_root)
        (repo / "course_work").symlink_to(real_root, target_is_directory=True)
    before_docs = files_under(repo / "docs")
    with pytest.raises(ValueError):
        build_preview(draft, output, repo=repo)
    assert files_under(repo / "docs") == before_docs


@pytest.mark.parametrize("mutation", [
    "not-object", "null", "bad-series-type", "bad-version-type", "false-preview",
    "empty-lessons", "too-many-lessons", "lesson-not-object", "bad-id-type", "duplicate-id",
    "traversal-id", "bad-version", "bad-compatible", "boolean-minutes", "missing-source", "empty-title",
])
def test_bad_manifest_fails_with_safe_value_error(project: tuple[Path, Path, Path], mutation: str) -> None:
    _, draft, _ = project
    data = metadata()
    if mutation == "not-object":
        data = []
    elif mutation == "null":
        data = None
    elif mutation == "bad-series-type":
        data["series_id"] = 3
    elif mutation == "bad-version-type":
        data["content_version"] = None
    elif mutation == "false-preview":
        data["preview_only"] = False
    elif mutation == "empty-lessons":
        data["lessons"] = []
    elif mutation == "too-many-lessons":
        data["lessons"] = data["lessons"] * 16
    elif mutation == "lesson-not-object":
        data["lessons"][0] = None
    elif mutation == "bad-id-type":
        data["lessons"][0]["id"] = ["one"]
    elif mutation == "duplicate-id":
        data["lessons"][1]["id"] = "one"
    elif mutation == "traversal-id":
        data["lessons"][0]["id"] = "../escape"
    elif mutation == "bad-version":
        data["content_version"] = "not-versioned"
    elif mutation == "bad-compatible":
        data["lessons"][0]["compatible_versions"] = [None]
    elif mutation == "boolean-minutes":
        data["lessons"][0]["minutes"] = True
    elif mutation == "missing-source":
        (draft / "one.md").unlink()
    else:
        data["title"] = " "
    (draft / "preview.json").write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError):
        read_manifest(draft)


def test_invalid_manifest_does_not_create_output(project: tuple[Path, Path, Path]) -> None:
    repo, draft, output = project
    (draft / "preview.json").write_text('{"broken":', encoding="utf-8")
    with pytest.raises(ValueError):
        build_preview(draft, output, repo=repo)
    assert not output.exists()


@pytest.mark.parametrize("reserved", ["index", "readme", "sources", "review", "validation"])
def test_reserved_lesson_names_cannot_overwrite_navigation_or_support_pages(
    project: tuple[Path, Path, Path], reserved: str
) -> None:
    repo, draft, output = project
    data = metadata()
    data["lessons"][0]["id"] = reserved
    (draft / (reserved + ".md")).write_text("# Synthetic reserved page\n", encoding="utf-8")
    (draft / "preview.json").write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError):
        build_preview(draft, output, repo=repo)
    assert not output.exists()


@pytest.mark.parametrize("index", [0, 1])
def test_exercises_are_individual_manual_controls_inside_the_correct_lesson(index: int) -> None:
    data = metadata()
    lesson = data["lessons"][index]
    page = lesson_page(data, lesson, "# Heading\n\nBODY_END_MARKER\n")
    panel = re.search(r'<section class="completion-panel".*?</section>', page).group()
    parsed = Elements(panel)
    owner = parsed.select("section", "data-course-lesson")[0]
    assert owner["data-lesson-id"] == lesson["id"]
    assert owner["data-content-version"] == data["content_version"]
    exercises = parsed.select("div", "data-course-exercise")
    assert [attrs["data-exercise-id"] for attrs in exercises] == [exercise["id"] for exercise in lesson["exercises"]]
    inputs = parsed.select("input", "data-exercise-complete")
    assert len(inputs) == len(lesson["exercises"])
    assert all(attrs["type"] == "checkbox" and "disabled" in attrs and "checked" not in attrs for attrs in inputs)
    assert len(parsed.select("input", "data-course-complete")) == 1
    assert page.index("BODY_END_MARKER") < page.index('data-course-exercise')
    assert len(parsed.select("span", "data-exercise-status")) == len(inputs)
    assert parsed.select("p", "data-exercise-summary")


def test_exercise_titles_cannot_inject_elements() -> None:
    data = metadata()
    data["lessons"][0]["exercises"][0]["title"] = '<img src=x onerror="unsafe">'
    page = lesson_page(data, data["lessons"][0], "Body")
    assert not Elements(page).select("img")
    assert "&lt;img" in page


@pytest.mark.parametrize("exercises", [
    None, [], {}, [None], [{"id": "../escape", "title": "Task"}], [{"id": 42, "title": "Task"}],
    [{"id": "ex-01", "title": " "}], [{"id": "ex-01", "title": None}],
    [{"id": "ex-01", "title": "Task one"}, {"id": "ex-01", "title": "Task two"}],
])
def test_exercise_metadata_rejects_empty_unsafe_or_duplicate_items(
    project: tuple[Path, Path, Path], exercises: object
) -> None:
    repo, draft, output = project
    data = metadata()
    data["lessons"][0]["exercises"] = exercises
    (draft / "preview.json").write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError):
        build_preview(draft, output, repo=repo)
    assert not output.exists()


def test_all_generated_local_links_assets_and_anchors_resolve(project: tuple[Path, Path, Path]) -> None:
    repo, draft, output = project
    build_preview(draft, output, repo=repo)
    for path in output.rglob("*.html"):
        parsed = Elements(path.read_text(encoding="utf-8"))
        for tag, attrs in parsed.tags:
            attribute = "src" if tag in ("script", "img") else "href" if tag in ("a", "link") else None
            if attribute is None or attribute not in attrs:
                continue
            url = urlsplit(attrs[attribute])
            if url.scheme or url.netloc:
                continue
            destination = (path.parent / unquote(url.path)).resolve() if url.path else path.resolve()
            assert destination.is_relative_to(output.resolve()), (path.name, attrs[attribute])
            assert destination.is_file(), (path.name, attrs[attribute])
            if url.fragment and destination.suffix == ".html":
                target = Elements(destination.read_text(encoding="utf-8"))
                assert unquote(url.fragment) in {a.get("id") for _, a in target.tags}, (path.name, attrs[attribute])
