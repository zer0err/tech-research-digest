import httpx
import pytest

from research_bot import core


def test_mimo_disabled_without_explicit_flag(monkeypatch):
    monkeypatch.setenv('MIMO_API_KEY', 'not-a-real-key')
    monkeypatch.delenv('MIMO_FALLBACK_ENABLED', raising=False)
    assert not core.mimo_enabled()
    with pytest.raises(RuntimeError):
        core.mimo_analyse('title', 'focus', [])


@pytest.mark.parametrize('status', [200, 429])
def test_mimo_uses_fixed_model_and_always_notifies(monkeypatch, status):
    monkeypatch.setenv('MIMO_API_KEY', 'not-a-real-key')
    monkeypatch.setenv('MIMO_FALLBACK_ENABLED', 'true')
    notifications = []
    monkeypatch.setattr(core, 'send_telegram', notifications.append)
    requests = []

    def post(self, url, **kwargs):
        requests.append((url, kwargs['json']))
        return httpx.Response(status, json={'choices': [{'finish_reason': 'stop', 'message': {'content': 'report'}}]},
                              request=httpx.Request('POST', url))

    monkeypatch.setattr(httpx.Client, 'post', post)
    if status == 200:
        assert core.mimo_analyse('title', 'focus', []) == 'report'
    else:
        with pytest.raises(RuntimeError):
            core.mimo_analyse('title', 'focus', [])
    assert len(requests) == len(notifications) == 1
    assert requests[0][0] == 'https://api.xiaomimimo.com/v1/chat/completions'
    assert requests[0][1]['model'] == 'mimo-v2.6-flash'
    assert requests[0][1]['thinking'] == {'type': 'disabled'}
    assert 'mimo-v2.6-flash' in notifications[0]


def test_mimo_timeout_still_sends_usage_notice(monkeypatch):
    monkeypatch.setenv('MIMO_API_KEY', 'not-a-real-key')
    monkeypatch.setenv('MIMO_FALLBACK_ENABLED', 'true')
    notifications = []
    monkeypatch.setattr(core, 'send_telegram', notifications.append)

    def post(*args, **kwargs):
        raise httpx.ReadTimeout('mock timeout')

    monkeypatch.setattr(httpx.Client, 'post', post)
    with pytest.raises(httpx.ReadTimeout):
        core.mimo_analyse('title', 'focus', [])
    assert len(notifications) == 1
