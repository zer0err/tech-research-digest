import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from research_bot import finalize, schedule


@pytest.fixture
def delivery(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr('sys.argv', ['finalize'])

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 11, 9, 11, tzinfo=UTC).astimezone(tz)

    monkeypatch.setattr(finalize, 'datetime', Clock)
    Path('work').mkdir()
    pending = {'topic': 'daily_digest', 'slot': 'daily_digest', 'title': 'Daily digest',
               'url': 'https://example.com/daily', 'created_at': '2026-11-09T11:00:00+00:00',
               'items': [], 'published_count': 2, 'notify': True}
    sent = []
    monkeypatch.setattr(finalize, 'send_telegram', sent.append)
    monkeypatch.setattr(finalize, 'send_ntfy', lambda *args, **kwargs: False)
    return pending, sent


def run(pending):
    Path('work/pending.json').write_text(json.dumps(pending))
    return finalize.main()


def test_digest_only_once_even_if_finalizer_repeated(delivery):
    pending, sent = delivery
    assert run(pending) == 0
    assert run(pending) == 0
    assert len(sent) == 1
    assert '2026-11-09' in json.loads(Path('state/seen.json').read_text())['daily_notifications']


def test_ntfy_failure_does_not_send_alert_or_repeat_telegram(delivery, monkeypatch):
    pending, sent = delivery

    def fail(*args, **kwargs):
        raise RuntimeError('ntfy unavailable')

    monkeypatch.setattr(finalize, 'send_ntfy', fail)
    run(pending)
    run(pending)
    assert len(sent) == 1


@pytest.mark.parametrize('changes', [{'replay_date': '2026-11-08'},
                                    {'created_at': '2026-11-08T11:00:00+00:00'}])
def test_old_editions_never_notify(delivery, changes):
    pending, sent = delivery
    pending.update(changes)
    run(pending)
    assert sent == []


def test_early_digest_is_not_finalized(delivery, monkeypatch):
    pending, sent = delivery
    monkeypatch.setattr(schedule, 'is_due', lambda *args: False)
    with pytest.raises(ValueError, match='before 19:00'):
        run(pending)
    assert sent == []
    assert not Path('state/seen.json').exists()


def test_empty_day_still_sends_one_status(delivery):
    pending, sent = delivery
    pending['published_count'] = 0
    run(pending)
    assert len(sent) == 1
    assert '今日暂无有效新内容' in sent[0]


def test_daytime_article_cannot_opt_into_notifications(delivery):
    pending, sent = delivery
    pending.update(topic='morning_radar', slot='morning_radar', items=[{
        'uid': 'test', 'title': 'Paper', 'url': 'https://example.com/paper',
        'published': pending['created_at'], 'summary': 'Evidence', 'source': 'Test'}])
    run(pending)
    assert sent == []


def test_failed_telegram_can_retry(delivery, monkeypatch):
    pending, sent = delivery

    def fail(*args):
        raise RuntimeError('rejected')

    monkeypatch.setattr(finalize, 'send_telegram', fail)
    with pytest.raises(RuntimeError):
        run(pending)
    assert not Path('state/seen.json').exists()
    monkeypatch.setattr(finalize, 'send_telegram', sent.append)
    run(pending)
    assert len(sent) == 1


def test_daily_schedule_boundary():
    assert not schedule.is_due('daily_digest', datetime(2026, 11, 9, 10, 59, 59, tzinfo=UTC))
    assert schedule.is_due('daily_digest', datetime(2026, 11, 9, 11, tzinfo=UTC))


def test_previous_day_receipt_does_not_block_today(delivery):
    pending, sent = delivery
    Path('state').mkdir()
    Path('state/seen.json').write_text(json.dumps({
        'version': 1, 'topics': {}, 'daily_notifications': {'2026-11-08': {'sent_at': 'yesterday'}}}))
    run(pending)
    assert len(sent) == 1


def test_workflow_daily_trigger_matches_due_time():
    import yaml

    project = Path(__file__).resolve().parents[1]
    workflow = yaml.safe_load((project / '.github/workflows/editorial-day.yml').read_text())
    # PyYAML's YAML 1.1 parser treats the GitHub Actions key `on` as True.
    triggers = workflow.get('on', workflow.get(True))
    crons = [entry['cron'] for entry in triggers['schedule']]
    assert '0 11 * * *' in crons
    assert '47 10 * * *' not in crons
    editorial = yaml.safe_load((project / 'config/editorial.yml').read_text())
    assert editorial['slots']['daily_digest']['time'] == '19:00'
