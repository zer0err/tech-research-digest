"""Publish only safe receipt metadata, never pending payloads or source credentials."""
import json
from pathlib import Path

from .schedule import load


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
    export()
    render_index(json.loads(Path("docs/posts.json").read_text()))
