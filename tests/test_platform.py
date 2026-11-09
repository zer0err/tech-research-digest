import json
from pathlib import Path

from research_bot.platform import build_platform


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
