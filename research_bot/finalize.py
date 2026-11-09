from __future__ import annotations

import argparse
import json
import logging
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
    if count <= 0 and pending["topic"] != "daily_digest":
        raise ValueError("Refusing to notify or finalize empty content")
    state_path = Path(args.state)
    state = load_state(state_path)
    now = datetime.now(UTC)
    edition = datetime.fromisoformat(pending["created_at"])
    today = now.astimezone(schedule.BEIJING).date().isoformat()
    receipts = state.setdefault("daily_notifications", {})
    notify = (
        pending["topic"] == "daily_digest"
        and pending.get("notify", True)
        and not pending.get("replay_date")
        and edition.astimezone(schedule.BEIJING).date().isoformat() == today
        and schedule.is_due("daily_digest", now)
        and today not in receipts
    )
    if pending["topic"] == "daily_digest" and pending.get("notify", True) and not pending.get("replay_date"):
        if edition.astimezone(schedule.BEIJING).date().isoformat() == today and not schedule.is_due("daily_digest", now):
            raise ValueError("Daily notification cannot be delivered before 19:00 Asia/Shanghai")
    if notify:
        message = (f"{pending['title']}｜{count} 篇有效简报\n完整内容：{pending['url']}" if count
                   else f"{pending['title']}｜今日暂无有效新内容\n每日状态：{pending['url']}")
        send_telegram(message)
        # Save Telegram success before optional delivery so its failure cannot repeat Telegram.
        receipts[today] = {"sent_at": now.isoformat(), "url": pending["url"]}
        state["daily_notifications"] = dict(sorted(receipts.items(), reverse=True)[:400])
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")
        try:
            send_ntfy(message, title=str(pending["title"]), click_url=str(pending["url"]))
        except Exception:
            logging.exception("Optional ntfy delivery failed; see Actions logs")
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
