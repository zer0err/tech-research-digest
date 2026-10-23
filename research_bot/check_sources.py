"""Read-only connector health check: never calls Groq or publishes content."""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import yaml

from .sources import fetch_entries


def main() -> None:
    topics = yaml.safe_load(Path("config/sources.yml").read_text())["topics"]
    selected = {}
    for topic in topics.values():
        for source in topic["sources"]:
            kind = source.get("type", "rss")
            if kind != "rss" or source["name"] == "NVIDIA Technical Blog":
                selected.setdefault(kind if kind != "rss" else "nvidia", source)
    now = datetime.now(UTC)
    results = []
    with httpx.Client(timeout=40, follow_redirects=True, headers={"User-Agent": "Vorasio-Source-Check/1.0"}) as client:
        for kind, source in selected.items():
            probe = {**source, "limit": 2}
            cutoff = now - timedelta(days=730 if kind in {"acl", "cvf"} else 30)
            try:
                entries = fetch_entries(probe, client, now, cutoff)
                result = {"connector": kind, "ok": True, "received": len(entries),
                          "with_abstract": sum(bool(entry.get("summary")) for entry in entries)}
            except Exception as exc:
                # Never stringify HTTP exceptions: request URLs or credentials may be present.
                result = {"connector": kind, "ok": False, "error": type(exc).__name__}
                if isinstance(exc, httpx.HTTPStatusError):
                    result["status"] = exc.response.status_code
            results.append(result)
            print(json.dumps(result))
    Path("work").mkdir(exist_ok=True)
    Path("work/source-check.json").write_text(json.dumps(results, indent=2) + "\n")
    if any(not result["ok"] for result in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
