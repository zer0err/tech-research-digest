"""Collect and validate a single rotation-domain draft; never publish here."""
from __future__ import annotations

import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import yaml

from .rotation_claims import rotation_claim_issues
from .core import (
    Item,
    SourceUnavailable,
    canonical_url,
    collect,
    dump_items,
    groq_analyse,
    identity_aliases,
    link_keys,
    normalize_doi,
    normalize_report,
    report_validation_errors,
)
from .domain_report import MODULES
from .schedule import ZONE

_CONFIG = Path(__file__).resolve().parents[1] / "config"
_SOURCE_CONFIG = _CONFIG / "sources.yml"
_OTHER_CONFIG = _CONFIG / "rotation_other.yml"
# Keep the source window independent of the 3-item model budget. This only
# changes the local window; capped/rolling providers may still omit older items.
_LOOKBACK_HOURS = 240
_MAX_ITEMS = 3
# collect() deliberately admits precise timestamps up to now + 2h. Shift the
# collection clock, not the scheduled cutoff, and retain both fixed bounds.
_COLLECT_GRACE = timedelta(hours=2)
_AI = ("artificial intelligence", "machine learning", "neural network", "deep learning",
       "language model", "computer vision", "generative ai", "llm", "ai model")

# Every slot routes to one field. Explicit source pools are reused, but narrow
# local terms drive acceptance rather than inherit broad legacy topic filters.
_ROUTES = {
    "models": (
        ("model_research",),
        ("foundation model", "language model architecture", "model architecture", "reasoning model",
         "mixture of experts", "multilingual language model"),
        ("training dataset", "data curation", "retrieval-augmented generation", "vision-language-action"),
        "重点核对架构、能力与可对比的实验边界。",
    ),
    "training": (
        ("model_research",),
        ("pretraining", "pre-training", "post-training", "training dataset", "data curation",
         "training data", "instruction tuning", "preference optimization", "curriculum learning"),
        (),
        "只报道训练算法、数据方法或确有证据的训练效率，不把一般模型发布作为训练技术。",
    ),
    "inference": (
        ("inference_systems", "efficient_ai"),
        ("inference engine", "serving throughput", "inference runtime", "quantization", "model compression",
         "inference latency", "speculative decoding", "machine learning compiler", "kernel fusion"),
        (),
        "注明软硬件条件、吞吐、延迟、显存及质量代价，不泛化跨设备的结果。",
    ),
    "agents": (
        ("prompt_engineering", "ecosystem"),
        ("agent tool", "agent framework", "agent orchestration", "model context protocol",
         "multi-agent", "tool calling", "agent workflow"),
        ("robotics", "embodied agent", "vision-language-action", "physical robot"),
        "只报道具体工具调用或智能体编排进展、适用边界与可复现入口。",
    ),
    "knowledge": (
        ("prompt_engineering", "model_research"),
        ("retrieval augmented generation", "retrieval-augmented generation", "vector retrieval",
         "semantic retrieval", "knowledge graph", "document indexing", "retrieval evaluation"),
        (),
        "区分检索和生成证据，核对引用、语料和评测条件。",
    ),
    "multimodal": (
        ("multimodal",),
        ("multimodal", "image generation", "video generation", "speech recognition", "speech synthesis",
         "audio generation", "vision-language model", "audio-visual", "speech enhancement"),
        ("vision-language-action", "robot manipulation", "embodied agent"),
        "注明模态、交互任务、质量指标、复现条件与限制。",
    ),
    "robotics": (
        ("embodied",),
        ("robotics", "robot manipulation", "robot learning", "vision-language-action",
         "embodied intelligence", "sim-to-real", "robot navigation"),
        (),
        "跟踪有实体目标或明确机器人仿真的工作，区分仿真和真实设备证据。",
    ),
    "evaluation": (
        ("product_safety", "prompt_engineering"),
        ("model evaluation", "benchmark", "red teaming", "prompt injection", "robustness evaluation",
         "safety evaluation", "model safety", "model reliability", "firmware security"),
        (),
        "聚焦评测方法及防御性安全结论；说明测试威胁模型和结论的适用边界，不输出攻击载荷或可执行利用指令。",
    ),
    "applications": (
        ("ecosystem",),
        ("generally available", "general availability", "production deployment", "production use",
         "pricing", "customer case study", "customer deployment", "commercial launch", "product launch"),
        (),
        "仅报告有官方发布、可用范围或费用证据的实际产品变化，避免营销和未经核实的商业推断。",
    ),
    "infrastructure": (
        ("ai_hardware",),
        ("ai accelerator", "accelerator architecture", "compute-in-memory", "gpu cluster", "ai hardware",
         "fpga acceleration", "npu architecture", "gpu interconnect", "neuromorphic"),
        (),
        "关注开发和计算基础设施，核对硬件、互连、功耗与基准条件。",
    ),
}

