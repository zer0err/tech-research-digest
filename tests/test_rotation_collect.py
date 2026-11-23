import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest
import yaml

from research_bot import rotation_collect as rotation
from research_bot.core import Collected, Item, SourceUnavailable, in_lookback

CUTOFF = datetime(2026, 11, 23, 1, tzinfo=UTC)
EVIDENCE = "The original source explains the limitations of direct measurements and provides reproducible evidence."


def item(i, *, aliases=()):
    return Item(f"item-{i}", f"Item {i}", f"https://example.org/{i}",
                (CUTOFF - timedelta(minutes=i)).isoformat(), EVIDENCE, "Official source", aliases=aliases)


def report(items):
    claims = "\n".join(f"- 已按来源公开的实验设置核对，但仍需独立复核适用条件。 [{i}]"
                       for i in range(1, len(items) + 1))
    body = "本节仅说明原始资料可直接核对的范围与局限，保留对证据边界的说明。" * 12
    refs = "\n".join(f"[{i}] {entry.title} {entry.url}" for i, entry in enumerate(items, 1))
    return f"## 本期结论\n{claims}\n## 逐项分析\n{body}\n## 工程行动建议\n{body}\n## 参考资料\n{refs}"


def test_routes_are_explicit_and_gap_filters_are_narrow():
    assert len(rotation.MODULES) == 10
    configs = {name: rotation.collection_config(name) for name in rotation.MODULES}
    assert all(c["sources"] and c["keywords"] and c["max_items"] == 3 for c in configs.values())
    assert "training dataset" in configs["training"]["keywords"]
    assert "tool calling" in configs["agents"]["keywords"]
    assert "semantic retrieval" in configs["knowledge"]["keywords"]
    assert "pricing" in configs["applications"]["keywords"]
    assert "generative ai" in configs["applications"]["required_any"]
    assert all(source.get("kind") != "resource" for c in configs.values() for source in c["sources"])


def test_generate_uses_single_domain_call_and_keeps_cutoff_and_dedup(monkeypatch):
    calls = []

    def fake_collect(config, clock):
        calls.append(("collect", config["title"]))
        lower = clock - timedelta(hours=config["lookback_hours"])
        assert lower == CUTOFF - timedelta(days=10)
        assert in_lookback(CUTOFF, "instant", lower, clock)
        assert not in_lookback(CUTOFF + timedelta(seconds=1), "instant", lower, clock)
        return [item(6), item(5), item(4), item(3, aliases=("doi:10.1/same",)),
                item(2, aliases=("doi:10.1/same",)), item(1)]

    def fake_model(title, focus, selected, content_type):
        assert "[n]" in focus and content_type == "research"
        calls.append(("model", title))
        assert [entry.uid for entry in selected] == ["item-2", "item-4", "item-5"]
        return report(selected)

    monkeypatch.setattr(rotation, "collect", fake_collect)
    monkeypatch.setattr(rotation, "groq_analyse", fake_model)
    blocked = {"url:https://example.org/1"}
    result = rotation.generate("training", CUTOFF, blocked)
    assert result["ok"] and result["topic"] == "training" and result["title"] == "训练方法与数据"
    assert calls == [("collect", "训练方法与数据"), ("model", "训练方法与数据")]
    assert blocked == {"url:https://example.org/1"}
    assert json.loads(json.dumps(result))["items"][0]["uid"] == "item-2"


def test_rejected_and_api_failure_never_return_evidence_for_publication(monkeypatch):
    monkeypatch.setattr(rotation, "collect", lambda *args: [item(1)])
    monkeypatch.setattr(rotation, "groq_analyse", lambda *args: report(args[2]).replace(
        "已按来源公开", "产生凭空的12345倍提升，已按来源公开"))
    result = rotation.generate("evaluation", CUTOFF, set())
    assert result["reason"] == "analysis_rejected" and result["items"] == []
    assert "unsupported_headline_numbers" in result["issues"]

    def fail(*args):
        raise httpx.ConnectError("simulated")
    monkeypatch.setattr(rotation, "groq_analyse", fail)
    assert rotation.generate("evaluation", CUTOFF, set())["reason"] == "analysis_api_failure"


def test_no_model_for_empty_duplicates_or_unavailable_sources(monkeypatch):
    def never(*args):
        pytest.fail("model must not run")
    monkeypatch.setattr(rotation, "groq_analyse", never)
    monkeypatch.setattr(rotation, "collect", lambda *args: Collected([], {"failed": 0}))
    assert rotation.generate("agents", CUTOFF, set())["reason"] == "no_matching_in_window"
    monkeypatch.setattr(rotation, "collect", lambda *args: Collected([], {"failed": 1}))
    assert rotation.generate("agents", CUTOFF, set())["reason"] == "source_failure"
    monkeypatch.setattr(rotation, "collect", lambda *args: [item(1)])
    assert rotation.generate("agents", CUTOFF, {"url:https://example.org/1"})["reason"] == "deduplicated"

    def fail(*args):
        raise SourceUnavailable("none")
    monkeypatch.setattr(rotation, "collect", fail)
    assert rotation.generate("agents", CUTOFF, set())["reason"] == "source_failure"
    with pytest.raises(ValueError, match="Unknown"):
        rotation.generate("unknown", CUTOFF, set())
    with pytest.raises(ValueError, match="timezone"):
        rotation.generate("agents", CUTOFF.replace(tzinfo=None), set())


def test_other_explicit_opt_in_no_model_and_no_empty_block(monkeypatch, tmp_path):
    config = tmp_path / "other.yml"
    monkeypatch.setattr(rotation, "_OTHER_CONFIG", config)
    monkeypatch.setattr(rotation, "groq_analyse", lambda *args: pytest.fail("Other is model-free"))
    monkeypatch.setattr(rotation, "collect", lambda *args: pytest.fail("Other is network-free"))
    assert rotation.generate_other(CUTOFF, set())["report"] == ""
    seed = {"title": "Verified <official> notice", "summary": EVIDENCE, "source": "Official source",
            "published": CUTOFF.isoformat(), "url": "https://example.org/official", "verified": True,
            "residual_reason": "An independently verified public policy notice outside the ten technical domains."}
    config.write_text(yaml.safe_dump({
        "official_hosts": ["example.org"],
        "verified_items": [
            {**seed, "url": "https://malicious.example/official"},
            {**seed, "title": "Dummy", "url": "https://example.org/unverified", "verified": False},
            {**seed, "url": "http://example.org/unsafe"},
            {**seed, "url": "https://example.org/too-late", "published": (CUTOFF + timedelta(seconds=1)).isoformat()},
            seed,
        ],
    }))
    result = rotation.generate_other(CUTOFF, set())
    assert result["ok"] and result["analysis"] is None
    assert [entry["url"] for entry in result["items"]] == [seed["url"]]
    assert "\\<official\\>" in result["report"]
    assert not rotation.generate_other(CUTOFF, {"url:" + seed["url"]})["ok"]
