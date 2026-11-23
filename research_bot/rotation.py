"""VORASIO B: three durable domain slots and one daily publisher.

The Actions runner is the single writer. Receipts are also the deploy/delivery
handoff, so an interrupted job does not regenerate an already sealed edition.
"""
from __future__ import annotations

import argparse
import json
import logging
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path

from . import schedule
from .daily import TOPIC, canonical_name, markdown_sections, public_origin, render_daily_page
from .domain_report import MODULES
from .provenance import metadata

HOURS = schedule.ROTATION_HOURS
ASSEMBLY_HOUR = schedule.ROTATION_ASSEMBLY_HOUR
STATE = Path("state/rotation")
INDEX = Path("docs/posts.json")
PENDING = Path("work/pending.json")
DEPLOY_REQUIRED = Path("work/deploy-required")
STATUS_DEPLOY_REQUIRED = Path("work/status-deploy-required")
SOFT_FAILURES = {"source_failure", "analysis_api_failure", "analysis_rejected", "invalid_draft"}
RETRY_DELAY = timedelta(minutes=30)
MAX_ATTEMPTS = 2
RECOVERY_DAYS = 7


def stamp(day: date, hour: int) -> datetime:
    return datetime.combine(day, time(hour), schedule.ZONE)


def slots(day: date) -> list[tuple[int, str]]:
    offset = (day - schedule.ROTATION_START).days * len(HOURS)
    domains = tuple(MODULES)
    return [(hour, domains[(offset + i) % len(domains)]) for i, hour in enumerate(HOURS)]


def read(path: Path, default):
    return json.loads(path.read_text()) if path.exists() else default


def write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    temp.replace(path)


def state_for(day: date) -> dict:
    return read(STATE / f"{day}.json", {"day": day.isoformat(), "status": "drafting", "slots": {}})


def save(record: dict) -> None:
    write(STATE / f"{date.fromisoformat(record['day'])}.json", record)


def has_edition(day: date, entries: list[dict]) -> bool:
    return any(entry.get("topic") == TOPIC and entry.get("url") == canonical_name(str(day))
               and entry.get("status") == "published" for entry in entries)


def recoverable(day: date):
    for n in range(RECOVERY_DAYS + 1):
        previous = day - timedelta(days=n)
        if previous < schedule.ROTATION_START:
            continue
        receipt = state_for(previous)
        if receipt["status"] in {"prepared", "deployed"}:
            yield receipt


def eligible_batch(row: dict, now: datetime) -> bool:
    if not row:
        return True
    return (row["status"] in SOFT_FAILURES and row["attempts"] < MAX_ATTEMPTS
            and now >= datetime.fromisoformat(row["finished_at"]) + RETRY_DELAY)


def plan(now: datetime, entries: list[dict] | None = None) -> list[str]:
    now = now.astimezone(schedule.ZONE)
    day = now.date()
    if day < schedule.ROTATION_START:
        return []
    recover = next(recoverable(day), None)
    if recover:
        return [f"resume:{recover['day']}"]
    record = state_for(day)
    if record["status"] != "drafting" or has_edition(day, entries if entries is not None else read(INDEX, [])):
        return []
    if now >= stamp(day, ASSEMBLY_HOUR):
        return ["assemble"]
    return [f"{hour:02d}" for hour, _ in slots(day) if now >= stamp(day, hour)
            and eligible_batch(record["slots"].get(f"{hour:02d}", {}), now)]


def item_keys(item: dict) -> set[str]:
    from .daily import identity_keys

    explicit = {a for a in item.get("aliases", []) if a.startswith(("doi:", "arxiv:", "url:"))}
    key = item.get("uid")
    return identity_keys(item.get("url", ""), item.get("doi", "")) | explicit | ({key} if key else set())


def reserve(items: list[dict], blocked: set[str]) -> bool:
    fresh = set()
    for item in items:
        keys = item_keys(item)
        if not item.get("url", "").startswith("https://") or not keys or keys & (blocked | fresh):
            return False
        published = datetime.fromisoformat(item["published"])
        if published.tzinfo is None:
            return False
        fresh |= keys
    blocked.update(fresh)
    return bool(fresh)


def history_keys() -> set[str]:
    from .core import load_state, seen_identities

    state = load_state(Path("state/seen.json"))
    keys = seen_identities(state)
    # A canonical issue may be committed even though delivery state has not
    # been finalized. Its provenance is still part of the public history.
    for entry in read(INDEX, []):
        for source in (entry.get("provenance") or {}).get("sources", []):
            keys |= item_keys(source)
    return keys


