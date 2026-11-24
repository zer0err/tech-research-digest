"""Local decision logs for independent topic previews."""
import json
import logging
from pathlib import Path


def decision(slot: str, reason: str, **details) -> None:
    record = {"slot": slot, "reason": reason, **details}
    Path("reports").mkdir(exist_ok=True)
    Path(f"reports/decision-{slot}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    logging.info("Publication decision: %s", json.dumps(record, ensure_ascii=False))
