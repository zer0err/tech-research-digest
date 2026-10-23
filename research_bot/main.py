from __future__ import annotations

import argparse
import json
import logging
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from .core import collect, dump_items, fallback_report, groq_analyse, load_state, report_is_complete, unseen
from .site import publish_post


def prepare_topic(
    topic: str,
    config: dict[str, object],
    state_path: Path,
    now: datetime,
    dry_run: bool = False,
    publish_key: str | None = None,
    allow_empty: bool = False,
) -> bool:
    state = load_state(state_path)
    candidates = collect(config, now)
    candidates = [item for item in candidates if item.summary.strip() and item.url.startswith("https://")]
    fresh = unseen(candidates, state, topic)
    limit = int(config["max_items"])
    if config.get("content_type") == "radar":
        resources = [item for item in fresh if item.kind == "resource"][:2]
        regular = [item for item in fresh if item.kind != "resource"][: limit - len(resources)]
        selected = sorted(resources + regular, key=lambda item: item.published, reverse=True)
    else:
        selected = fresh[:limit]
    if not selected and not allow_empty:
        logging.info("No unseen in-window items for %s", topic)
        return False
    if dry_run:
        print(json.dumps(dump_items(selected), ensure_ascii=False, indent=2))
        return bool(selected)
    if selected:
        content_type = str(config.get("content_type", "research"))
        report = groq_analyse(
            str(config["title"]),
            str(config["analysis_focus"]),
            selected,
            content_type,
        )
        if not report_is_complete(report, selected, content_type):
            logging.warning("Model output for %s failed completeness checks; publishing source-only fallback", topic)
            report = fallback_report(selected, content_type)
    else:
        report = "## 本时段状态\n\n本时段未发现符合日期、相关性与去重条件的新资料。"
    if config.get("content_type") == "radar" and not any(item.kind == "resource" for item in selected):
        marker = "## 今日免费 VPS 与 AI 资源"
        replacement = f"{marker}\n\n今日未发现新的、可由公开来源确认的免费资源。"
        if marker in report:
            report = re.sub(r"## 今日免费 VPS 与 AI 资源.*?(?=\n## |\Z)", replacement, report, flags=re.S)
        else:
            report += f"\n\n{replacement}"
    header = f"{config['title']}｜{now.astimezone(ZoneInfo('Asia/Shanghai')).strftime('%Y-%m-%d')}｜{len(selected)} 项\n\n"
    key = publish_key or topic
    public_url = publish_post(key, str(config["title"]), now, report, selected)
    Path("reports").mkdir(exist_ok=True)
    Path(f"reports/{key}-{now:%Y%m%dT%H%M%SZ}.md").write_text(header + report)
    Path("work").mkdir(exist_ok=True)
    Path("work/pending.json").write_text(
        json.dumps(
            {
                "topic": topic,
                "title": config["title"],
                "url": public_url,
                "created_at": now.isoformat(),
                "items": dump_items(selected),
                "notify": config.get("notify", True),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True)
    parser.add_argument("--config", default="config/sources.yml")
    parser.add_argument("--state", default="state/seen.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(levelname)s %(message)s")
    now = datetime.now(UTC)
    config = yaml.safe_load(Path(args.config).read_text())["topics"][args.topic]
    prepare_topic(args.topic, config, Path(args.state), now, args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
