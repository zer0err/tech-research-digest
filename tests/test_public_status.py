import json
from pathlib import Path

from research_bot.public_status import export


def test_public_receipts_do_not_expose_pending_payload(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path('state').mkdir()
    Path('state/slots.json').write_text(json.dumps({'version': 1, 'slots': {
        '2026-10-25:morning_radar': {'status': 'already_published', 'attempts': 2,
                                    'pending': {'private': 'secret'}, 'maintenance_notified': True}}}))
    result = export()
    assert result['2026-10-25:morning_radar'] == {'status': 'already_published', 'attempts': 2}
    assert 'secret' not in Path('docs/slot-status.json').read_text()
