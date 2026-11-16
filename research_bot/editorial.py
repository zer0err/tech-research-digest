from __future__ import annotations

import argparse
import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from . import schedule
from .audit import decision
from .daily import TOPIC, prepare_daily_report

BEIJING = ZoneInfo("Asia/Taipei")


def prepare_daily_digest(now: datetime, notify: bool = True) -> bool:
    """Compatibility name. Empty editions are not published and are not announced."""
    del notify
    return prepare_daily_report(now)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slot", required=True)
    parser.add_argument("--editorial-config", default="config/editorial.yml")
    parser.add_argument("--sources-config", default="config/sources.yml")
    parser.add_argument("--state", default="state/seen.json")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--replay-date", default="", help="Explicit past Asia/Taipei edition date; preserve existing articles")
    args = parser.parse_args()
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(levelname)s %(message)s")
    now = datetime.now(UTC)
    replay = bool(args.replay_date)
    if replay:
        edition = datetime.strptime(args.replay_date, "%Y-%m-%d").replace(hour=23, minute=59, tzinfo=BEIJING)
        if edition.date() >= now.astimezone(BEIJING).date():
            raise ValueError("Replay date must be a past Asia/Taipei date")
        now = edition.astimezone(UTC)
        os.environ["REPLAY_EDITION_DATE"] = args.replay_date
    editorial = yaml.safe_load(Path(args.editorial_config).read_text())
    slot = (editorial.get("slots") or {}).get(args.slot)
    if not slot or args.slot != TOPIC or slot.get("special") != "daily_report":
        Path("work/pending.json").unlink(missing_ok=True)
        decision(args.slot, "retired_slot")
        return 0
    production = os.getenv("PUBLICATION_MODE", "production") == "production" and not args.dry_run
    if production:
        Path("work/pending.json").unlink(missing_ok=True)
        if not schedule.is_due(args.slot, now):
            decision(args.slot, "not_due_yet", timezone="Asia/Taipei", planned_time=schedule.TIMES[args.slot])
            return 0
        ledger = schedule.load()
        entries = json.loads(Path("docs/posts.json").read_text()) if Path("docs/posts.json").exists() else []
        receipt = ledger["slots"].get(schedule.key(args.slot, now), {})
        if replay and any(e.get("topic") == args.slot and e.get("execution_date", str(e.get("date", ""))[:10]) == args.replay_date
                          and e.get("status") == "published" for e in entries):
            decision(args.slot, "existing_article_preserved", edition_date=args.replay_date)
            return 0
        if receipt.get("status") == "prepared":
            Path("work").mkdir(exist_ok=True)
            Path("work/pending.json").write_text(json.dumps(receipt["pending"], ensure_ascii=False, indent=2) + "\n")
            decision(args.slot, "resume_prepared_publication")
            return 0
        if not replay and not schedule.eligible(args.slot, now, ledger, entries):
            decision(args.slot, "slot_already_completed_or_retry_limited")
            return 0
    def persist_result() -> None:
        if not production:
            return
        pending_path = Path("work/pending.json")
        if pending_path.exists():
            pending = json.loads(pending_path.read_text())
            pending["slot"] = args.slot
            if replay:
                pending["replay_date"] = args.replay_date
            pending_path.write_text(json.dumps(pending, ensure_ascii=False, indent=2) + "\n")
            schedule.record(args.slot, now, "prepared", pending, observed_at=datetime.now(UTC) if replay else None)
        else:
            audit = Path(f"reports/decision-{args.slot}.json")
            result = json.loads(audit.read_text()) if audit.exists() else {}
            schedule.record(args.slot, now, result.get("reason", "analysis_rejected"), observed_at=datetime.now(UTC) if replay else None)
    if args.dry_run:
        prepare_daily_report(now, dry_run=True, sources_path=Path(args.sources_config))
        return 0
    prepare_daily_report(now, sources_path=Path(args.sources_config))
    persist_result()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
