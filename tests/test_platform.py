import json
from datetime import UTC, datetime
from pathlib import Path

from research_bot.core import Item
from research_bot.navigation import update_document_chrome
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
    post.write_text('<html><head></head><body><header class="site-header"><nav></nav></header>'
                    '<main>正文</main><footer><span>文章来源保留。</span></footer></body></html>')
    daily = Path('docs/posts/20261101-daily.html')
    daily.write_text('<html><head></head><body><main><h2>本期结论</h2><ol><li><strong>实验结论</strong>。说明。</li></ol>'
                     '</main></body></html>')
    build_platform()
    index = Path('docs/index.html').read_text()
    assert 'class="digest-home"' in index
    header = index.split('</header>', 1)[0]
    assert 'class="reading-nav"' in header
    assert [label for label in ('日报', '领域', '学习', '工具') if f'>{label}</a>' in header] == ['日报', '领域', '学习', '工具']
    assert 'href="index.html" aria-current="page">日报' in header
    assert 'href="index.html#latest"' not in header
    assert 'class="digest-menu"' not in header
    assert index.count('href="subscribe.html"') == 1
    assert index.index('href="posts/20261101-daily.html">阅读本期') < index.index('id="latest"')
    assert '<li>实验结论</li>' in index
    assert 'id="date-picker"' in index
    assert 'id="timeline-search"' in index
    assert '<details class="digest-archive" id="latest"><summary>查找往期</summary>' in index
    assert index.count('data-status-date=') == 1
    assert 'timeline-row pending' not in index
    assert '查看发布状态' not in index
    assert '<option value="2026-11-01" selected>2026-11-01</option>' in index
    assert '编辑精选' not in index
    assert 'rel="alternate" type="application/rss+xml" title="VORASIO" href="feed.xml"' in index
    assert 'href="services.html">开发咨询' not in index.split('</header>')[0]
    assert 'href="services.html">开发咨询' in index.split('<footer class="reading-footer">')[1]
    assert 'posts/20261101-daily.html' in Path('docs/feed.xml').read_text()
    assert 'posts/20261101-daily.html' in Path('docs/sitemap.xml').read_text()
    first = post.read_text()
    assert 'data-platform-release="fixture-release"' in first
    assert 'services.html?source=/posts/fixture.html' in first
    assert '../subscribe.html' in first
    assert 'href="../index.html" aria-current="location">日报' in first
    assert 'href="../assets/site-chrome.css?v=reading-1"' in first
    assert '文章来源保留。' in first
    assert '<main id="main" tabindex="-1">正文' in first
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


def test_navigation_migration_preserves_redirects_and_existing_reading_markup():
    redirect = '<html><head><meta http-equiv="refresh" content="0; url=x.html#edition-1"></head></html>'
    assert update_document_chrome(redirect, 'posts/old.html') == redirect

    body = '<main id="chapter" tabindex="-1"><article><h1>不可更动</h1><a href="#ref">原文</a></article></main>'
    page = (
        '<html><head><script src="../assets/article.js?v=legacy"></script></head>'
        '<body><a class="knowledge-skip" href="#chapter">跳到正文</a>'
        '<header class="site-header"><nav aria-label="主导航"></nav></header>'
        + body + '<footer><span>证据说明</span></footer></body></html>'
    )
    updated = update_document_chrome(page, 'knowledge/chapter.html')
    assert body in updated
    assert 'href="../courses/index.html" aria-current="location">学习</a>' in updated
    assert 'src="../assets/article.js?v=legacy"' in updated
    assert '证据说明' in updated
    assert updated.count('跳到正文') == 1
    assert update_document_chrome(updated, 'knowledge/chapter.html') == updated
