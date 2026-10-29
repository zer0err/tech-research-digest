"""Generate responsive, accessible SVG explanations for the AI knowledge guide."""
from __future__ import annotations

from html import escape
from pathlib import Path

GREEN = '#176453'
INK = '#192522'
MUTED = '#596b61'
LINE = '#ccd6cd'
PAPER = '#f8f7f1'
SOFT = '#e8f0e9'
GOLD = '#956924'


class Drawing:
    def __init__(self, width: int, height: int, title: str, desc: str, mobile: bool):
        self.width, self.height, self.mobile = width, height, mobile
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
            f'<title id="title">{escape(title)}</title><desc id="desc">{escape(desc)}</desc>',
            '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#176453"/></marker></defs>',
            f'<rect width="{width}" height="{height}" rx="16" fill="{PAPER}"/>',
        ]

    def rect(self, x, y, w, h, fill='white', stroke=LINE, dash=False):
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{fill}" stroke="{stroke}" stroke-width="1.5"'+(' stroke-dasharray="7 5"' if dash else '')+'/>')

    def text(self, x, y, lines, size=18, color=INK, bold=False, anchor='start', gap=None):
        if isinstance(lines, str):
            lines = [lines]
        gap = gap or size * 1.55
        for i, line in enumerate(lines):
            self.parts.append(f'<text x="{x}" y="{y+i*gap}" fill="{color}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Noto Sans SC,Microsoft YaHei,sans-serif" font-size="{size}" font-weight="{650 if bold else 400}" text-anchor="{anchor}">{escape(line)}</text>')

    def arrow(self, x1, y1, x2, y2, path=None, dash=False):
        d = path or f'M{x1},{y1} L{x2},{y2}'
        self.parts.append(f'<path d="{d}" fill="none" stroke="{GREEN}" stroke-width="2" marker-end="url(#arrow)"'+(' stroke-dasharray="5 4"' if dash else '')+'/>')

    def box(self, x, y, w, h, title, lines=(), accent=False):
        self.rect(x, y, w, h, GREEN if accent else 'white', GREEN if accent else LINE)
        self.text(x+18, y+31, title, 18 if self.mobile else 20, 'white' if accent else GREEN, True)
        self.text(x+18, y+61, lines, 16 if self.mobile else 17, '#e0eee6' if accent else MUTED)

    def finish(self):
        return ''.join(self.parts) + '</svg>\n'


def ecosystem(mobile):
    title='AI 生态的七个观察层'
    desc='模型、推理接入、知识工具支持智能体运行与业务搭建，最终形成编程应用及通用专业应用。各层可以直接组合，并非每个产品都需要全部层。'
    if mobile:
        d=Drawing(360,1000,title,desc,True)
        d.text(20,34,'能力怎样变成产品？',21,bold=True)
        d.text(20,62,'按角色读图，并非固定技术流水线',15,MUTED)
        entries=[('01 模型','理解、推理、生成'),('02 推理与接入','运行模型 · 提供调用入口'),('03 知识与工具','查资料 · 读文件 · 操作网页'),('04 框架与运行时','执行、记进度、处理错误'),('05 工作流与搭建','业务流程 · 连接系统 · 发布')]
        for i,(label,note) in enumerate(entries):
            y=92+i*136
            d.box(20,y,320,104,label,[note],i==3)
            if i<4:d.arrow(180,y+108,180,y+130)
        d.arrow(180,744,180,771)
        d.text(180,800,'应用层的两条分支',17,GREEN,True,'middle')
        d.box(20,822,320,72,'06 编程与软件创造',['开发 · 调试 · 创建应用'])
        d.box(20,909,320,72,'07 通用与专业应用',['研究 · 办公 · 视觉与语音'])
    else:
        d=Drawing(900,664,title,desc,False)
        d.text(30,40,'能力怎样变成产品？',25,bold=True)
        d.text(30,72,'先看基础能力，再看执行组织，最后看用户拿到什么。',18,MUTED)
        cards=[('01 模型',['理解 · 推理 · 生成']),('02 推理与接入',['运行模型 · 提供调用入口']),('03 知识与工具',['检索资料 · 连接外部操作'])]
        for i,(label,note) in enumerate(cards):
            x=30+i*286
            d.box(x,105,268,104,label,note)
            d.arrow(x+134,214,x+134,255)
        d.box(30,265,840,92,'04 智能体框架与运行时 / Harness',['执行循环 · 上下文 · 工具调度 · 状态与恢复'],True)
        d.arrow(450,362,450,390)
        d.box(30,400,840,92,'05 工作流与搭建平台',['将模型、工具与执行能力组合成业务流程'])
        d.arrow(450,497,450,516)
        d.arrow(450,516,236,546,path='M450,516 L236,516 L236,546')
        d.arrow(450,516,664,546,path='M450,516 L664,516 L664,546')
        d.box(30,553,412,86,'06 编程与软件创造',['代码修改 · 软件开发 · 应用原型'])
        d.box(458,553,412,86,'07 通用与专业应用',['研究 · 办公 · 图像 · 视频 · 语音'])
    return d.finish()


