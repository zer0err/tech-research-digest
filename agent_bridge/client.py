"""Send an A2A task and poll its artifacts; preserve a local audit transcript."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from uuid import uuid4

import httpx

from .server import ADDRESS, TOKEN_FILE


def request_review(text: str, *, context_id: str | None = None, output: Path | None = None) -> dict:
    headers = {'Authorization': 'Bearer ' + TOKEN_FILE.read_text().strip(), 'A2A-Version': '1.0',
               'Content-Type': 'application/a2a+json'}
    transcript = []
    with httpx.Client(base_url=ADDRESS, headers=headers, timeout=30, trust_env=False) as client:
        response = client.get('/.well-known/agent-card.json')
        response.raise_for_status()
        card = response.json()
        message = {'messageId': str(uuid4()), 'role': 'ROLE_USER', 'parts': [{'text': text}]}
        if context_id:
            message['contextId'] = context_id
        response = client.post('/message:send', json={'message': message, 'configuration': {'returnImmediately': True}})
        response.raise_for_status()
        payload = response.json()
        task = payload.get('task', payload)
        if not task.get('id'):
            raise RuntimeError('A2A server did not return a task')
        transcript.append(task)
        def checkpoint() -> None:
            if output:
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(json.dumps(
                    {'agent': card['name'], 'task': task, 'transcript': transcript},
                    ensure_ascii=False, indent=2,
                ))
        checkpoint()
        deadline = time.monotonic() + 360
        terminal = {'TASK_STATE_COMPLETED', 'TASK_STATE_FAILED', 'TASK_STATE_CANCELED', 'TASK_STATE_REJECTED'}
        while task.get('status', {}).get('state') not in terminal:
            if time.monotonic() > deadline:
                raise TimeoutError(f'A2A polling deadline exceeded for task {task["id"]}; task not restarted')
            time.sleep(2)
            response = client.get('/tasks/' + task['id'])
            response.raise_for_status()
            task = response.json()
            if task != transcript[-1]:
                transcript.append(task)
                checkpoint()
        result = {'agent': card['name'], 'task': task, 'transcript': transcript}
        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(result, ensure_ascii=False, indent=2))
        if task['status']['state'] != 'TASK_STATE_COMPLETED':
            raise RuntimeError(f'A2A task {task["id"]} ended with {task["status"]["state"]}')
        return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--context-id')
    parser.add_argument('--output', type=Path, default=Path('outputs/a2a/latest.json'))
    args = parser.parse_args()
    result = request_review(args.input.read_text(), context_id=args.context_id, output=args.output)
    print(json.dumps(result['task'], ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
