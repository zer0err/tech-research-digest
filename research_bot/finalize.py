from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from .core import Item, load_state, send_telegram, update_state


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pending", default="work/pending.json")
    parser.add_argument("--state", default="state/seen.json")
    args = parser.parse_args()
    pending = json.loads(Path(args.pending).read_text())
    items = [Item(**raw) for raw in pending["items"]]
    count = len(items) if pending["topic"] != "daily_digest" else int(pending.get("published_count", 0))
    if count <= 0:
        raise ValueError("Refusing to notify or finalize empty content")
    if pending.get("notify", True):
        label = "篇有效简报" if pending["topic"] == "daily_digest" else "项新内容"
        send_telegram(f"{pending['title']}｜{count} {label}\n完整内容：{pending['url']}")
    state_path = Path(args.state)
    state = load_state(state_path)
    update_state(state, pending["topic"], items, datetime.fromisoformat(pending["created_at"]))
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
