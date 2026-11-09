from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from research_bot import launch

SHA = 'a' * 40
CONFIG = {'enabled': True, 'campaign_id': 'launch-1', 'base_url': 'https://vorasio.com'}


def prepare(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('GITHUB_RUN_ID', '123')
    for page in launch.PAGES:
        if not page or page.endswith('.html'):
            p = tmp_path / 'docs' / (page or 'index.html')
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('<main data-platform-release="launch-1">Ready</main>')
    return tmp_path / 'state' / 'launch.json'


def pages(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, text='<rss version="2.0"><channel/></rss>' if request.url.path.endswith('.xml')
                          else '<main data-platform-release="launch-1">Ready</main>')


def test_verify_then_claim_and_skip_every_existing_status(tmp_path, monkeypatch):
    receipt = prepare(tmp_path, monkeypatch)
    with httpx.Client(transport=httpx.MockTransport(pages)) as client:
        assert launch.claim(CONFIG, receipt, SHA, client)
        assert json.loads(receipt.read_text())['launch-1']['status'] == 'claimed'
        for status in ['claimed', 'sent', 'unknown']:
            launch.save(receipt, {'launch-1': {'status': status}})
            assert not launch.claim(CONFIG, receipt, SHA, client)


@pytest.mark.parametrize('failure', ['missing_marker', 'http_error', 'bad_feed'])
def test_bad_public_release_is_not_claimed(tmp_path, monkeypatch, failure):
    receipt = prepare(tmp_path, monkeypatch)

    def handler(request):
        if failure == 'http_error':
            return httpx.Response(404)
        if failure == 'missing_marker':
            return httpx.Response(200, text='<html>old release</html>')
        if request.url.path.endswith('.xml'):
            return httpx.Response(200, text='<html/>')
        return pages(request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client, pytest.raises((ValueError, httpx.HTTPError)):
        launch.claim(CONFIG, receipt, SHA, client)
    assert not receipt.exists()


def test_disabled_campaign_never_requests(tmp_path):
    with httpx.Client(transport=httpx.MockTransport(lambda r: pytest.fail('Unexpected network'))) as client:
        assert not launch.claim({}, tmp_path / 'receipt.json', SHA, client)


@pytest.mark.parametrize('timeout', [False, True])
def test_one_post_success_or_unknown_no_resend(tmp_path, monkeypatch, timeout):
    receipt = prepare(tmp_path, monkeypatch)
    launch.save(receipt, {'launch-1': {'status': 'claimed', 'sha': SHA, 'run_id': '123', 'base_url': 'https://vorasio.com'}})
    monkeypatch.setenv('TELEGRAM_BOT_TOKEN', 'not-a-real-token')
    monkeypatch.setenv('TELEGRAM_CHAT_ID', 'test-chat')
    calls = []

    def handler(request):
        calls.append(request)
        # The local pre-send receipt survives a crash or unknown response.
        assert launch.read_json(receipt)['launch-1']['status'] == 'unknown'
        assert 'WhatsApp' not in request.content.decode()
        if timeout:
            raise httpx.ReadTimeout('Ambiguous delivery')
        return httpx.Response(200, json={'ok': True, 'result': {'message_id': 456}})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert launch.send(CONFIG, receipt, SHA, client) is not timeout
        assert not launch.send(CONFIG, receipt, SHA, client)
    assert len(calls) == 1
    assert launch.read_json(receipt)['launch-1']['status'] == ('unknown' if timeout else 'sent')


def test_other_run_cannot_consume_claim(tmp_path, monkeypatch):
    receipt = prepare(tmp_path, monkeypatch)
    launch.save(receipt, {'launch-1': {'status': 'claimed', 'sha': SHA, 'run_id': 'other'}})
    with httpx.Client(transport=httpx.MockTransport(lambda r: pytest.fail('Unexpected POST'))) as client:
        assert not launch.send(CONFIG, receipt, SHA, client)
