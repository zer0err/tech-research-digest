import json
from datetime import UTC, datetime
from pathlib import Path

from research_bot.site import publish_post


def test_fragment_replay_is_not_listed_as_a_daily_report(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('REPLAY_EDITION_DATE', '2026-10-25')
    publish_post('paper_brief', '测试', datetime(2026, 10, 25, 15, 59, tzinfo=UTC), '## 内容\n有来源的补发内容', [None])
    assert Path('docs/posts/20261025-paper_brief.html').exists()
    assert json.loads(Path('docs/posts.json').read_text()) == []
    assert 'posts/20261025-paper_brief.html' not in Path('docs/index.html').read_text()
    assert 'posts/20261025-paper_brief.html' not in Path('docs/feed.xml').read_text()
