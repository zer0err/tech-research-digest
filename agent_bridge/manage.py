"""Install and control the current user's loopback A2A service."""
from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

from .backend import ROOT

SERVICE = 'vorasio-a2a.service'


def install() -> None:
    unit = Path.home() / '.config/systemd/user' / SERVICE
    unit.parent.mkdir(parents=True, exist_ok=True)
    # All values are local paths, not credentials; authentication stays in Codex's existing store.
    def quoted(value: str) -> str:
        return '"' + value.replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%') + '"'
    home = os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))
    unit.write_text(
        '[Unit]\nDescription=VORASIO local A2A reviewer\nAfter=network.target\n\n[Service]\nType=simple\n'
        f'WorkingDirectory={quoted(str(ROOT))}\n'
        f'ExecStart={quoted(str(ROOT / ".venv-a2a/bin/python"))} -m agent_bridge.server\n'
        f'Environment={quoted("CODEX_HOME=" + home)}\nEnvironment=PYTHONUNBUFFERED=1\n'
        'Restart=on-failure\nRestartSec=3\nTimeoutStopSec=10\n\n[Install]\nWantedBy=default.target\n'
    )
    keys = [key for key in ['SSL_CERT_FILE', 'SSL_CERT_DIR', 'HTTPS_PROXY', 'HTTP_PROXY', 'ALL_PROXY', 'NO_PROXY']
            if os.environ.get(key)]
    if keys:
        subprocess.run(['systemctl', '--user', 'import-environment', *keys], check=True)
    subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)
    subprocess.run(['systemctl', '--user', 'enable', '--now', SERVICE], check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['install', 'start', 'stop', 'status'])
    args = parser.parse_args()
    if args.action == 'install':
        install()
    else:
        subprocess.run(['systemctl', '--user', args.action, SERVICE], check=True)


if __name__ == '__main__':
    main()
