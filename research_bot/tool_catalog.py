"""Deterministic validation for the curated AI tool catalog."""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CATEGORIES = {
    "general-text", "search-research", "coding-development", "image-design",
    "video", "audio-music", "agents-automation", "data-analysis",
    "models-infrastructure", "edge-hardware", "learning-education",
}
REGIONS = {"mainland", "overseas", "cross-region", "unknown"}
PRICING = {"free-open-source", "free-tier", "free-trial", "paid", "unknown"}
ACCESS = {"web", "desktop", "mobile", "api", "plugin", "local", "hardware"}


def canonical_url(value: str) -> str:
    parts = urlsplit(value)
    if parts.scheme != "https" or not parts.netloc or parts.username or parts.password:
        raise ValueError("URLs must be public HTTPS URLs without credentials")
    path = parts.path.rstrip("/") or "/"
    return urlunsplit(("https", parts.netloc.lower(), path, "", ""))


def validate_catalog(data: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict) or not isinstance(data.get("tools"), list):
        return ["catalog must be an object containing a tools list"]
    ids: set[str] = set()
    urls: set[str] = set()
    for index, tool in enumerate(data["tools"]):
        path = f"tools[{index}]"
        if not isinstance(tool, dict):
            errors.append(f"{path}: must be an object")
            continue
        required = ("id", "name", "provider", "official_url", "primary_category", "capabilities",
                    "summary_zh", "regions", "access", "pricing", "evidence", "verified_at", "status")
        for field in required:
            if field not in tool:
                errors.append(f"{path}.{field}: missing")
        tool_id = tool.get("id")
        if not isinstance(tool_id, str) or not ID.fullmatch(tool_id):
            errors.append(f"{path}.id: unsafe id")
        elif tool_id in ids:
            errors.append(f"{path}.id: duplicate")
        else:
            ids.add(tool_id)
        for field in ("name", "provider", "summary_zh"):
            if not isinstance(tool.get(field), str) or not tool[field].strip():
                errors.append(f"{path}.{field}: must be non-empty text")
        if tool.get("primary_category") not in CATEGORIES:
            errors.append(f"{path}.primary_category: invalid")
        if not isinstance(tool.get("capabilities"), list) or not tool["capabilities"]:
            errors.append(f"{path}.capabilities: must be a non-empty list")
        if not isinstance(tool.get("access"), list) or not tool["access"] or not set(tool["access"]) <= ACCESS:
            errors.append(f"{path}.access: invalid")
        region = tool.get("regions", {})
        if not isinstance(region, dict) or region.get("availability") not in REGIONS:
            errors.append(f"{path}.regions: invalid availability")
        pricing = tool.get("pricing", {})
        modes = pricing.get("modes", []) if isinstance(pricing, dict) else []
        if not isinstance(modes, list) or not modes or not set(modes) <= PRICING:
            errors.append(f"{path}.pricing.modes: invalid")
        evidence = tool.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{path}.evidence: official evidence required")
            evidence = []
        evidence_kinds = {item.get("kind") for item in evidence if isinstance(item, dict)}
        if "official_repository" not in evidence_kinds and "official_product" not in evidence_kinds:
            errors.append(f"{path}.evidence: official source required")
        if "free-open-source" in modes and "official_license" not in evidence_kinds:
            errors.append(f"{path}.pricing: open-source claim requires official license evidence")
        for label, value in [("official_url", tool.get("official_url")), *(
            (f"evidence[{i}].url", item.get("url")) for i, item in enumerate(evidence) if isinstance(item, dict)
        )]:
            try:
                normalized = canonical_url(value) if isinstance(value, str) else ""
                if not normalized:
                    raise ValueError
                if label == "official_url":
                    if normalized in urls:
                        errors.append(f"{path}.official_url: duplicate canonical URL")
                    urls.add(normalized)
            except ValueError:
                errors.append(f"{path}.{label}: invalid URL")
        try:
            verified = date.fromisoformat(tool.get("verified_at", ""))
            if verified > date.today():
                errors.append(f"{path}.verified_at: future date")
        except (TypeError, ValueError):
            errors.append(f"{path}.verified_at: invalid date")
        if tool.get("status") not in {"active", "candidate", "unavailable"}:
            errors.append(f"{path}.status: invalid")
    return errors


def load_catalog(path: Path = Path("config/tools.json")) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_catalog(data)
    if errors:
        raise ValueError("\n".join(errors))
    return data


if __name__ == "__main__":
    catalog = load_catalog()
    print(f"OK: {len(catalog['tools'])} curated tool records")