def relationship(mobile):
    title='Model、Harness 与 Agent 的关系'
    desc='Agent 是面向目标的完整系统。Harness 组织执行并调度模型、工具和状态；模型负责理解和生成，工具连接外部环境。'
    if mobile:
        d=Drawing(360,866,title,desc,True)
        d.text(20,34,'三个概念，各管什么？',21,bold=True)
        d.rect(14,63,332,692,SOFT,GREEN)
        d.text(30,96,'Agent：面向目标的完整系统',18,GREEN,True)
        d.text(30,124,'例：修复登录问题并验证结果',16,MUTED)
        d.rect(30,148,300,579,'white',GREEN,True)
        d.text(47,181,'Harness：组织与调度执行',18,GREEN,True)
        d.box(46,207,268,101,'Model / 模型',['理解信息，决定下一步'],True)
        d.arrow(180,313,180,342)
        d.box(46,352,268,94,'Tools / 工具',['读文件、改代码、运行测试'])
        d.arrow(180,452,180,481)
        d.box(46,490,268,94,'Context & State',['资料、任务进度、运行结果'])
        d.text(49,621,['权限 · 错误恢复 · 执行追踪','让每一步可管理、可检查'],16,MUTED)
        d.arrow(180,760,180,785)
        d.rect(20,797,320,50,'white')
        d.text(180,829,'外部环境：项目、浏览器、业务系统',16,INK,anchor='middle')
    else:
        d=Drawing(900,580,title,desc,False)
        d.text(30,40,'三个概念，各管什么？',25,bold=True)
        d.rect(30,68,840,407,SOFT,GREEN)
        d.text(52,102,'Agent：围绕目标观察、行动、检查的完整系统',22,GREEN,True)
        d.text(52,133,'例：修复登录问题，并把验证通过的修改交给用户。',18,MUTED)
        d.rect(55,155,790,291,'white',GREEN,True)
        d.text(77,190,'Harness：组织执行，调度模型、工具与状态',20,GREEN,True)
        d.box(80,215,310,142,'Model / 模型',['理解上下文','生成方案与工具调用请求'],True)
        d.box(480,215,340,142,'Tools / 工具',['读取和修改项目文件','运行测试，返回实际结果'])
        d.arrow(398,267,470,267)
        d.arrow(474,307,398,307)
        d.text(80,406,'Context & State：资料与进度     ·     权限、错误恢复与执行追踪',18,MUTED)
        d.arrow(650,479,650,505)
        d.rect(30,516,840,44,'white')
        d.text(450,544,'外部环境：代码库、文件、浏览器、业务系统',18,INK,anchor='middle')
    return d.finish()


