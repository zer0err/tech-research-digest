"""Protocol tests use explicit fixture backends; live Codex evidence stays in outputs/a2a."""
import asyncio

import pytest

pytest.importorskip('a2a')
import httpx

from agent_bridge.server import create_app

HEADERS = {'Authorization': 'Bearer fixture', 'A2A-Version': '1.0'}


def message(text='review', context=None):
    value = {'messageId': 'fixture', 'role': 'ROLE_USER', 'parts': [{'text': text}]}
    if context:
        value['contextId'] = context
    return {'message': value}


def test_authentication_and_agent_card():
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(token='fixture')),
                                     base_url='http://test') as c:
            assert (await c.get('/.well-known/agent-card.json')).status_code == 401
            card = (await c.get('/.well-known/agent-card.json', headers=HEADERS)).json()
            assert card['supportedInterfaces'][0]['protocolBinding'] == 'HTTP+JSON'
            assert card['securityRequirements']
    asyncio.run(run())


def test_task_artifact_polling_and_same_context_followup():
    async def backend(text):
        return {'verdict': 'pass', 'summary': text, 'findings': [], 'limits': ['fixture only']}

    async def run():
        app = create_app(backend=backend, token='fixture')
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test', headers=HEADERS) as c:
            task = (await c.post('/message:send', json=message())).json()['task']
            assert task['status']['state'] == 'TASK_STATE_COMPLETED'
            assert task['artifacts'][0]['name'] == 'review.json'
            readback = (await c.get('/tasks/' + task['id'])).json()
            assert readback['id'] == task['id']
            followup = (await c.post('/message:send', json=message('recheck', task['contextId']))).json()['task']
            assert followup['id'] != task['id']
            assert followup['contextId'] == task['contextId']
    asyncio.run(run())


def test_worker_failure_is_failed_task_not_fabricated_review():
    async def backend(text):
        raise RuntimeError('fixture failure')

    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(backend=backend, token='fixture')),
                                     base_url='http://test', headers=HEADERS) as c:
            task = (await c.post('/message:send', json=message())).json()['task']
            assert task['status']['state'] == 'TASK_STATE_FAILED'
            assert not task.get('artifacts')
            assert 'fixture failure' not in str(task)
    asyncio.run(run())


def test_oversize_request_rejected_before_model_call():
    async def backend(text):
        pytest.fail('must not invoke backend')

    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(backend=backend, token='fixture')),
                                     base_url='http://test', headers=HEADERS) as c:
            assert (await c.post('/message:send', json=message('x' * 200_001))).status_code == 413
    asyncio.run(run())


def test_async_task_can_be_cancelled_without_model_retry():
    cancelled = []

    async def backend(text):
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.append(True)

    async def run():
        app = create_app(backend=backend, token='fixture')
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test', headers=HEADERS) as c:
            payload = {**message(), 'configuration': {'returnImmediately': True}}
            task = (await c.post('/message:send', json=payload)).json()['task']
            response = await c.post('/tasks/' + task['id'] + ':cancel', json={})
            assert response.status_code == 200
            state = (await c.get('/tasks/' + task['id'])).json()['status']['state']
            assert state == 'TASK_STATE_CANCELED'
            assert cancelled == [True]
    asyncio.run(run())
