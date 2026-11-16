"""Consolidate historical fragment pages into one daily report per Asia/Taipei date.

This command rewrites public HTML and publication receipts. It does not call Telegram.
"""
from __future__ import annotations

import json

from .daily import migrate


def main() -> None:
    mapping = migrate()
    counts = mapping.get("counts", {})
    print(json.dumps(counts, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
