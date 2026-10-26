"""Same-day catch-up planning and persistent per-slot publication receipts."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

BEIJING = ZoneInfo("Asia/Shanghai")
LEDGER = Path("state/slots.json")
TIMES = {
    "morning_radar": "09:07", "model_research": "10:17", "open_source": "11:27", "paper_brief": "12:37",
    "prompt_engineering": "13:47", "core_research": "14:07", "dev_practice": "15:17", "applied_ai": "16:27",
    "ecosystem": "17:37", "daily_digest": "18:47",
}


def key(slot: str, now: datetime) -> str:
    return f"{now.astimezone(BEIJING):%Y-%m-%d}:{slot}"


def load() -> dict:
    if not LEDGER.exists():
        return {"version": 1, "slots": {}}
    data = json.loads(LEDGER.read_text())
    if data.get("version") != 1 or not isinstance(data.get("slots"), dict):
        raise ValueError("Invalid slot ledger")
    return data


def save(data: dict) -> None:
    LEDGER.parent.mkdir(exist_ok=True)
    # Bound state while retaining enough receipts to explain recent publication decisions.
    data["slots"] = dict(sorted(data["slots"].items(), reverse=True)[:600])
    LEDGER.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def completed(slot: str, now: datetime, ledger: dict, entries: list[dict]) -> bool:
    record = ledger["slots"].get(key(slot, now), {})
    if record.get("status") == "prepared":
        return False  # Resume deploy/notification instead of generating again.
    if record.get("status") in {"published", "no_matching_in_window", "insufficient_abstract", "already_published", "empty_digest"}:
        return True
    return any(entry.get("topic") == slot
               and str(entry.get("execution_date", entry.get("date", "")))[:10] == f"{now.astimezone(BEIJING):%Y-%m-%d}"
               and entry.get("status") == "published" and int(entry.get("count", 0)) > 0 for entry in entries)


def eligible(slot: str, now: datetime, ledger: dict, entries: list[dict]) -> bool:
    if completed(slot, now, ledger, entries):
        return False
    record = ledger["slots"].get(key(slot, now), {})
    if record.get("status") == "prepared":
        return True
    if int(record.get("attempts", 0)) >= 3:
        return False
    if record.get("updated_at") and now - datetime.fromisoformat(record["updated_at"]) < timedelta(minutes=60):
        return False
    return True


def is_due(slot: str, now: datetime) -> bool:
    return now.astimezone(BEIJING).strftime("%H:%M") >= TIMES[slot]


def due_slots(now: datetime, ledger: dict, entries: list[dict]) -> list[str]:
    return [slot for slot in TIMES if is_due(slot, now) and eligible(slot, now, ledger, entries)]


def record(slot: str, now: datetime, status: str, pending: dict | None = None, *, observed_at: datetime | None = None) -> None:
    data = load()
    previous = data["slots"].get(key(slot, now), {})
    data["slots"][key(slot, now)] = {
        "status": status, "updated_at": (observed_at or now).isoformat(),
        "attempts": int(previous.get("attempts", 0)) + (status != "published"),
    }
    if previous.get("maintenance_notified"):
        data["slots"][key(slot, now)]["maintenance_notified"] = True
    if pending:
        data["slots"][key(slot, now)]["pending"] = pending
    save(data)


def main() -> None:
    from datetime import UTC

    from .audit import decision
    now = datetime.now(UTC)
    entries = json.loads(Path("docs/posts.json").read_text()) if Path("docs/posts.json").exists() else []
    slots = due_slots(now, load(), entries)
    decision("catchup", "planned", due=slots, checked_at=now.isoformat())
    print(json.dumps(slots))


if __name__ == "__main__":
    main()
