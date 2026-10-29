from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from . import schedule
from .core import Item, load_state, send_ntfy, send_telegram, update_state


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pending", default="work/pending.json")
    parser.add_argument("--state", default="state/seen.json")
    args = parser.parse_args()
    pending = json.loads(Path(args.pending).read_text())
    if pending.get("mode", "production") != "production":
        raise ValueError("Test output cannot be published or added to production state")
    items = [Item(**raw) for raw in pending["items"]]
    count = len(items) if pending["topic"] != "daily_digest" else int(pending.get("published_count", 0))
    if count <= 0:
        raise ValueError("Refusing to notify or finalize empty content")
    if pending.get("notify", True):
        label = "篇有效简报" if pending["topic"] == "daily_digest" else "项新内容"
        message = f"{pending['title']}｜{count} {label}\n完整内容：{pending['url']}"
        send_telegram(message)
        try:
            send_ntfy(message, title=str(pending["title"]), click_url=str(pending["url"]))
        except Exception:
            # Telegram remains the maintenance channel if the optional ntfy delivery fails.
            send_telegram(f"【维护提醒，非内容推送】{pending['title']} 的 ntfy 推送失败，请检查 GitHub Actions。")
    state_path = Path(args.state)
    state = load_state(state_path)
    update_state(state, pending["topic"], items, datetime.fromisoformat(pending["created_at"]))
    if items:
        state.setdefault("publications", {})[pending["url"]] = {
            "topic": pending["topic"], "created_at": pending["created_at"], "items": pending["items"],
            "analysis": pending.get("analysis"),
        }
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    if pending.get("slot"):
        schedule.record(pending["slot"], datetime.fromisoformat(pending["created_at"]), "published",
                        observed_at=datetime.now(UTC) if pending.get("replay_date") else None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
