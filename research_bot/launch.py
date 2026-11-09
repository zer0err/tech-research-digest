"""Verify an already deployed release and claim one Telegram launch delivery."""
from __future__ import annotations

import argparse
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree

import httpx

PAGES = ('', 'domains/index.html', 'subscribe.html', 'services.html', 'feed.xml')


def read_json(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def claim(config: dict, receipt_path: Path, sha: str, client: httpx.Client) -> bool:
    if config.get('enabled') is not True:
        return False
    campaign = config.get('campaign_id', '')
    base = config.get('base_url', '').rstrip('/')
    parsed = urlparse(base)
    if not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', campaign) or not re.fullmatch(r'[a-f0-9]{40}', sha):
        raise ValueError('Invalid campaign or deployment SHA')
    if base != 'https://vorasio.com':
        raise ValueError('Launch verification is restricted to the configured VORASIO site')
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Expected a public HTTPS site URL')
    receipts = read_json(receipt_path)
    if campaign in receipts:
        return False
    for page in PAGES:
        response = client.get(f'{base}/{page}', params={'platform_release': campaign})
        response.raise_for_status()
        if page == 'feed.xml':
            root = ElementTree.fromstring(response.content)
            if root.tag not in ('rss', '{http://www.w3.org/2005/Atom}feed'):
                raise ValueError('Invalid subscription feed')
        else:
            local = Path('docs') / (page or 'index.html')
            marker = f'data-platform-release="{campaign}"'
            if marker not in response.text or not local.exists() or marker not in local.read_text():
                raise ValueError('Deployed release does not match the checked-out release')
    receipts[campaign] = {'status': 'claimed', 'sha': sha, 'claimed_at': datetime.now(UTC).isoformat(), 'base_url': base}
    save(receipt_path, receipts)
    return True


def send(config: dict, receipt_path: Path, sha: str, client: httpx.Client) -> bool:
    campaign = config['campaign_id']
    receipts = read_json(receipt_path)
    receipt = receipts.get(campaign, {})
    if receipt.get('status') != 'claimed' or receipt.get('sha') != sha:
        return False
    # Only the original claim-owning workflow run may attempt this POST.
    owner = os.environ.get('GITHUB_RUN_ID', '')
    if receipt.get('run_id') != owner or not owner:
        return False
    token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    chat = os.environ.get('TELEGRAM_CHAT_ID', '')
    if not token or not chat:
        receipt['status'] = 'unknown'
        receipt['error'] = 'missing_delivery_configuration'
        save(receipt_path, receipts)
        return False
    # Mark unknown before the request: crashes/timeouts must never cause an automatic retry.
    receipt['status'] = 'unknown'
    receipt['attempted_at'] = datetime.now(UTC).isoformat()
    save(receipt_path, receipts)
    message = ('VORASIO AI 精选平台已更新：领域导航、RSS 订阅与开发需求整理工具已上线。'
               '\n可按 AI 领域阅读精选资讯，并整理 AI 软件或智能硬件开发需求。'
               f"\n浏览平台：{receipt['base_url']}/\n订阅精选：{receipt['base_url']}/subscribe.html")
    try:
        response = client.post(f'https://api.telegram.org/bot{token}/sendMessage',
                               json={'chat_id': chat, 'text': message, 'disable_web_page_preview': True})
        response.raise_for_status()
        payload = response.json()
        if payload.get('ok') is not True or not payload.get('result', {}).get('message_id'):
            return False
        receipt.update(status='sent', message_id=payload['result']['message_id'], sent_at=datetime.now(UTC).isoformat())
        save(receipt_path, receipts)
        return True
    except (httpx.HTTPError, ValueError, KeyError):
        # Do not log exception text: request URLs contain the Telegram credential.
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['claim', 'send'])
    parser.add_argument('--config', default='config/platform-launch.json')
    parser.add_argument('--receipt', default='state/platform-launch.json')
    parser.add_argument('--sha', required=True)
    args = parser.parse_args()
    config = read_json(Path(args.config))
    receipt = Path(args.receipt)
    with httpx.Client(timeout=25, follow_redirects=False) as client:
        if args.action == 'claim':
            claimed = claim(config, receipt, args.sha, client)
            if claimed:
                data = read_json(receipt)
                data[config['campaign_id']]['run_id'] = os.environ.get('GITHUB_RUN_ID', '')
                save(receipt, data)
            if output := os.environ.get('GITHUB_OUTPUT'):
                with Path(output).open('a') as stream:
                    stream.write(f'claimed={str(claimed).lower()}\n')
            return 0
        success = send(config, receipt, args.sha, client)
        print('Launch delivery confirmed.' if success else 'Launch delivery unconfirmed; automatic resend disabled.')
        return 0 if success else 1


if __name__ == '__main__':
    raise SystemExit(main())
