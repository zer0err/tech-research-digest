"""Render the evergreen AI knowledge section from its reviewed Markdown source."""
from __future__ import annotations

import html
import re
from pathlib import Path

from markdown_it import MarkdownIt

from .site import shell

TITLE = "从模型到智能体：一篇看懂 AI 生态、代表产品与常见术语"
SLUG = "ai-ecosystem-guide"
VERIFIED = "2026-10-29"
DESCRIPTION = "七个观察层、73 个代表模型与工具，读懂 model、harness、agent、vibe coding 的关系和应用场景。"
LAYERS = (
    ("模型", "12 个模型家族"),
    ("推理与接入", "10 个运行与接入工具"),
    ("知识与工具", "10 个检索与操作工具"),
    ("智能体框架与运行时", "10 个开发框架"),
    ("工作流与搭建平台", "10 个业务搭建平台"),
    ("编程与软件创造", "11 个编程应用"),
    ("通用与专业应用", "10 个成品应用"),
)
DIAGRAMS = (
    ('ecosystem', '生态地图', '从能力到应用', '箭头表示常见的能力组合方向；不是所有产品都需要逐层搭建。第六与第七项是应用层的两条分支。'),
    ('model-harness-agent', '三个核心概念', 'Model、Harness 与 Agent', '外框表示整个 Agent 系统；虚线范围表示 Harness 在运行中的组织与调度范围，并不表示模型参数属于 Harness。'),
    ('agent-loop', '执行循环', 'Agent 怎样完成任务', '工具结果和验收条件决定是否完成；未完成就带着反馈继续，缺少信息或权限时请人协助。'),
    ('rag-vs-finetuning', '知识与训练', 'RAG 与微调', 'RAG 通常不改模型参数，微调会调整参数；二者可以结合使用。'),
    ('ai-coding-methods', '编程方式', '三种 AI 编程方式', '区别在于人怎样组织、审查和验收工作；三种方式可以组合，不是固定的升级阶梯。'),
)
DIAGRAM_HEIGHTS = {
    'ecosystem': (664, 1000),
    'model-harness-agent': (580, 866),
    'agent-loop': (454, 866),
    'rag-vs-finetuning': (526, 1000),
    'ai-coding-methods': (382, 773),
}


def page_shell(title: str, description: str, body: str) -> str:
    page = shell(title, description, body, "../")
    page = page.replace(
        '<script type="module" src="../assets/article.js?v=replay-6"></script>',
        '<link rel="stylesheet" href="../assets/knowledge.css?v=2">',
    )
    page = page.replace('<body>', '<body class="knowledge-page"><a class="knowledge-skip" href="#main">跳到正文</a>')
    page = page.replace('<main>', '<main id="main">')
    page = page.replace(
        '<a href="../knowledge/index.html">AI 知识科普</a>',
        '<a aria-current="page" href="../knowledge/index.html">AI 知识科普</a>',
    )
    page = page.replace(
        '由 GitHub Actions 定时采集，Groq 辅助分析。重要结论请核对原论文。',
        'AI 辅助整理的科普内容，参考来源见正文；产品能力与名称以官方最新说明为准。',
    )
    return page


