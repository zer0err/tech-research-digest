"""Publish only safe receipt metadata, never pending payloads or source credentials."""
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from .schedule import BEIJING, TIMES, load, save


def notify_maintenance() -> None:
    from .core import send_telegram
    ledger = load()
    now = datetime.now(UTC)
    today = now.astimezone(BEIJING).date().isoformat()
    for key, record in ledger["slots"].items():
        if not key.startswith(today + ':') or record.get("maintenance_notified"):
            continue
        status = record.get("status")
        failed = status in {"analysis_rejected", "source_failure", "analysis_api_failure"} and record.get("attempts", 0) >= 3
        updated = datetime.fromisoformat(record["updated_at"]).astimezone(BEIJING)
        planned = datetime.fromisoformat(today + 'T' + TIMES[key.split(':', 1)[1]]).replace(tzinfo=BEIJING)
        delayed = (updated - planned).total_seconds() > 3600
        if failed or delayed:
            send_telegram(f"【维护提醒，非内容推送】{key}：" + ("多次处理未通过，需检查。" if failed else "任务执行较计划延迟超过一小时。"))
            record["maintenance_notified"] = True
    save(ledger)


def export() -> dict:
    records = {
        key: {field: value for field, value in record.items()
              if field in {"status", "updated_at", "attempts"}}
        for key, record in load()["slots"].items()
    }
    Path("docs").mkdir(exist_ok=True)
    Path("docs/slot-status.json").write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n")
    return records


if __name__ == "__main__":
    from .site import render_index
    if os.getenv("NOTIFY_MAINTENANCE") == "true":
        notify_maintenance()
    export()
    render_index(json.loads(Path("docs/posts.json").read_text()))
