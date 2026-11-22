import json
from datetime import UTC, datetime
from pathlib import Path

from research_bot.core import Item
from research_bot.platform import build_platform
from research_bot.site import publish_post


def test_platform_regeneration_adds_routes_and_article_cta_without_duplicates(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path('docs/posts').mkdir(parents=True)
    fixture = {
        'date': '2026-11-01T09:00:00+08:00', 'topic': 'daily_report', 'status': 'published',
        'count': 3, 'url': 'posts/20261101-daily.html', 'title': '示例日报（2026-11-01）',
    }
    Path('docs/posts.json').write_text(json.dumps([fixture]))
    Path('docs/feed.xml').write_text('<rss/>')
    Path('config').mkdir()
    Path('config/platform-launch.json').write_text(json.dumps({'campaign_id': 'fixture-release'}))
    post = Path('docs/posts/fixture.html')
    post.write_text('<html><head></head><body><header><nav></nav></header><main>正文</main></body></html>')
    daily = Path('docs/posts/20261101-daily.html')
    daily.write_text('<html><head></head><body><main><h2>本期结论</h2><ol><li><strong>实验结论</strong>。说明。</li></ol>'
                     '</main></body></html>')
    build_platform()
    index = Path('docs/index.html').read_text()
    assert 'class="digest-home"' in index
    assert 'class="digest-menu"' in index
    assert index.count('href="subscribe.html"') == 1
    assert index.index('href="posts/20261101-daily.html">阅读本期') < index.index('id="latest"')
    assert '<li>实验结论</li>' in index
    assert 'id="date-picker"' in index
    assert 'id="timeline-search"' in index
    assert 'id="latest"' in index
    assert '编辑精选' not in index
    assert 'rel="alternate" type="application/rss+xml" title="VORASIO" href="feed.xml"' in index
    assert 'href="services.html">开发咨询' not in index.split('</header>')[0]
    assert 'href="services.html">开发咨询' in index.split('<footer>')[1]
    assert 'posts/20261101-daily.html' in Path('docs/feed.xml').read_text()
    assert 'posts/20261101-daily.html' in Path('docs/sitemap.xml').read_text()
    first = post.read_text()
    assert 'data-platform-release="fixture-release"' in first
    assert 'services.html?source=/posts/fixture.html' in first
    assert '../subscribe.html' in first
    assert Path('docs/domains/index.html').exists()
    assert Path('docs/services.html').exists()
    build_platform()
    assert post.read_text() == first
    assert Path('docs/index.html').read_text() == index


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