def loop(mobile):
    title='智能体怎样通过反馈完成任务'
    desc='接收目标后查看信息，决定行动，调用工具，再检查结果。未完成时带着反馈继续；达到条件时交付；缺少权限或信息时请求人工帮助。'
    steps=[('01 接收目标','先明确什么叫完成'),('02 查看信息','读取当前资料和任务状态'),('03 决定行动','选择下一步与可用工具'),('04 执行并检查','调用工具，查看真实结果')]
    if mobile:
        d=Drawing(360,866,title,desc,True)
        d.text(20,34,'Agent 的关键：反馈循环',21,bold=True)
        for i,(label,note) in enumerate(steps):
            y=65+i*123
            d.box(32,y,296,91,label,[note],i==2)
            if i<3:d.arrow(180,y+96,180,y+116)
        d.arrow(180,530,180,554)
        d.rect(32,564,296,78,SOFT,GREEN)
        d.text(180,596,'达到完成条件了吗？',19,GREEN,True,'middle')
        d.text(180,622,'看结果，不能只看模型说完成',15,MUTED,anchor='middle')
        d.arrow(180,649,180,678)
        d.box(32,689,296,73,'完成 → 交付结果',['附上依据或验证结果'],True)
        d.arrow(28,606,28,224,path='M28,606 L12,606 L12,224 L28,224',dash=True)
        d.text(32,798,['未完成 → 带着反馈继续','缺少信息或权限 → 请人协助'],16,GOLD)
    else:
        d=Drawing(900,454,title,desc,False)
        d.text(30,40,'Agent 的关键：反馈循环',25,bold=True)
        d.text(30,72,'一个任务可能经历多轮观察、行动与验证。',18,MUTED)
        for i,(label,note) in enumerate(steps):
            x=30+i*219
            notes = [note] if i == 0 else [
                ['读取当前资料', '与任务状态'],
                ['选择下一步', '与可用工具'],
                ['调用工具', '查看真实结果'],
            ][i - 1]
            d.box(x,110,200,113,label,notes,i==2)
            if i<3:d.arrow(x+204,166,x+214,166)
        d.arrow(787,228,787,268)
        d.rect(620,280,267,100,SOFT,GREEN)
        d.text(754,316,'达到完成条件？',21,GREEN,True,'middle')
        d.text(754,350,'完成 → 交付结果',18,GREEN,anchor='middle')
        d.arrow(616,330,349,229,path='M616,330 L349,330 L349,229',dash=True)
        d.text(385,309,'未完成：带着反馈继续',18,GREEN)
        d.text(30,414,'缺少信息、权限或遇到无法处理的问题 → 请求人工帮助',18,GOLD)
    return d.finish()


