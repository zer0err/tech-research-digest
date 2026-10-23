from __future__ import annotations

import argparse
import json
import logging
import os
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from .audit import decision
from .main import prepare_topic
from .site import base_url, publish_post

BEIJING = ZoneInfo("Asia/Shanghai")


def resolve_slot(slot_name: str, now: datetime, editorial: dict[str, object], topics: dict[str, object]) -> tuple[str, dict[str, object]]:
    slot = editorial["slots"][slot_name]
    weekday = str(now.astimezone(BEIJING).isoweekday())
    topic_name = slot.get("topic") or slot.get("topic_by_weekday", {}).get(weekday)
    if not topic_name:
        raise ValueError(f"No topic configured for slot {slot_name} on weekday {weekday}")
    config = deepcopy(topics[topic_name])
    for key in ("title", "content_type", "max_items", "notify"):
        if key in slot:
            config[key] = slot[key]
    return str(topic_name), config


def prepare_daily_digest(now: datetime, notify: bool = True) -> bool:
    Path("work/pending.json").unlink(missing_ok=True)
    if os.getenv("PUBLICATION_MODE") == "test":
        decision("daily_digest", "test_only")
        return False
    data_path = Path("docs/posts.json")
    entries = json.loads(data_path.read_text()) if data_path.exists() else []
    local_date = now.astimezone(BEIJING).date().isoformat()
    todays = [entry for entry in entries if str(entry.get("date", ""))[:10] == local_date
              and entry.get("topic") != "daily_digest" and entry.get("status") == "published" and int(entry.get("count", 0)) > 0]
    if not todays:
        logging.info("No valid published articles today; skipping daily digest")
        return False
    if todays:
        links = "\n".join(
            f"- [{entry['title']}]({base_url()}/{entry['url']})" for entry in reversed(todays)
        )
        report = (
            f"## 今日概览\n\n今天共发布 **{len(todays)}** 个内容更新。以下列表仅汇总站内已经通过发布流程的内容，"
            "不额外生成未经来源支持的结论。\n\n## 今日内容\n\n"
            f"{links}\n\n## 阅读建议\n\n优先阅读与你当前项目直接相关的栏目；"
            "涉及免费资源、价格、配额和兼容性的内容，请再次打开原始来源核验。"
        )
    else:
        report = "## 今日状态\n\n截至本次汇总，今日没有成功发布的新内容。"
    title = f"VORASIO AI 日报（{local_date}）"
    url = publish_post("daily_digest", title, now, report, [None] * len(todays))
    Path("reports").mkdir(exist_ok=True)
    Path(f"reports/daily_digest-{now:%Y%m%dT%H%M%SZ}.md").write_text(report)
    Path("work").mkdir(exist_ok=True)
    Path("work/pending.json").write_text(
        json.dumps(
            {
                "topic": "daily_digest",
                "title": title,
                "url": url,
                "created_at": now.isoformat(),
                "items": [],
                "published_count": len(todays),
                "notify": notify,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slot", required=True)
    parser.add_argument("--editorial-config", default="config/editorial.yml")
    parser.add_argument("--sources-config", default="config/sources.yml")
    parser.add_argument("--state", default="state/seen.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(levelname)s %(message)s")
    now = datetime.now(UTC)
    editorial = yaml.safe_load(Path(args.editorial_config).read_text())
    topics = yaml.safe_load(Path(args.sources_config).read_text())["topics"]
    slot = editorial["slots"].get(args.slot)
    if not slot:
        raise ValueError(f"Unknown editorial slot: {args.slot}")
    if slot.get("special") == "daily_digest":
        if args.dry_run:
            print("daily_digest")
            return 0
        prepare_daily_digest(now)
        return 0
    topic_name, config = resolve_slot(args.slot, now, editorial, topics)
    prepare_topic(
        topic_name,
        config,
        Path(args.state),
        now,
        dry_run=args.dry_run,
        publish_key=str(slot.get("publish_key", args.slot)),
        allow_empty=bool(slot.get("allow_empty", False)),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
