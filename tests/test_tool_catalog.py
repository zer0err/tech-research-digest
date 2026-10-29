import copy
import json
from pathlib import Path

from research_bot.tool_catalog import canonical_url, validate_catalog


CATALOG = json.loads((Path(__file__).parents[1] / "config/tools.json").read_text(encoding="utf-8"))


def test_real_catalog_has_verified_nonempty_records():
    assert len(CATALOG["tools"]) >= 12
    assert validate_catalog(CATALOG) == []
    assert all(tool["status"] == "active" for tool in CATALOG["tools"])


def test_duplicate_url_and_id_are_rejected():
    data = copy.deepcopy(CATALOG)
    duplicate = copy.deepcopy(data["tools"][0])
    duplicate["official_url"] += "/"
    data["tools"].append(duplicate)
    errors = validate_catalog(data)
    assert any("duplicate" in error for error in errors)


def test_open_source_claim_requires_license_evidence():
    data = copy.deepcopy(CATALOG)
    data["tools"][0]["evidence"] = [data["tools"][0]["evidence"][0]]
    assert any("license evidence" in error for error in validate_catalog(data))


def test_unknown_is_explicit_and_urls_are_canonicalized():
    assert canonical_url("https://Example.COM/path/?tracking=1") == "https://example.com/path"
    data = copy.deepcopy(CATALOG)
    data["tools"][0]["regions"]["availability"] = "probably-mainland"
    assert any("regions" in error for error in validate_catalog(data))