def rag(mobile):
    title='RAG 与微调分别改变什么'
    desc='RAG 在使用时检索相关资料，把证据交给现有模型，通常不改变模型参数。微调用训练样本更新模型参数，以调整稳定行为或任务表现。'
    if mobile:
        d=Drawing(360,1000,title,desc,True)
        d.text(20,34,'查资料，还是调整模型？',21,bold=True)
        d.rect(14,62,332,441,'white',LINE)
        d.text(32,97,'RAG：把资料带进当前回答',19,GREEN,True)
        for y,label,note in [(121,'问题 + 资料库','检索相关片段'),(246,'现有模型 + 证据','基于资料生成回答')]:
            d.box(32,y,296,92,label,[note],y==246)
        d.arrow(180,220,180,238)
        d.text(32,383,['得到：有资料依据的回答','通常不修改模型参数'],16,GREEN)
        d.text(32,455,'适合：制度、手册、经常更新的资料',15,MUTED)
        d.rect(14,527,332,452,'white',LINE)
        d.text(32,563,'微调：通过训练调整模型',19,GOLD,True)
        d.box(32,590,296,92,'训练样本 + 基础模型',['输入示例，执行额外训练'])
        d.arrow(180,687,180,712)
        d.box(32,722,296,92,'参数更新后的模型',['调整任务行为或输出风格'],True)
        d.text(32,858,['得到：模型参数发生变化','仍需评测，仍可能需要检索'],16,GREEN)
        d.text(32,942,'适合：稳定的任务行为与表达模式',15,MUTED)
    else:
        d=Drawing(900,526,title,desc,False)
        d.text(30,40,'查资料，还是调整模型？',25,bold=True)
        for x in [30,465]:d.rect(x,72,405,430,'white')
        d.text(50,110,'RAG：把资料带进当前回答',21,GREEN,True)
        d.box(50,137,365,87,'问题 + 资料库',['先检索相关片段'])
        d.arrow(232,230,232,255)
        d.box(50,266,365,88,'现有模型 + 检索证据',['基于资料生成回答'],True)
        d.text(50,395,['通常不修改模型参数','适合：制度、手册与更新频繁的资料'],17,GREEN)
        d.text(485,110,'微调：通过训练调整模型',21,GOLD,True)
        d.box(485,137,365,87,'训练样本 + 基础模型',['执行额外训练'])
        d.arrow(667,230,667,255)
        d.box(485,266,365,88,'参数更新后的模型',['调整任务行为或输出风格'],True)
        d.text(485,395,['会修改模型参数','适合：稳定任务行为与表达模式'],17,GREEN)
        d.text(485,469,'两者可以结合，微调后仍可能需要 RAG。',15,MUTED)
    return d.finish()


def coding(mobile):
    title='三种 AI 编程方式的关注点'
    desc='Vibe coding 通过描述需求、运行和反馈探索原型；AI 辅助编程强调设计、审查和验证；规格驱动开发先明确需求与验收再实现。三者可结合，不是固定成熟度阶梯。'
    items=[('Vibe coding',['描述想法 → 生成与运行','看效果 → 继续反馈'],'关注：快速探索与原型'),('AI 辅助编程',['明确设计 → AI 协助实现','审查修改 → 测试验证'],'关注：理解、验证与维护'),('规格驱动开发',['写清需求与验收标准','AI 实现 → 对照标准验收'],'关注：需求边界与协作')]
    if mobile:
        d=Drawing(360,773,title,desc,True)
        d.text(20,34,'同样用 AI，工作方式不同',21,bold=True)
        for i,(title,lines,note) in enumerate(items):
            y=70+i*216
            d.box(20,y,320,185,title,lines,i==1)
            d.text(38,y+151,note,16,'#e0eee6' if i==1 else GREEN)
        d.text(20,744,'可以组合使用，不是固定的升级阶梯。',16,MUTED)
    else:
        d=Drawing(900,382,title,desc,False)
        d.text(30,40,'同样用 AI，工作方式不同',25,bold=True)
        d.text(30,72,'区别主要在人怎样组织工作、审查和验收。',18,MUTED)
        for i,(title,lines,note) in enumerate(items):
            x=30+i*287
            d.box(x,105,266,200,title,lines,i==1)
            d.text(x+18,270,note,16,'#e0eee6' if i==1 else GREEN)
        d.text(30,350,'可以先探索原型，再补齐规格与验证；三种方式可以结合。',18,MUTED)
    return d.finish()


ILLUSTRATIONS = {
    'ecosystem': ecosystem,
    'model-harness-agent': relationship,
    'agent-loop': loop,
    'rag-vs-finetuning': rag,
    'ai-coding-methods': coding,
}


def render_illustrations(repo: Path = Path('.')) -> None:
    output=repo/'docs/assets/knowledge'
    output.mkdir(parents=True,exist_ok=True)
    for name, draw in ILLUSTRATIONS.items():
        for mobile in (False,True):
            suffix='-mobile' if mobile else ''
            (output/f'{name}{suffix}.svg').write_text(draw(mobile),encoding='utf-8')


if __name__=='__main__':
    render_illustrations()
    print('Rendered five desktop/mobile SVG diagram pairs.')
