import httpx
import pytest

from research_bot import core


def test_mimo_disabled_without_explicit_flag(monkeypatch):
    monkeypatch.setenv('MIMO_API_KEY', 'not-a-real-key')
    monkeypatch.delenv('MIMO_FALLBACK_ENABLED', raising=False)
    assert not core.mimo_enabled()
    with pytest.raises(RuntimeError):
        core.mimo_analyse('title', 'focus', [])


@pytest.mark.parametrize('status,calls', [(200, 1), (429, 3)])
def test_mimo_uses_fixed_model_without_extra_notifications(monkeypatch, status, calls):
    monkeypatch.setenv('MIMO_API_KEY', 'not-a-real-key')
    monkeypatch.setenv('MIMO_FALLBACK_ENABLED', 'true')
    monkeypatch.setattr(core.time, 'sleep', lambda *_args: None)
    monkeypatch.setattr(core.random, 'random', lambda: 0)
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
    assert len(requests) == calls
    assert notifications == []
    assert requests[0][0] == 'https://api.xiaomimimo.com/v1/chat/completions'
    assert requests[0][1]['model'] == 'mimo-v2.6-flash'
    assert requests[0][1]['thinking'] == {'type': 'disabled'}


def test_mimo_timeout_does_not_send_extra_message(monkeypatch):
    monkeypatch.setenv('MIMO_API_KEY', 'not-a-real-key')
    monkeypatch.setenv('MIMO_FALLBACK_ENABLED', 'true')
    notifications = []
    monkeypatch.setattr(core, 'send_telegram', notifications.append)
    monkeypatch.setattr(core.time, 'sleep', lambda *_args: None)
    attempts = []

    def post(*args, **kwargs):
        attempts.append(1)
        raise httpx.ReadTimeout('mock timeout')

    monkeypatch.setattr(httpx.Client, 'post', post)
    with pytest.raises(httpx.ReadTimeout):
        core.mimo_analyse('title', 'focus', [])
    assert len(attempts) == 3
    assert notifications == []