if set(_ROUTES) != set(MODULES):
    raise RuntimeError("Rotation collector routes must match the ten canonical domains")


def collection_config(domain: str) -> dict:
    """Build an explicit, fresh collector config from the site's approved source definitions."""
    pools, terms, excluded, focus = _ROUTES[domain]
    legacy = yaml.safe_load(_SOURCE_CONFIG.read_text(encoding="utf-8"))["topics"]
    sources = {}
    for pool in pools:
        for source in legacy[pool]["sources"]:
            if source.get("kind") == "resource":
                continue
            identity = (
                source.get("type", "rss"), source["url"], source.get("query"), source.get("limit")
            )
            sources.setdefault(identity, source)
    return {
        "title": MODULES[domain],
        "analysis_focus": focus,
        "lookback_hours": _LOOKBACK_HOURS - int(_COLLECT_GRACE.total_seconds() // 3600),
        "max_items": _MAX_ITEMS,
        "max_per_source": 2,
        "keywords": list(terms),
        # Application release/pricing language alone does not establish AI relevance.
        "required_any": list(_AI) if domain == "applications" else [],
        "exclude_any": list(excluded),
        "sources": list(sources.values()),
    }


def generate(domain: str, cutoff: datetime, blocked: set[str]) -> dict:
    """Fetch one domain at its scheduled cutoff and perform at most one analysis call."""
    if domain not in _ROUTES:
        raise ValueError(f"Unknown rotation domain: {domain}")
    if cutoff.tzinfo is None or cutoff.utcoffset() is None:
        raise ValueError("Rotation cutoff must include a timezone")

    config = collection_config(domain)
    row = {"ok": False, "topic": domain, "title": config["title"], "report": "", "items": [],
           "analysis": None}
    try:
        candidates = collect(config, cutoff.astimezone(ZONE) - _COLLECT_GRACE)
    except SourceUnavailable:
        return {**row, "reason": "source_failure"}

    unavailable = getattr(candidates, "stats", {}).get("failed", 0)
    usable = sorted(
        (item for item in candidates if item.title.strip() and len(item.summary.strip()) >= 40
         and item.url.startswith("https://") and item.kind != "resource"),
        key=lambda item: (item.published, item.uid, item.url),
        reverse=True,
    )
    selected = []
    identities = set(blocked)
    for item in usable:
        keys = set(link_keys(item))
        if keys & identities:
            continue
        selected.append(item)
        identities.update(keys)
        if len(selected) == _MAX_ITEMS:
            break
    if not selected:
        reason = "source_failure" if unavailable else ("deduplicated" if usable else "no_matching_in_window")
        return {**row, "reason": reason}

    content_type = "research"
    try:
        report = groq_analyse(
            row["title"],
            config["analysis_focus"] + " 仅保留资料原有数值，第一节各条结论须标注相应的 [n] 引用。"
            " 摘要已点名基线时写出名称，不可称未提供基线；可明确哪些细节未给出。"
            " 未实测低端设备部署时，只可写部署设想、用户可访问性或待验证事项，不可写已验证。",
            selected,
            content_type,
        )
    except (httpx.HTTPError, OSError, RuntimeError, ValueError, KeyError, TypeError, IndexError, AttributeError):
        return {**row, "reason": "analysis_api_failure"}
    report = normalize_report(report, content_type, selected)
    issues = report_validation_errors(report, selected, content_type)
    issues.extend(rotation_claim_issues(report, [item.summary for item in selected]))
    if "降级为" in report:
        issues.append("model_truncated_or_fallback")
    if len(report) < 300:
        issues.append("insufficient_analysis")
    if issues:
        return {**row, "reason": "analysis_rejected", "issues": issues}
    return {
        **row,
        "ok": True,
        "reason": "prepared",
        "report": report,
        "items": dump_items(selected),
        "analysis": {"provider": "Groq", "model": os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")},
        "sources_failed": unavailable,
    }


def _md_text(text: str) -> str:
    return re.sub(r"([\\`*_{}\[\]()#<>!|])", r"\\\1", " ".join(text.split()))


def generate_other(cutoff: datetime, blocked: set[str]) -> dict:
    """Render only explicitly approved residual evidence; never fetch or call a model."""
    if cutoff.tzinfo is None or cutoff.utcoffset() is None:
        raise ValueError("Rotation cutoff must include a timezone")
    row = {"ok": False, "topic": "other", "title": "其他", "report": "", "items": [], "analysis": None}
    if not _OTHER_CONFIG.is_file():
        return {**row, "reason": "no_verified_residual"}
    try:
        config = yaml.safe_load(_OTHER_CONFIG.read_text(encoding="utf-8"))
        host_config, entries = config["official_hosts"], config["verified_items"]
        if not isinstance(host_config, list) or not isinstance(entries, list):
            raise TypeError("official_hosts and verified_items must be lists")
        hosts = {host.lower() for host in host_config}
    except (OSError, yaml.YAMLError, TypeError, KeyError, AttributeError):
        return {**row, "reason": "invalid_residual_config"}

    candidates = []
    lower = cutoff - timedelta(hours=_LOOKBACK_HOURS)
    for record in entries:
        try:
            if record["verified"] is not True or not record["residual_reason"].strip():
                continue
            title, summary, source = (record[key].strip() for key in ("title", "summary", "source"))
            published = datetime.fromisoformat(record["published"])
            raw_url = record["url"].strip()
            parts = urlsplit(raw_url)
            url = canonical_url(raw_url)
            doi = normalize_doi(record.get("doi", ""))
            if (
                not title or not source or len(summary) < 40 or published.utcoffset() is None
                or not lower < published <= cutoff or parts.scheme != "https"
                or any(char.isspace() for char in raw_url)
                or parts.hostname not in hosts or parts.username is not None
                or parts.password is not None or parts.port not in (None, 443)
            ):
                continue
        except (AttributeError, KeyError, TypeError, ValueError):
            continue
        aliases = identity_aliases({"link": url, "doi": doi})
        candidates.append(Item("url:" + url, title, url, published.isoformat(), summary, source,
                               doi=doi, date_precision="instant", aliases=aliases))
    selected = []
    keys = set(blocked)
    for item in sorted(candidates, key=lambda value: (datetime.fromisoformat(value.published), value.url), reverse=True):
        identities = set(link_keys(item))
        if identities & keys:
            continue
        selected.append(item)
        keys.update(identities)
        if len(selected) == 2:
            break
    if not selected:
        return {**row, "reason": "no_verified_residual"}

    bullets = [
        f"- **{_md_text(item.title)}**：{_md_text(item.summary)} [{index}]"
        for index, item in enumerate(selected, 1)
    ]
    return {**row, "ok": True, "reason": "prepared", "report": "\n".join(bullets), "items": dump_items(selected)}