def accepted(record: dict) -> list[dict]:
    return [row["result"] for _, row in sorted(record["slots"].items()) if row["status"] == "prepared"]


def make_pending(record: dict) -> None:
    pending = dict(record["pending"])
    pending["notify"] = pending.get("notify", True) and not bool(record.get("notification_claim"))
    write(PENDING, pending)
    if record["status"] == "prepared":
        DEPLOY_REQUIRED.touch()


def summarize(rows: list[dict]) -> str:
    from .daily import visible_text

    label = "、".join(row["title"] for row in rows)
    return visible_text(f"本期收录：{label}。按领域查看简报与原始来源。")[:160]


def seal_empty(now: datetime, record: dict) -> None:
    from .public_status import export

    record.update(status="sealed_empty", sealed_at=now.isoformat())
    schedule.record(TOPIC, now, "empty_digest")
    save(record)
    export()
    STATUS_DEPLOY_REQUIRED.parent.mkdir(parents=True, exist_ok=True)
    STATUS_DEPLOY_REQUIRED.touch()


def assemble(now: datetime, record: dict) -> None:
    from .site import render_index
    from .rotation_collect import generate_other

    day = date.fromisoformat(record["day"])
    scheduled = stamp(day, ASSEMBLY_HOUR)
    rows = accepted(record)
    if not rows:
        seal_empty(now, record)
        return

    blocked = history_keys()
    confirmed = []
    for row in rows:
        # If another publication has used any source since this draft was
        # generated, omit the section wholesale rather than orphan its claims.
        if reserve(row["items"], blocked):
            confirmed.append(row)
    if not confirmed:
        seal_empty(now, record)
        return

    used = {row["topic"] for row in confirmed}
    missing = [MODULES[domain] for _, domain in slots(day) if domain not in used]
    try:
        other = generate_other(scheduled, set(blocked))
        if other.get("ok") and reserve(other["items"], blocked):
            confirmed.append(other)
    except (ValueError, KeyError, TypeError, OSError):
        logging.warning("Optional Other evidence was unusable; no Other section added")
    items = [item for row in confirmed for item in row["items"]]
    flavor = [row.get("analysis") or {} for row in confirmed]
    analysis = {key: "、".join(dict.fromkeys(value[key] for value in flavor if value.get(key))) or "未记录"
                for key in ("provider", "model")}
    provenance = metadata(items, analysis)
    sections = markdown_sections(confirmed)
    for section, row in zip(sections, confirmed):
        section["kicker"] = "领域简报" if row["topic"] != "other" else "补充"
    path = canonical_name(str(day))
    title = f"VORASIO AI 日报（{day}）"
    disclosure = "每批只处理一个领域。采集截止为各批计划时刻，晚于截止的资料不纳入该批。"
    if missing:
        disclosure += "本期未收录：" + "、".join(missing) + "。"
    page = render_daily_page(title, now, sections, provenance["sources"], analysis, disclosure, path,
                             scheduled_at=scheduled)
    target = Path("docs") / path
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(page)
    entry = {
        "title": title, "date": now.isoformat(), "scheduled_at": scheduled.isoformat(),
        "rotation": "B", "count": len(provenance["sources"]), "url": path, "topic": TOPIC,
        "status": "published", "summary": summarize(confirmed), "provenance": provenance,
        "sections": [{k: section[k] for k in ("topic", "source_topic", "title", "anchor")} for section in sections],
    }
    entries = read(INDEX, [])
    entries.insert(0, entry)
    entries.sort(key=lambda old: str(old.get("date") or ""), reverse=True)
    render_index(entries)
    pending = {
        "topic": TOPIC, "slot": TOPIC, "title": title, "url": f"{public_origin()}/{path}",
        "created_at": now.isoformat(), "scheduled_at": scheduled.isoformat(),
        "items": items, "published_count": entry["count"], "notify": True, "mode": "production",
        "analysis": analysis, "source_topic": TOPIC, "rotation": "B",
    }
    record.update(status="prepared", sealed_at=now.isoformat(), pending=pending)
    schedule.record(TOPIC, now, "prepared", pending)
    save(record)
    make_pending(record)


