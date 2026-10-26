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

from .audit import decision
from .core import (
    SourceUnavailable,
    collect,
    dump_items,
    groq_analyse,
    load_state,
    mimo_analyse,
    mimo_enabled,
    normalize_report,
    report_validation_errors,
    unseen,
)
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
    # A skipped run must never reuse a previous run's publish/notification request.
    Path("work/pending.json").unlink(missing_ok=True)
    mode = os.getenv("PUBLICATION_MODE", "production")
    if mode not in {"production", "test"}:
        raise ValueError("Unknown publication mode")
    state = load_state(state_path) if mode == "production" else {"version": 1, "topics": {}}
    key = publish_key or topic
    try:
        candidates = collect(config, now)
    except SourceUnavailable:
        if dry_run:
            raise
        logging.exception("Sources unavailable for %s", topic)
        decision(key, "source_failure", mode=mode)
        return False
    collected = len(candidates)
    candidates = [item for item in candidates if len(item.summary.strip()) >= 40 and item.title.strip()
                  and item.url.startswith("https://")]
    fresh = unseen(candidates, state, topic)
    counts = {"collected": collected, "usable": len(candidates), "already_published": len(candidates) - len(fresh),
              "unpublished": len(fresh), "mode": mode}
    limit = min(3, int(config["max_items"]))
    if config.get("content_type") == "radar":
        resources = [item for item in fresh if item.kind == "resource"][:2]
        regular = [item for item in fresh if item.kind != "resource"][: limit - len(resources)]
        selected = sorted(resources + regular, key=lambda item: item.published, reverse=True)
    else:
        selected = fresh[:limit]
    if not selected:
        logging.info("No unseen in-window items for %s", topic)
        reason = "already_published" if candidates else ("insufficient_abstract" if collected else "no_matching_in_window")
        decision(key, reason, **counts)
        return False
    if dry_run:
        print(json.dumps(dump_items(selected), ensure_ascii=False, indent=2))
        return bool(selected)
    content_type = str(config.get("content_type", "research"))
    for attempt in range(2):
        try:
            analyse = mimo_analyse if attempt == 1 and mimo_enabled() else groq_analyse
            try:
                report = analyse(str(config["title"]), str(config["analysis_focus"]), selected, content_type)
            except Exception:
                if analyse is not groq_analyse or not mimo_enabled():
                    raise
                analyse = mimo_analyse
                report = mimo_analyse(str(config["title"]), str(config["analysis_focus"]), selected, content_type)
        except Exception as exc:
            logging.warning("Analysis unavailable for %s (%s); skipping publication", topic, type(exc).__name__)
            decision(key, "analysis_api_failure", error=type(exc).__name__, **counts)
            return False
        report = normalize_report(report, content_type)
        issues = report_validation_errors(report, selected, content_type)
        if "降级为" in report:
            issues.append("model_truncated_or_fallback")
        if len(report) < 300:
            issues.append("insufficient_analysis")
        if not issues:
            break
        logging.warning("Analysis for %s rejected (%s); attempt %s", topic, ",".join(issues), attempt + 1)
        Path("reports").mkdir(exist_ok=True)
        Path(f"reports/rejected-{topic}-{now:%Y%m%dT%H%M%SZ}-{attempt}.md").write_text(report)
        if attempt == 1:
            decision(key, "analysis_rejected", issues=issues, **counts)
            return False
        selected = selected[:2]
    if config.get("content_type") == "radar":
        marker = "## 今日免费 VPS 与 AI 资源"
        resources = [
            f"- [{i}] **待核验线索：{item.title}**。免费期限、额度、信用卡、地区与续费条件："
            f"尚未经官方页面核验。[查看来源]({item.url})"
            for i, item in enumerate(selected, 1) if item.kind == "resource"
        ]
        resource_text = "\n".join(resources) if resources else "今日未发现新的、可由公开来源确认的免费资源。"
        replacement = f"{marker}\n\n{resource_text}"
        if marker in report:
            report = re.sub(r"## 今日免费 VPS 与 AI 资源.*?(?=\n## |\Z)", replacement, report, flags=re.S)
        else:
            report += f"\n\n{replacement}"
    header = f"{config['title']}｜{now.astimezone(ZoneInfo('Asia/Shanghai')).strftime('%Y-%m-%d')}｜{len(selected)} 项\n\n"
    if mode == "test":
        Path("reports").mkdir(exist_ok=True)
        Path(f"reports/test-{key}.md").write_text(header + report)
        decision(key, "test_only", selected=len(selected), **counts)
        return False
    analysis = {"provider": "Xiaomi MiMo" if analyse is mimo_analyse else "Groq",
                "model": "mimo-v2.6-flash" if analyse is mimo_analyse else os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")}
    public_url = publish_post(key, str(config["title"]), now, report, selected, analysis=analysis)
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
                "mode": mode,
                "analysis": analysis,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    decision(key, "prepared", selected=len(selected), **counts)
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
