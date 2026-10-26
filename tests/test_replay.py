import json
from datetime import UTC, datetime
from pathlib import Path

from research_bot.site import publish_post


def test_backfill_preserves_edition_but_discloses_actual_publication(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('REPLAY_EDITION_DATE', '2026-10-25')
    publish_post('paper_brief', '测试', datetime(2026, 10, 25, 15, 59, tzinfo=UTC), '## 内容\n有来源的补发内容', [None])
    entry = json.loads(Path('docs/posts.json').read_text())[0]
    assert entry['execution_date'] == '2026-10-25'
    assert entry['date'] != '2026-10-25T23:59:00+08:00'
    assert entry['url'] == 'posts/20261025-paper_brief.html'
    assert '补发' in Path('docs/posts/20261025-paper_brief.html').read_text()
    assert 'data-execution-date="2026-10-25"' in Path('docs/index.html').read_text()
