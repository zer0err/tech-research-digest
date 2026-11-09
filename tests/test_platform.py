import json
from datetime import UTC, datetime
from pathlib import Path

from research_bot.core import Item
from research_bot.platform import build_platform
from research_bot.site import publish_post


def test_platform_regeneration_adds_routes_and_article_cta_without_duplicates(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path('docs/posts').mkdir(parents=True)
    Path('docs/posts.json').write_text('[]')
    Path('docs/feed.xml').write_text('<rss/>')
    Path('config').mkdir()
    Path('config/platform-launch.json').write_text(json.dumps({'campaign_id': 'fixture-release'}))
    post = Path('docs/posts/fixture.html')
    post.write_text('<html><head></head><body><header><nav></nav></header><main>正文</main></body></html>')
    build_platform()
    first = post.read_text()
    assert 'data-platform-release="fixture-release"' in first
    assert 'services.html?source=/posts/fixture.html' in first
    assert '../subscribe.html' in first
    assert Path('docs/domains/index.html').exists()
    assert Path('docs/services.html').exists()
    build_platform()
    assert post.read_text() == first


def test_scheduled_article_and_same_day_rewrite_keep_conversion_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('PUBLIC_BASE_URL', 'https://vorasio.com')
    item = Item('fixture', '资料', 'https://example.com/source', '2026-11-09', '测试摘要', 'fixture')
    for text in ('首次正文', '修订正文'):
        publish_post('agents', 'Agent 项目', datetime(2026, 11, 9, tzinfo=UTC), text, [item])
        page = Path('docs/posts/20261109-agents.html').read_text()
        assert page.count('data-growth-cta') == 1
        assert '../services.html?source=/posts/20261109-agents.html' in page
        assert '<link rel="alternate" type="application/rss+xml"' in page
        assert text in page
