from __future__ import annotations

import argparse
import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from .core import collect, dump_items, groq_analyse, load_state, unseen
from .site import publish_post


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True, choices=["ai_papers", "ai_agents", "audio", "edge_ai"])
    parser.add_argument("--config", default="config/sources.yml")
    parser.add_argument("--state", default="state/seen.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(levelname)s %(message)s")
    now = datetime.now(UTC)
    config = yaml.safe_load(Path(args.config).read_text())["topics"][args.topic]
    state_path = Path(args.state)
    state = load_state(state_path)
    candidates = collect(config, now)
    selected = unseen(candidates, state, args.topic)[: int(config["max_items"])]
    if not selected:
        logging.info("No unseen in-window items for %s", args.topic)
        return 0
    if args.dry_run:
        print(json.dumps(dump_items(selected), ensure_ascii=False, indent=2))
        return 0
    report = groq_analyse(config["title"], selected)
    header = f"{config['title']}｜{now.astimezone(ZoneInfo('Asia/Shanghai')).strftime('%Y-%m-%d')}｜{len(selected)} 项\n\n"
    public_url = publish_post(args.topic, config["title"], now, report, selected)
    Path("reports").mkdir(exist_ok=True)
    Path(f"reports/{args.topic}-{now:%Y%m%dT%H%M%SZ}.md").write_text(header + report)
    Path("work").mkdir(exist_ok=True)
    Path("work/pending.json").write_text(
        json.dumps(
            {
                "topic": args.topic,
                "title": config["title"],
                "url": public_url,
                "created_at": now.isoformat(),
                "items": dump_items(selected),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