def tick(now: datetime | None = None, *, clock=None) -> None:
    if clock is None:
        clock = lambda: datetime.now(UTC)
    now = (now or clock()).astimezone(schedule.ZONE)
    day = now.date()
    PENDING.unlink(missing_ok=True)
    DEPLOY_REQUIRED.unlink(missing_ok=True)
    STATUS_DEPLOY_REQUIRED.unlink(missing_ok=True)
    if day < schedule.ROTATION_START:
        return
    recover = next(recoverable(day), None)
    if recover:
        make_pending(recover)
        return
    record = state_for(day)
    if record["status"] != "drafting" or has_edition(day, read(INDEX, [])):
        return
    close = stamp(day, ASSEMBLY_HOUR)
    if now >= close:
        assemble(now, record)
        return

    from .rotation_collect import generate

    blocked = history_keys()
    for row in accepted(record):
        blocked.update(key for item in row["items"] for key in item_keys(item))
    for hour, domain in slots(day):
        current = max(now, clock().astimezone(schedule.ZONE))
        key = f"{hour:02d}"
        old = record["slots"].get(key, {})
        cutoff = stamp(day, hour)
        if current < cutoff or current >= close or not eligible_batch(old, current):
            continue
        result = generate(domain, cutoff, set(blocked))
        finished = max(current, clock().astimezone(schedule.ZONE))
        status = result.get("reason", "invalid_draft")
        if finished >= close:
            status = "missed_deadline"
        elif result.get("ok"):
            if result.get("topic") == domain and result.get("report") and reserve(result["items"], blocked):
                status = "prepared"
                result["items"] = [{**item, "summary": ""} for item in result["items"]]
            else:
                status = "invalid_draft"
        elif status == "prepared":
            status = "invalid_draft"
        record["slots"][key] = {
            "domain": domain, "cutoff": cutoff.isoformat(), "finished_at": finished.isoformat(),
            "status": status, "attempts": old.get("attempts", 0) + 1,
            **({"result": result} if status == "prepared" else {}),
        }
        save(record)
    finished = max(now, clock().astimezone(schedule.ZONE))
    if close <= finished and finished.date() == day:
        assemble(finished, record)


def transition(action: str, now: datetime) -> None:
    pending = read(PENDING, {})
    day = datetime.fromisoformat(pending["created_at"]).astimezone(schedule.ZONE).date()
    record = state_for(day)
    # A mismatched/stale pending file must not authorize publication or send.
    if record.get("pending", {}).get("url") != pending.get("url"):
        raise ValueError("Rotation pending receipt mismatch")
    if action == "deployed":
        if record["status"] == "prepared":
            record.update(status="deployed", deployed_at=now.isoformat())
            save(record)
        elif record["status"] != "deployed":
            raise ValueError("Edition not prepared")
        DEPLOY_REQUIRED.unlink(missing_ok=True)
    elif action == "claim":
        if record["status"] != "deployed":
            raise ValueError("Cannot claim notification before Pages deployment")
        if (record.get("notification_claim") or not pending.get("notify")
                or now.astimezone(schedule.ZONE).date() != day):
            pending["notify"] = False
            write(PENDING, pending)
            return
        # Persist and push BEFORE making the request. An ambiguous/interrupted
        # send is not retried automatically (prefer one missed send to two).
        if now < stamp(day, ASSEMBLY_HOUR):
            raise ValueError("Edition is not due")
        record["notification_claim"] = now.isoformat()
        save(record)
    elif action == "finalized":
        if record["status"] != "deployed":
            raise ValueError("Cannot finalize before Pages deployment")
        ledger = schedule.load()["slots"]
        if ledger.get(schedule.key(TOPIC, datetime.fromisoformat(pending["created_at"])), {}).get("status") != "published":
            raise ValueError("Publication ledger has not been finalized")
        record.update(status="finalized", finalized_at=now.isoformat())
        # Retain audit metadata, not full duplicate draft data, in current tree.
        for row in record["slots"].values():
            row.pop("result", None)
        record.pop("pending", None)
        save(record)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    for action in ("plan", "tick", "mark-deployed", "claim-notification", "mark-finalized"):
        group.add_argument("--" + action, dest="action", action="store_const", const=action)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    now = datetime.now(UTC)
    if args.action == "plan":
        print(json.dumps(plan(now)))
    elif args.action == "tick":
        tick(now)
    else:
        transitions = {"mark-deployed": "deployed", "claim-notification": "claim", "mark-finalized": "finalized"}
        transition(transitions[args.action], now)


if __name__ == "__main__":
    main()
