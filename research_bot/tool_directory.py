"""Render the curated AI tool catalog as a progressively enhanced static page."""
from __future__ import annotations

import html
import json
from pathlib import Path

from .site import shell
from .tool_catalog import load_catalog

CATEGORY_LABELS = {
    "general-text": "通用文本",
    "search-research": "搜索与研究",
    "coding-development": "编程与开发",
    "image-design": "图像与设计",
    "video": "视频",
    "audio-music": "音频与音乐",
    "agents-automation": "Agent 与自动化",
    "data-analysis": "数据分析与评测",
    "models-infrastructure": "模型与基础设施",
    "edge-hardware": "端侧与硬件",
    "learning-education": "学习与教育",
}
REGION_LABELS = {
    "mainland": "中国大陆",
    "overseas": "海外",
    "cross-region": "跨地区（本地部署）",
    "unknown": "待核验",
}
PRICING_LABELS = {
    "free-open-source": "免费开源",
    "free-tier": "有免费额度",
    "free-trial": "限时试用",
    "paid": "付费",
    "unknown": "待核验",
}
ACCESS_LABELS = {
    "web": "网页",
    "desktop": "桌面端",
    "mobile": "移动端",
    "api": "API",
    "plugin": "插件",
    "local": "本地运行",
    "hardware": "硬件",
}


def _select(name: str, label: str, values: list[str], labels: dict[str, str]) -> str:
    options = ['<option value="">全部</option>'] + [
        f'<option value="{html.escape(value, quote=True)}">{html.escape(labels[value])}</option>'
        for value in values
    ]
    return (
        f'<label>{html.escape(label)}<select data-tool-filter="{html.escape(name, quote=True)}">'
        f'{"".join(options)}</select></label>'
    )


def _card(tool: dict) -> str:
    region = tool["regions"]["availability"]
    pricing = tool["pricing"]["modes"]
    capabilities = "、".join(tool["capabilities"])
    access = "、".join(ACCESS_LABELS[item] for item in tool["access"])
    pricing_text = "、".join(PRICING_LABELS[item] for item in pricing)
    license_name = tool["pricing"].get("license", "")
    license_evidence = next(
        (item["url"] for item in tool["evidence"] if item.get("kind") == "official_license"),
        "",
    )
    license_html = ""
    if license_name and license_evidence:
        license_html = (
            '<div><dt>开源许可</dt><dd>'
            f'<a href="{html.escape(license_evidence, quote=True)}" rel="noopener noreferrer">'
            f'{html.escape(license_name)}</a></dd></div>'
        )
    search_text = " ".join(
        [tool["name"], tool["provider"], tool["summary_zh"], capabilities]
    ).lower()
    return (
        f'<article class="directory-card" data-tool-card data-tool-id="{html.escape(tool["id"], quote=True)}" '
        f'data-category="{html.escape(tool["primary_category"], quote=True)}" '
        f'data-access="{html.escape(" ".join(tool["access"]), quote=True)}" '
        f'data-region="{html.escape(region, quote=True)}" data-pricing="{html.escape(" ".join(pricing), quote=True)}" '
        f'data-search="{html.escape(search_text, quote=True)}">'
        f'<p class="eyebrow">{html.escape(CATEGORY_LABELS[tool["primary_category"]])}</p>'
        f'<h2>{html.escape(tool["name"])}</h2><p class="tool-provider">项目 / 维护方：{html.escape(tool["provider"])}</p>'
        f'<p>{html.escape(tool["summary_zh"])}</p><dl>'
        f'<div><dt>适用能力</dt><dd>{html.escape(capabilities)}</dd></div>'
        f'<div><dt>使用方式</dt><dd>{html.escape(access)}</dd></div>'
        f'<div><dt>使用边界</dt><dd>本地部署 · 通常无需产品注册；{html.escape(tool["regions"]["notes_zh"])}</dd></div>'
        f'<div><dt>费用边界</dt><dd>{html.escape(pricing_text)}；{html.escape(tool["pricing"]["notes_zh"])}</dd></div>'
        f'{license_html}</dl>'
        f'<a class="read-link" href="{html.escape(tool["official_url"], quote=True)}" rel="noopener noreferrer">'
        '查看官方来源 <span>↗</span></a>'
        f'<p class="tool-verified">核验日期：{html.escape(tool["verified_at"])}</p></article>'
    )


def render_tools_page(
    catalog_path: Path = Path("config/tools.json"),
    output_path: Path = Path("docs/tools/index.html"),
) -> Path:
    catalog = load_catalog(catalog_path)
    tools = [tool for tool in catalog["tools"] if tool["status"] == "active"]
    if not tools:
        raise ValueError("refusing to publish an empty tool directory")
    categories = sorted({tool["primary_category"] for tool in tools}, key=lambda item: CATEGORY_LABELS[item])
    access = sorted({mode for tool in tools for mode in tool["access"]}, key=lambda item: ACCESS_LABELS[item])
    controls = (
        '<div class="tool-filters" aria-label="筛选工具">'
        '<label>搜索<input type="search" data-tool-search placeholder="名称、维护方或能力" autocomplete="off"></label>'
        + _select("category", "领域", categories, CATEGORY_LABELS)
        + _select("access", "使用方式", access, ACCESS_LABELS)
        + '<button type="button" data-tool-reset>重置</button></div>'
    )
    body = (
        '<section class="directory-page"><header class="series-heading">'
        '<p class="eyebrow">AI ECOSYSTEM</p><h1>AI 生态工具目录</h1>'
        '<p class="lead">按真实使用边界整理的 AI 开发与应用工具。当前只收录已核验官方来源的条目，不用空栏目凑数。</p>'
        f'<p class="directory-notice">首批收录：可本地运行的开源项目（{len(tools)}）。资料核验至 {html.escape(catalog["verified_at"])}。'
        '“免费开源”只表示软件许可，不代表模型、硬件、网络或第三方服务没有成本；可用性与价格可能变化，请在使用前复核官方页面。</p>'
        '</header>' + controls
        + f'<p class="tool-result-count" data-tool-count aria-live="polite">显示全部 {len(tools)} 项</p>'
        + '<div class="directory-grid" data-tool-grid>' + "".join(_card(tool) for tool in tools) + '</div>'
        + '<div class="tool-empty" data-tool-empty hidden><p>当前没有符合且已核验的条目。</p>'
        '<button type="button" data-tool-empty-reset>清除筛选</button></div>'
        + '<section class="directory-policy"><h2>收录原则</h2><p>优先使用产品官网、官方代码仓库和官方许可文件。'
        '地区不是国籍标签，而是个人用户能否访问与注册的使用边界；无法核实的价格或可用性不会写成确定事实。广告与商业合作不得改变排序和核验结论。</p>'
        '<noscript><p>未启用 JavaScript 时仍会显示全部条目；筛选功能不可用。</p></noscript></section>'
        '</section><script type="module" src="../assets/tool-directory.js?v=1"></script>'
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        shell("AI 生态工具目录 · VORASIO", "经官方来源核验的 AI 工具目录", body, "../"),
        encoding="utf-8",
    )
    return output_path


if __name__ == "__main__":
    rendered = render_tools_page()
    print(json.dumps({"rendered": str(rendered)}, ensure_ascii=False))
