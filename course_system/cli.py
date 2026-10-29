from __future__ import annotations

import argparse
import json
from pathlib import Path

from .validate import validate_series


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate VORASIO course metadata before local preview or release.")
    parser.add_argument("metadata", type=Path, help="Path to a series metadata JSON file")
    parser.add_argument(
        "--release",
        action="store_true",
        help="Apply the full-series release gate instead of the authoring gate",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        series = json.loads(args.metadata.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot load {args.metadata}: {exc}")
        return 2

    issues = validate_series(series, for_release=args.release)
    if not issues:
        mode = "release" if args.release else "authoring"
        print(f"OK: {series.get('series_id', '<unknown>')} passed the {mode} gate")
        return 0

    for issue in issues:
        print(f"{issue.path}: [{issue.code}] {issue.message}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
