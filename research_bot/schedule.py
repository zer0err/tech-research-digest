"""Same-day catch-up planning and persistent per-slot publication receipts."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

BEIJING = ZoneInfo("Asia/Shanghai")
LEDGER = Path("state/slots.json")
EDITORIAL_PATH = Path(__file__).resolve().parent.parent / "config" / "editorial.yml"
# Statuses that mean "nothing was published, but a later pass the same day may find new items".
SOFT_EMPTY = {"already_published", "no_matching_in_window"}
# Statuses that close the slot for the rest of the Beijing day.
TERMINAL = {"published", "insufficient_abstract", "empty_digest"}


def load_editorial(path: Path = EDITORIAL_PATH) -> dict:
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict) or not isinstance(data.get("slots"), dict) or not data["slots"]:
        raise ValueError("Invalid editorial schedule")
    for name, slot in data["slots"].items():
        if not isinstance(slot, dict) or not isinstance(slot.get("time"), str):
            raise ValueError(f"Editorial slot {name} needs a Beijing time")
    return data


EDITORIAL = load_editorial()
TIMES = {name: str(slot["time"]) for name, slot in EDITORIAL["slots"].items()}
EMPTY_RESCAN = timedelta(minutes=int(EDITORIAL.get("empty_rescan_minutes", 180)))
FAILURE_RETRY = timedelta(minutes=int(EDITORIAL.get("failure_retry_minutes", 60)))
MAX_ATTEMPTS = int(EDITORIAL.get("max_attempts", 3))


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
    if record.get("status") in TERMINAL:
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
    if int(record.get("attempts", 0)) >= MAX_ATTEMPTS:
        return False
    status = record.get("status")
    updated = record.get("updated_at")
    # A same-day empty receipt without a timestamp must not spin on every catch-up.
    if status in SOFT_EMPTY and not updated:
        return False
    cooldown = EMPTY_RESCAN if status in SOFT_EMPTY else FAILURE_RETRY
    if updated and now - datetime.fromisoformat(updated) < cooldown:
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
