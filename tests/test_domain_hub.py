from __future__ import annotations

import json
from pathlib import Path

import pytest

from research_bot.domain_hub import eligible_post, render_domain_hub
from research_bot.domain_report import MODULES


def post(**changes):
    return {'title': '模型 <script>alert(1)</script>', 'url': 'posts/20261109-model.html',
            'status': 'published', 'count': 1, 'topic': 'model_research',
            'date': '2026-11-09', **changes}


def site(tmp_path: Path, entries: list) -> Path:
    (tmp_path / 'posts').mkdir()
    (tmp_path / 'posts/20261109-model.html').write_text('published article')
    (tmp_path / 'posts.json').write_text(json.dumps(entries))
    return tmp_path


def test_hub_lists_ten_domains_without_claiming_complete_coverage(tmp_path):
    root = site(tmp_path, [post(), post(), post(topic='daily_digest'), post(topic='core_research')])
    page = render_domain_hub(root).read_text()
    for key, title in MODULES.items():
        assert f'id="{key}"' in page
        assert title in page
    assert '不是全文语义核实' in page
    assert '待补充' in page
    assert page.count('href="../posts/20261109-model.html"') == 1
    assert '&lt;script&gt;' in page
    assert '<script>alert' not in page


@pytest.mark.parametrize('changes', [
    {'status': 'fallback'}, {'count': 0}, {'count': True}, {'title': ''},
    {'url': 'https://evil.example/x.html'}, {'url': '//evil.example/x.html'},
    {'url': 'posts/../secret.html'}, {'url': 'posts/%2e%2e.html'},
    {'url': 'posts/20261109-model.html?x=1'}, {'url': 'posts/missing.html'},
    {'url': 'posts/a"onclick="x.html'}, {'url': 'posts\\20261109-model.html'},
])
def test_rejects_invalid_or_unpublished_articles(tmp_path, changes):
    root = site(tmp_path, [])
    assert not eligible_post(post(**changes), root)


def test_rejects_symlink_outside_posts(tmp_path):
    root = site(tmp_path, [])
    outside = tmp_path / 'private.html'
    outside.write_text('private')
    (root / 'posts/linked.html').symlink_to(outside)
    assert not eligible_post(post(url='posts/linked.html'), root)


def test_rotating_application_slot_is_not_a_domain_claim(tmp_path):
    root = site(tmp_path, [post(topic='applied_ai')])
    page = render_domain_hub(root).read_text()
    assert 'href="../posts/20261109-model.html"' not in page
    assert page.count('待补充：') == len(MODULES)


def test_missing_post_index_builds_empty_directory(tmp_path):
    page = render_domain_hub(tmp_path).read_text()
    assert page.count('待补充：') == len(MODULES)
