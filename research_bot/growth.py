"""Static subscription and enquiry pages; no visitor data is collected here."""
from __future__ import annotations

import html
import json
import re
from pathlib import Path


def load_config(path: Path = Path('config/growth.json')) -> dict:
    try:
        value = json.loads(path.read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def whatsapp_url(config: dict) -> str:
    number = str(config.get('whatsapp_number', '')).strip().removeprefix('+')
    return f'https://wa.me/{number}' if re.fullmatch(r'[1-9][0-9]{6,14}', number) else ''


def render_growth_pages(config: dict | None = None, site_dir: Path = Path('docs')) -> None:
    from .site import shell

    config = load_config() if config is None else config
    destination = whatsapp_url(config)
    site_dir.mkdir(parents=True, exist_ok=True)
    subscription = '''<article class="growth-page"><p class="eyebrow">关注 AI 的变化，也关注实际用途</p>
<h1>订阅 AI 精选资讯</h1><p>公开阅读模型、Agent、开发工具与智能硬件资讯。通过 RSS 阅读器接收站点更新，自主决定阅读频率。</p>
<section class="growth-card"><h2>RSS 订阅已开放</h2><p>将下面的订阅源地址添加到你使用的 RSS 阅读器。RSS 不要求在本站登记邮箱或手机号。</p>
<a class="growth-button" href="feed.xml">打开 RSS 订阅源</a><p><a href="index.html">先浏览最新资讯 →</a></p></section>
<section class="growth-card"><h2>从资讯走向项目</h2><p>如果你正在规划 AI 软件或 AI 硬件项目，可以先整理目标、现有条件与验收标准，
再讨论下一步。</p>
<a href="services.html">整理项目需求 →</a></section><p>邮件订阅与付费订阅尚未开放。本站不会把 RSS 订阅视为商业联系许可。</p>
<p><a href="privacy.html">资料使用说明</a></p></article>'''
    contact = (
        f'<a class="growth-button" data-whatsapp href="{html.escape(destination, quote=True)}" '
        'target="_blank" rel="noopener noreferrer">打开 WhatsApp，讨论需求 ↗</a>'
        if destination else '<p class="growth-notice">WhatsApp 联系入口待配置。你仍可以整理并复制需求摘要；当前不会发送给任何人。</p>'
    )
    consult = '''<article class="growth-page"><p class="eyebrow">AI 软件 · AI 硬件 · 软件与设备协同</p><h1>把项目想法整理成可讨论的需求</h1>
<p>从业务问题出发，说明希望实现的结果。以下工具只在当前浏览器生成需求摘要，不提交资料。</p>
<form id="project-brief" class="growth-card"><fieldset disabled data-brief-fields>
<label>项目方向<select name="direction"><option>AI 软件</option><option>AI 硬件</option>
<option>软件与硬件协同</option><option>尚在探索</option></select></label>
<label>希望解决的问题<textarea name="problem" maxlength="2000" placeholder="谁在什么场景下，遇到什么问题？"></textarea></label>
<label>目标用户与使用场景<textarea name="audience" maxlength="1000"></textarea></label>
<label>现有条件<textarea name="resources" maxlength="1000" placeholder="例如已有产品、数据授权、设备、接口或团队"></textarea></label>
<label>期望交付与验收方式<textarea name="outcome" maxlength="1000" placeholder="什么结果能说明项目有效？"></textarea></label>
<label>期望时间与预算范围（选填）<input name="constraints" maxlength="300"></label>
<p class="growth-notice">请勿填写密码、API 密钥、客户个人资料或未获授权的保密材料。可先用概括描述。</p>
<button class="growth-button" type="submit">生成需求摘要</button></fieldset></form>
<section class="growth-card"><h2>需求摘要</h2><textarea id="brief-output" rows="12" readonly aria-label="生成的需求摘要"></textarea>
<button id="copy-brief" type="button">复制摘要</button><p id="brief-status" role="status" aria-live="polite"></p>''' + contact + '''
<p>如 WhatsApp 已配置，请复制摘要后自行粘贴、检查并发送。打开联系入口不会自动发送消息。
项目范围、可行性与合作安排需双方进一步确认。</p></section>
<noscript><p>启用 JavaScript 后可生成摘要；
也可以自行按上述字段整理需求。</p></noscript><p><a href="privacy.html">资料使用说明</a> · <a href="subscribe.html">
订阅资讯</a></p></article>'''
    privacy = '''<article class="growth-page article-body"><h1>资料使用说明</h1><h2>公开内容与 RSS</h2>
<p>公开文章和 RSS 可直接访问。本站当前没有邮箱订阅登记、付费订阅或会员账户。</p><h2>需求整理工具</h2>
<p>需求字段只在当前页面内用于生成摘要，不上传到本站服务器，不写入浏览器持久存储。刷新或离开页面后内容可能丢失。点击复制会将摘要写入你的设备剪贴板。
摘要可包含站内来源路径，但不包含链接查询参数和片段。</p>
<h2>WhatsApp 联系</h2><p>点击联系入口会离开本站并访问 WhatsApp。只有你自行发送的内容才会进入聊天；此工具不会自动提交需求。
发送前请检查摘要，避免包含密钥、客户个人资料或未经授权的保密信息。</p>
<p>WhatsApp 的账户、聊天和数据处理由其服务规则管理。若希望更正或删除已发送的需求，请在原聊天中提出。资讯订阅和项目咨询是两个独立选择。</p>
<h2>网站访问</h2><p>网站托管服务可能处理常规访问日志。此需求整理工具没有增加分析追踪器或广告 Cookie。</p>
<p><a href="subscribe.html">订阅资讯</a> · <a href="services.html">整理项目需求</a> · <a href="index.html">返回首页</a></p></article>'''
    for filename, title, body in (
        ('subscribe.html', '订阅 AI 精选资讯', subscription),
        ('services.html', 'AI 软件与硬件项目需求', consult),
        ('consult.html', 'AI 软件与硬件项目需求', consult),
        ('privacy.html', '资料使用说明', privacy),
    ):
        page = shell(title, title + ' · VORASIO', body)
        page = page.replace(
            '</head>',
            '<script defer src="assets/growth.js"></script></head>',
        )
        (site_dir / filename).write_text(page)


def render_growth() -> None:
    """Build public growth pages using the checked-in site configuration."""
    render_growth_pages()