def render_article(source: str) -> tuple[str, list[tuple[int, str, str]]]:
    """Convert the chat article's bold section labels into semantic headings."""
    source = re.sub(r'^\*\*从模型到智能体：[^\n]+\*\*\n*', '', source, count=1)

    def heading(match: re.Match[str]) -> str:
        label = match.group(1)
        if re.match(r'[一二三四五六]、', label):
            return '## ' + label
        if re.match(r'[①②③④⑤⑥⑦]|[1-4]\. |围绕', label):
            return '### ' + label
        return match.group(0)

    source = re.sub(r'^\*\*([^\n]+)\*\*$', heading, source, flags=re.M)
    source += (
        '\n\n## 来源与编辑说明\n\n'
        '本文由 AI 辅助整理，依据 2026 年 10 月 29 日查阅的公开资料编写。'
        '各代表作品名称链接至官网、官方文档或官方仓库，作为对应简介的来源入口。'
        '收录代表性不等于性能排名，也不代表逐项安装或实测。'
        '七个观察层是教学分类；框架、运行时与应用存在交叉。'
        '模型与产品可能更名、停用或调整能力，使用前请复核对应官方页面。\n\n'
        '- [Harness 的职责：OpenAI 官方文档](https://developers.openai.com/api/docs/guides/agents/sandboxes)\n'
        '- [长任务的 Harness 设计：Anthropic](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)\n'
        '- [MCP 官方介绍](https://modelcontextprotocol.io/introduction)\n'
        '- [Vibe coding 的术语辨析：Simon Willison](https://simonwillison.net/2025/Mar/19/vibe-coding/)\n'
    )
    md = MarkdownIt('commonmark', {'html': False}).enable('table')
    tokens = md.parse(source)
    toc: list[tuple[int, str, str]] = []
    layer = 0
    for index, token in enumerate(tokens):
        if token.type != 'heading_open':
            continue
        label = tokens[index + 1].content
        if re.match(r'[①②③④⑤⑥⑦]', label):
            layer += 1
            anchor = f'layer-{layer}'
        else:
            anchor = f'section-{len(toc) + 1}'
        token.attrSet('id', anchor)
        toc.append((int(token.tag[1:]), anchor, label))
    if layer != 7:
        raise ValueError(f'Expected seven ecosystem layers, got {layer}')
    rendered = md.renderer.render(tokens, md.options, {})
    for index, (key, _, title, caption) in enumerate(DIAGRAMS, 1):
        pattern = rf'<p><img src="\.\./assets/knowledge/{key}\.svg" alt="([^"]*)"\s*/?></p>'

        def figure(match: re.Match[str]) -> str:
            alt = match.group(1)
            desktop_height, mobile_height = DIAGRAM_HEIGHTS[key]
            return (
                f'<figure class="knowledge-figure" id="diagram-{key}" '
                f'style="--diagram-ratio:900 / {desktop_height};--diagram-mobile-ratio:360 / {mobile_height}">'
                f'<div class="figure-heading"><span>图 {index:02d}</span><strong>{html.escape(title)}</strong></div>'
                '<picture>'
                f'<source media="(max-width: 600px)" srcset="../assets/knowledge/{key}-mobile.svg">'
                f'<img src="../assets/knowledge/{key}.svg" alt="{alt}" width="900" height="{desktop_height}" decoding="async">'
                '</picture>'
                f'<figcaption><b>读图提示：</b>{html.escape(caption)}</figcaption></figure>'
            )

        rendered, count = re.subn(pattern, figure, rendered)
        if count != 1:
            raise ValueError(f'Expected one illustration for {key}, got {count}')
    return rendered, toc


def toc_html(toc: list[tuple[int, str, str]]) -> str:
    items = ''.join(
        f'<li class="{"sub" if level == 3 else "top"}"><a href="#{anchor}">{html.escape(label)}</a></li>'
        for level, anchor, label in toc
    )
    return f'<ol>{items}</ol>'


