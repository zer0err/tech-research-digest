"""Local run decisions, uploaded for audit but never used as publication content."""
import json
import logging
import re
from pathlib import Path


def decision(slot: str, reason: str, **details) -> None:
    record = {"slot": slot, "reason": reason, **details}
    Path("reports").mkdir(exist_ok=True)
    Path(f"reports/decision-{slot}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    logging.info("Publication decision: %s", json.dumps(record, ensure_ascii=False))


def public_summaries(source: Path = Path("reports"), output: Path = Path("work/public-audit")) -> None:
    """Export bounded decision metadata, excluding raw drafts and diagnostic text."""
    output.mkdir(parents=True, exist_ok=True)
    for stale in output.glob("decision-*.json"):
        stale.unlink()
    for path in source.glob("decision-*.json"):
        try:
            record = json.loads(path.read_text())
        except (ValueError, OSError):
            continue
        if not isinstance(record, dict):
            continue
        summary = {}
        for key in ("slot", "reason", "mode"):
            value = record.get(key)
            if isinstance(value, str) and re.fullmatch(r"[a-z0-9_-]{1,80}", value):
                summary[key] = value
        for key in ("collected", "usable", "already_published", "unpublished", "selected"):
            value = record.get(key)
            if type(value) is int and value >= 0:
                summary[key] = value
        if "slot" in summary and "reason" in summary:
            (output / path.name).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    public_summaries()
