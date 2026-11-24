"""Current rotation timing and durable per-edition publication receipts."""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

LEDGER = Path("state/slots.json")
EDITORIAL_PATH = Path(__file__).resolve().parent.parent / "config" / "editorial.yml"
def load_editorial(path: Path = EDITORIAL_PATH) -> dict:
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict) or not isinstance(data.get("slots"), dict) or not data["slots"]:
        raise ValueError("Invalid editorial schedule")
    for name, slot in data["slots"].items():
        if not isinstance(slot, dict) or not isinstance(slot.get("time"), str):
            raise ValueError(f"Editorial slot {name} needs a publication time")
    return data


def publication_zone(data: dict | None = None) -> ZoneInfo:
    name = str((data or {}).get("timezone") or "Asia/Taipei")
    return ZoneInfo(name)


EDITORIAL = load_editorial()
ZONE = publication_zone(EDITORIAL)
ROTATION_START = date.fromisoformat(str(EDITORIAL.get("rotation_start_date", date.max)))
ROTATION_HOURS = tuple(int(hour) for hour in EDITORIAL.get("rotation_batch_hours", [9, 13, 17]))
ROTATION_ASSEMBLY_HOUR = int(EDITORIAL.get("rotation_assembly_hour", 18))
TIMES = {name: str(slot["time"]) for name, slot in EDITORIAL["slots"].items()}


def daily_planned_time(day: date) -> str:
    return f"{ROTATION_ASSEMBLY_HOUR:02d}:00" if day >= ROTATION_START else TIMES["daily_report"]


def key(slot: str, now: datetime) -> str:
    return f"{now.astimezone(ZONE):%Y-%m-%d}:{slot}"


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


def is_due(slot: str, now: datetime) -> bool:
    return now.astimezone(ZONE).strftime("%H:%M") >= TIMES[slot]


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
