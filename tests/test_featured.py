from __future__ import annotations

import json

from research_bot.featured import render_featured


def fixture(tmp_path, **changes):
    (tmp_path / 'posts').mkdir()
    (tmp_path / 'posts/a.html').write_text('article')
    entry = {'url': 'posts/a.html', 'title': '<script>title</script>',
             'status': 'published', 'count': 1, **changes}
    selection = {'url': 'posts/a.html', 'selection_date': '2026-11-09',
                 'audience': '软件', 'reason': '<b>reason</b>', 'development_question': '问题 <x>'}
    path = tmp_path / 'featured.json'
    path.write_text(json.dumps({'selections': [selection]}))
    return entry, selection, path


def test_explicit_selection_escapes_text_and_links(tmp_path):
    entry, _, path = fixture(tmp_path)
    page = render_featured([entry], path, site_dir=tmp_path)
    assert '编辑精选' in page
    assert '&lt;script&gt;title' in page
    assert '&lt;b&gt;reason' in page
    assert '&lt;x&gt;' in page
    assert '不代表事实已核实' in page
    assert 'href="posts/a.html"' in page


def test_not_selected_means_no_featured_section(tmp_path):
    entry, _, path = fixture(tmp_path)
    path.write_text('{"selections": []}')
    assert render_featured([entry], path, site_dir=tmp_path) == ''
    assert render_featured([entry], tmp_path / 'missing.json', site_dir=tmp_path) == ''


def test_invalid_published_state_and_missing_files_are_excluded(tmp_path):
    entry, _, path = fixture(tmp_path, status='fallback')
    assert render_featured([entry], path, site_dir=tmp_path) == ''
    entry.update(status='published', count=0)
    assert render_featured([entry], path, site_dir=tmp_path) == ''
    entry.update(count=1)
    (tmp_path / 'posts/a.html').unlink()
    assert render_featured([entry], path, site_dir=tmp_path) == ''


def test_unsafe_and_incomplete_selections_are_ignored(tmp_path):
    entry, selection, path = fixture(tmp_path)
    for changes in [{'url': 'https://example.com/a.html'}, {'url': 'posts/../a.html'},
                    {'selection_date': 'not-date'}, {'reason': ''}]:
        path.write_text(json.dumps({'selections': [{**selection, **changes}]}))
        assert render_featured([entry], path, site_dir=tmp_path) == ''


def test_duplicate_selections_are_not_rendered_twice(tmp_path):
    entry, selection, path = fixture(tmp_path)
    path.write_text(json.dumps({'selections': [selection, selection]}))
    page = render_featured([entry], path, site_dir=tmp_path)
    assert page.count('featured-card') == 1
