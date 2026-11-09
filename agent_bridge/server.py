"""Authenticated, loopback-only A2A 1.0 reviewer backed by real Codex execution."""
from __future__ import annotations

import asyncio
import json
import secrets
from pathlib import Path

import uvicorn
from a2a.helpers import new_task_from_user_message, new_text_message, new_text_part
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_rest_routes
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types.a2a_pb2 import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
    HTTPAuthSecurityScheme,
    SecurityRequirement,
    SecurityScheme,
    TaskState,
)
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .backend import review

ADDRESS = 'http://127.0.0.1:8787'
TOKEN_FILE = Path.home() / '.config/vorasio-a2a/token'


def local_token() -> str:
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not TOKEN_FILE.exists():
        TOKEN_FILE.write_text(secrets.token_urlsafe(32))
    TOKEN_FILE.chmod(0o600)
    token = TOKEN_FILE.read_text().strip()
    if len(token) < 32:
        raise RuntimeError('Local A2A token is invalid; replace it before starting')
    return token


class Reviewer(AgentExecutor):
    def __init__(self, backend=review):
        self.backend = backend
        self.lock = asyncio.Semaphore(1)

    async def execute(self, context: RequestContext, event_queue) -> None:
        task = context.current_task or new_task_from_user_message(context.message)
        await event_queue.enqueue_event(task)
        updater = TaskUpdater(event_queue, task.id, task.context_id)
        await updater.start_work()
        try:
            async with self.lock:
                result = await self.backend(context.get_user_input())
            await updater.add_artifact([new_text_part(json.dumps(result, ensure_ascii=False))], name='review.json')
            await updater.complete()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            await updater.update_status(TaskState.TASK_STATE_FAILED, new_text_message(type(exc).__name__))

    async def cancel(self, context: RequestContext, event_queue) -> None:
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        await updater.update_status(TaskState.TASK_STATE_CANCELED)


def create_app(*, backend=review, token: str | None = None) -> Starlette:
    token = token or local_token()
    card = AgentCard(
        name='VORASIO Independent Reviewer', version='0.1.0',
        description='Read-only AI platform review; Codex backend, no publication or message delivery.',
        supported_interfaces=[AgentInterface(url=ADDRESS, protocol_binding='HTTP+JSON', protocol_version='1.0')],
        capabilities=AgentCapabilities(streaming=False, push_notifications=False),
        default_input_modes=['text/plain'], default_output_modes=['application/json'],
        skills=[AgentSkill(id='platform-review', name='Platform implementation review',
                          description='Review evidence, report grounded defects and verification gaps.', tags=['review', 'ai-platform'])],
        security_schemes={'localBearer': SecurityScheme(http_auth_security_scheme=HTTPAuthSecurityScheme(scheme='bearer'))},
        security_requirements=[SecurityRequirement(schemes={'localBearer': {'list': []}})],
    )
    handler = DefaultRequestHandler(agent_executor=Reviewer(backend), task_store=InMemoryTaskStore(), agent_card=card)
    app = Starlette(routes=create_agent_card_routes(card) + create_rest_routes(handler))

    async def authenticate(request, call_next):
        header = request.headers.get('authorization', '')
        supplied = header.removeprefix('Bearer ')
        if not header.startswith('Bearer ') or not secrets.compare_digest(supplied, token):
            return JSONResponse({'error': 'unauthorized'}, status_code=401)
        if request.method == 'POST' and len(await request.body()) > 200_000:
            return JSONResponse({'error': 'request too large'}, status_code=413)
        return await call_next(request)

    app.add_middleware(BaseHTTPMiddleware, dispatch=authenticate)
    return app


def main() -> None:
    uvicorn.run(create_app(), host='127.0.0.1', port=8787, log_level='info')


if __name__ == '__main__':
    main()
