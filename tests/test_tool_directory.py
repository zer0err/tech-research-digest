from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from research_bot.tool_directory import render_tools_page


def test_renders_every_active_tool_without_empty_groups(tmp_path: Path) -> None:
    output = tmp_path / "docs" / "tools" / "index.html"
    render_tools_page(Path("config/tools.json"), output)
    page = output.read_text(encoding="utf-8")
    catalog = json.loads(Path("config/tools.json").read_text(encoding="utf-8"))
    active = [tool for tool in catalog["tools"] if tool["status"] == "active"]
    assert len(re.findall(r'data-tool-card(?:\s|>)', page)) == len(active)
    for tool in active:
        assert tool["name"] in page
        assert tool["official_url"] in page
        assert tool["verified_at"] in page
    assert "首批收录：可本地运行的开源项目（14）" in page
    assert "empty category" not in page.lower()


def test_filter_options_only_include_values_present_in_catalog(tmp_path: Path) -> None:
    output = tmp_path / "index.html"
    render_tools_page(Path("config/tools.json"), output)
    page = output.read_text(encoding="utf-8")
    assert '<option value="local">' in page
    assert '<option value="mobile">' in page
    assert '<option value="paid">' not in page
    assert '<option value="video">' not in page


def test_refuses_to_publish_empty_catalog(tmp_path: Path) -> None:
    catalog = tmp_path / "tools.json"
    catalog.write_text(json.dumps({"schema_version": 1, "verified_at": "2026-10-29", "tools": []}))
    with pytest.raises(ValueError, match="empty tool directory"):
        render_tools_page(catalog, tmp_path / "index.html")


def test_page_is_progressively_enhanced_and_mobile_ready(tmp_path: Path) -> None:
    output = tmp_path / "index.html"
    render_tools_page(Path("config/tools.json"), output)
    page = output.read_text(encoding="utf-8")
    assert "未启用 JavaScript 时仍会显示全部条目" in page
    assert 'data-tool-search' in page
    assert 'data-tool-filter="category"' in page
    assert 'data-tool-filter="access"' in page
    assert 'data-tool-filter="region"' not in page
    assert 'data-tool-filter="pricing"' not in page
    assert 'tool-directory.js?v=1' in page
    assert 'name="viewport"' in page