def render_knowledge(repo: Path = Path('.')) -> Path:
    from .knowledge_art import render_illustrations

    render_illustrations(repo)
    source = (repo / 'content/knowledge' / f'{SLUG}.md').read_text(encoding='utf-8')
    rendered, toc = render_article(source)
    output = repo / 'docs/knowledge'
    output.mkdir(parents=True, exist_ok=True)
    links = toc_html(toc)
    core_anchor = next(anchor for _, anchor, label in toc if label.startswith('三、'))
    scenarios_anchor = next(anchor for _, anchor, label in toc if label.startswith('五、'))
    visual_links = ''.join(
        f'<a href="#diagram-{key}"><span>0{index}</span>{label}</a>'
        for index, (key, label, _, _) in enumerate(DIAGRAMS, 1)
    )
    article = (
        '<nav class="knowledge-breadcrumb" aria-label="面包屑">'
        '<a href="../index.html">首页</a> / <a href="index.html">AI 知识科普</a> / 生态与术语</nav>'
        '<div class="knowledge-layout"><aside class="knowledge-toc" aria-label="本文目录">'
        f'<h2>本文目录</h2>{links}</aside><article class="knowledge-article">'
        f'<p class="eyebrow">AI 知识科普 · 01</p><h1>{TITLE}</h1>'
        f'<div class="knowledge-meta"><span>资料查证：<time datetime="{VERIFIED}">{VERIFIED}</time></span>'
        '<span>7 个观察层 · 73 个代表作品 · 5 组示意图</span><span>AI 辅助整理 · 含官方来源</span></div>'
        '<nav class="knowledge-visual-index" aria-label="五张图快速阅读"><p>先看图，再读正文</p>'
        f'<div>{visual_links}</div></nav>'
        '<details class="knowledge-mobile-toc"><summary>展开本文目录</summary>'
        f'{links}</details><div class="article-body">{rendered}</div>'
        '<div class="knowledge-end"><a href="index.html">← 返回 AI 知识科普</a> · '
        '<a href="../tools/index.html">浏览 AI 工具目录</a> · <a href="../courses/index.html">开始系统学习</a>'
        '</div></article></div>'
    )
    article_path = output / f'{SLUG}.html'
    article_path.write_text(page_shell(TITLE + ' · VORASIO', DESCRIPTION, article), encoding='utf-8')
    layer_map = ''.join(
        f'<li><a href="{SLUG}.html#layer-{i}"><b>0{i}</b><span>{name}</span><small>{count}</small></a></li>'
        for i, (name, count) in enumerate(LAYERS, 1)
    )
    hub = (
        '<section class="knowledge-hub"><header class="knowledge-hero">'
        '<p class="eyebrow">AI KNOWLEDGE · 概念与应用</p><h1>AI 知识科普</h1>'
        '<p class="lead">从模型到真实应用，读懂 AI 怎样工作。用代表作品认识生态，用具体场景理解术语。</p>'
        '<p class="knowledge-stats"><span>7 个观察层</span><span>73 个代表作品</span>'
        '<span>Model / Harness / Agent / Vibe coding</span></p></header>'
        '<article class="knowledge-card"><div><p class="eyebrow">入门长文 · 01</p>'
        f'<h2><a href="{SLUG}.html">{TITLE}</a></h2>'
        '<p>五组示意图串起七个观察层、核心术语和三个应用场景。'
        '先看生态地图与概念关系，再查阅 73 个代表作品及其官方来源。</p>'
        f'<p class="disclosure">资料查证：{VERIFIED} · 按家族与项目收录，非性能排行榜</p></div>'
        f'<a class="read-link" href="{SLUG}.html">阅读全文 →</a></article>'
        '<h2>从哪一层开始了解？</h2><p class="disclosure">按主要用途分类；编程与通用应用是应用层的两条分支。</p>'
        f'<ol class="knowledge-layer-map">{layer_map}</ol>'
        '<section class="knowledge-path"><h2>建议阅读顺序</h2><ol>'
        f'<li><a href="{SLUG}.html#section-1">先看生态全貌</a>：分清模型能力与产品能力。</li>'
        f'<li><a href="{SLUG}.html#{core_anchor}">再理解四个核心术语</a>：模型、Harness、Agent 与 Vibe coding。</li>'
        f'<li><a href="{SLUG}.html#{scenarios_anchor}">用应用场景串起来</a>：竞品研究、内部知识助手与读书应用。</li>'
        '</ol><p>想亲手练习？前往 <a href="../courses/index.html">AI 学习路线</a>；'
        '想按能力查找工具？前往 <a href="../tools/index.html">AI 工具目录</a>。</p></section></section>'
    )
    (output / 'index.html').write_text(page_shell('AI 知识科普 · VORASIO', DESCRIPTION, hub), encoding='utf-8')
    return article_path


if __name__ == '__main__':
    print(render_knowledge())
