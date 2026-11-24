# VORASIO AI × 智能硬件研究

<!-- EDITORIAL_CHARTER_START -->
## 品牌、使命与编辑章程

**以求证理解智能，以实践创造价值。**

Understand AI through evidence. Create value through practice.

VORASIO 是面向 AI 开发者与智能硬件实践者的自动化技术研究媒体。使命是把分散的 AI 技术信息转化为可信、清晰、可行动的知识，帮助读者做出更好的技术决策。愿景是成为连接 AI 研究与实际应用的可信知识平台。

文化：保持好奇，认真求证，坦诚表达，持续修正。以上理念作为内部编辑约定执行，首页不展示标语、价值观或宣言式文案，以内容和发布状态为主。

| 价值观 | 执行约定 |
|---|---|
| 求真 | 事实必须可回查，数字保留实验条件；区分事实、作者主张和分析推断；摘要缺失时不补造信息。 |
| 独立 | 按相关性与信息增量选题，不将营销宣传当成事实；单篇研究不代表行业共识。 |
| 实用 | 写清适用对象、前提、限制和验证步骤；教程只有实际运行通过才可标注“已验证”。 |
| 克制 | 跨栏目、跨天去重；没有可靠更新就如实说明；不用“最强、颠覆、必看”等无证据措辞。 |
| 尊重 | 保留署名与来源，尊重版权、隐私和读者注意力；不虚构真人团队、亲测经历或个人动机。 |
| 可纠正 | 保存来源和版本记录，重要错误修订后明确说明；完整性检查通过不等于事实已全部核实。 |

岗位与权限：出版人（站点所有者）决定方向、预算和章程；总编辑由章程及内容日历约束选题；研究员由来源采集程序承担；选题编辑由相关性与去重程序承担；技术作者由 Groq 承担；核查发布由来源及输出校验程序承担；技术验证由隔离的测试流程承担；产品运营由网站模板、发行程序和执行记录承担。上述是系统职责分工，不代表存在真人编辑团队。

免费资源必须区分免费层、限时试用、赠送额度和待核验线索，列明来源已披露的额度、期限、信用卡、地区和续费条件，未披露则写“未确认”。搜索结果只作线索，未经官方条件核验不得标为“已确认免费”。没有新结果时明确告知，不为每日更新重复推荐。

发布顺序：采集 → 相关性筛选 → 全局去重 → 据来源写作 → 引用与完整性检查 → 发布或降级为来源摘要。开发实践默认标注“实践参考，未经运行验证”。页面保留来源和发布日期，空档、待核验和降级内容必须明确标示。
<!-- EDITORIAL_CHARTER_END -->

基于 GitHub Actions、Groq 和 Telegram 的自动化研究系统。系统采集公开技术资料，经过日期过滤与全局去重后生成带来源编号的中文研究简报，发布到 GitHub Pages；Telegram 仅发送文章标题和网页链接。

AI 学习课程采用整套生成、AI 自查、代码实测后全量发布的方式，不建设课程后台或逐日定时释出。需求见 [`planning/COURSE_PLATFORM_REQUIREMENTS.md`](planning/COURSE_PLATFORM_REQUIREMENTS.md)，阶段 1 的确定性校验工具见 [`course_system/README.md`](course_system/README.md)。

AI 生态工具目录按“先证据、后页面”的顺序实施。阶段 A、B 已完成：首批公开 14 条经官方来源核验的开源本地项目，并提供搜索、领域与使用方式筛选；不发布空分类，不把软件开源误写成模型、硬件或外部服务免费。扩充大陆/海外与免费层/试用/付费产品属于下一阶段，规则见 [`planning/AI_TOOLS_DIRECTORY_REQUIREMENTS.md`](planning/AI_TOOLS_DIRECTORY_REQUIREMENTS.md)。

## 当前日报流程（北京时间 UTC+8）

| 时间 | 执行内容 | 是否公开 |
|---:|---|---|
| 09:00 | 轮到的第一个 AI 领域：采集、去重、生成并校验 | 否，保存批次回执 |
| 13:00 | 下一个 AI 领域：同样独立处理 | 否，保存批次回执 |
| 17:00 | 下一个 AI 领域：同样独立处理 | 否，保存批次回执 |
| 18:00 | 汇总当天通过校验的领域，生成一篇日报 | 至少一个领域通过才发布；否则只更新状态，不发通知 |

十个领域按[领域导航](docs/domains/index.html)的顺序连续轮换，跨天不重置；漏跑或某领域不通过不会改变轮转顺序。每批按自己的计划时刻截止，补跑不把迟到的新资料带入已经划定的窗口。18:00 封版后不再补做本期领域批次。

日报只有一个生产执行器：[`_rotation.yml`](.github/workflows/_rotation.yml)。[`editorial-day.yml`](.github/workflows/editorial-day.yml) 按 UTC cron `0 1,5,9,10 * * *` 启动，[`catchup.yml`](.github/workflows/catchup.yml) 负责到点后重试和恢复。两个入口在默认分支也可手动触发，但只执行当前应做事项，不能提前发布。

- 其他领域失败，不会挡住已通过的领域。可选「其他」须通过独立的官方来源配置校验，不能单独生成一篇日报。
- 先提交日报与待部署回执，再部署 GitHub Pages。部署成功后，先提交当天通知领取记录，再尝试发送一次通知；恢复不重新生成已封版日报，不自动重试可能已送达的通知。
- 首页保留最近已发布的日报，旧链接、归档、RSS 和站点地图按原路径访问。原始来源以及发布状态仍然可以核对。

README 的编辑章程区间是生成提示的唯一章程来源。自动校验是发布门槛，不保证所有结论都正确；关键结论仍须回查原始资料。

## 研发协作

本仓库公开，贡献与交付按 [研发流程](planning/DEVELOPMENT_WORKFLOW.md) 执行。使用任务分支和隔离 worktree；内部角色配置、任务包、草稿与原始日志保存在仓库外。新任务可使用 [任务模板](planning/TASK_TEMPLATE.md)，代理入口为 [AGENTS.md](AGENTS.md)。

## 仓库结构

```text
.
├── .github/          # CI、定时编辑、发布与公开贡献模板
├── .agents/          # 可公开的项目技能
├── research_bot/     # 采集、编辑、生成、状态与通知
├── course_system/    # 课程校验、预览与发布
├── agent_bridge/     # 本地 A2A 审查服务实现
├── infrastructure/   # 基础设施配置
├── config/           # 不含凭据的运行配置
├── content/          # 可公开内容源
├── docs/             # GitHub Pages 发布页面与资源
├── state/            # 正式去重及发布状态
├── tests/            # 测试与合成资料
├── planning/         # 公开需求、架构与贡献规范
├── reports/          # 本地报告输出，正文不随源码或 CI artifact 公开
├── AGENTS.md         # 代理协作入口
├── pyproject.toml
└── requirements*.txt
```

内部角色配置、任务与原始日志放在仓库外；具体本地目录由开发环境维护。正式流程只公开必要的来源、稿件与回执；测试 fixture 与成功构建记录不代表生产已发布。

## 来源与筛选

日报按当前领域选择已配置的来源池，而非每天扫过所有栏目。论文和行业资料主要来自 arXiv、书目索引、官方项目版本与公开技术资料。来源配置见 `config/sources.yml`，实际领域与关键词映射见 `research_bot/rotation_collect.py`。可选「其他」仅来自 `config/rotation_other.yml` 已人工确认的残余资料。

每批只接受符合其日期窗口、主题、链接与摘要要求的条目。精确日期不得晚于该批计划截止；只有日期而无时刻的资料按自然日处理。使用 DOI、arXiv 基 ID、规范化 URL 等标识消除重复。只保留通过校验的批次供当天合成；未发布资料不会记为正式已读。

`state/rotation/` 保留轮转与部署回执，`state/slots.json` 保留日期任务状态，`state/seen.json` 保留正式发布去重与通知成功回执。失败原因不等同于没有新资料。

## 部署

1. 新建 GitHub 仓库，把本目录全部提交到默认分支。
2. 仓库 **Settings → Actions → General → Workflow permissions** 选择 **Read and write permissions**。
3. 在 Groq Console 新建单独项目和 API key。建议给项目设置保守的模型限额，避免与其他应用抢组织额度。
4. 在 Telegram 与 `@BotFather` 创建 bot，先向 bot 发一条消息；调用 `getUpdates` 查到私聊 `chat.id`。群组则先邀请 bot，并使用群组的负数 chat ID。
5. 仓库 **Settings → Secrets and variables → Actions** 新增 Repository secrets：

   - `GROQ_API_KEY`
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `NTFY_TOPIC`（可选；使用高熵随机主题名，不要写入仓库）
   - `NTFY_TOKEN`（仅在 ntfy 服务器启用访问令牌时需要）

   ntfy 默认服务器是 `https://ntfy.sh`。如需自托管，可新增仓库变量
   `NTFY_BASE_URL`，值必须是无路径、无凭据的 HTTPS 地址。配置 `NTFY_TOPIC`
   后，成功发布的晚间日报可同时推送到 Telegram 和 ntfy；无有效日报时不发送。

6. 仓库 **Settings → Pages → Build and deployment → Source** 选择 **GitHub Actions**。工作流用 GitHub 官方 Pages actions 直接上传并部署 `docs/`，同时把生成文章提交回仓库留档。首次发布完成后会得到 `https://<用户>.github.io/<仓库>/`。
7. 可选 Repository variables：

   - `GROQ_MODEL`：默认 `openai/gpt-oss-20b`；模型是否仍可用以及准确额度，以 Groq Console 的 Models / Limits 页面为准。
   - `PUBLIC_BASE_URL`：使用自定义域名或 Pages 地址不是默认形式时设置，末尾不要加 `/`。普通项目 Pages 会自动推导，无需设置。

8. 先看 **Validate rotation changes offline** 的 CI 结果。上线后，在 Actions 核对默认分支生产任务、Pages 部署与回执；不要把手动触发当成不写入的测试。需要检查当天是否有工作，可以从仓库根目录执行只读的 `python -m research_bot.rotation --plan`。

不要把 key 写进 YAML、日志、`.env` 或提交历史。生产执行仅接收默认分支定时和手动触发。PR 校验只用合成数据与只读权限，不部署、不通知，不向来自 fork 的 PR 暴露 secrets。

## 校验与投递

- 每次领域采集最多选 3 项送入一次 Groq 分析；没有合格来源就不调用模型。默认最大输出 2800 token。HTTP 限流或暂时失败按客户端退避。
- 只依据提供的标题、摘要、日期、原始链接写作。首节结论须逐条引证，数字不得脱离来源，无法确认的信息如实标明。截断、降级输出和未通过校验的草稿都不发布。
- 日报保留在 `docs/posts/YYYYMMDD-daily.html`。同日重跑不覆盖已存在的日报。网站保留原始来源与引用，不把模型分析当成事实复核。
- 18:00 后且当天 Pages 部署成功，才可尝试一次通知；可选 ntfy 发送同一条日报。先持久化通知领取记录，再调用通知，避免断线后重复发送。若发送结果不明，不自动重试；这不是送达恰好一次的保证。跨日恢复不会补发旧通知。

## 本地测试

建议 Python 3.13：

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
pytest -q
ruff check .
```

离线测试通过 mock 验证调度、去重、汇总和恢复，不需要模型 key。若只需查看主流程当前计划，用：

```bash
python -m research_bot.rotation --plan
```

该命令只读状态，不采集、不调用模型、不部署。专题来源预览仍可按专题单独运行；它不是日报发布入口。

## 服务边界与成本

### 调度可靠性与漏跑恢复

- 调度与日历日统一为 `Asia/Taipei`（UTC+8，与北京时间相同）。九点、十三点、十七点只生成领域草稿；十八点是合成计划，GitHub 可能晚启动。
- GitHub 的备用入口在 UTC 01–15 时每小时 19、49 分检查。可重试的批次间隔至少 30 分钟、最多 2 次；超过 18:00 不补做。已封版而尚未完成部署或记账的内容可在恢复窗口内继续，使用原稿而不重新生成。
- 所有正式写入共享 `editorial-state-writer-v1`，从当前默认分支读状态。默认分支移动时停止，后续任务从最新状态恢复，不强推覆盖。
- 独立 [Cloudflare 触发器](infrastructure/cloudflare/README.md) 仍调用同一个 `catchup.yml`。它不选择领域、不接触模型或通知密钥；两个平台的状态和 GitHub 队列均可能影响实际时间。

### 已接入的补充来源

| 来源 | 接入与筛选方式 | 边界 |
|---|---|---|
| OpenAlex | 官方 API，按主题检索及真实出版日期过滤 | 需要 Actions secret `OPENALEX_API_KEY`；通过 Authorization 请求头传递，不写入仓库或 URL |
| ACL Anthology | 官方 RSS 发现论文，再读取论文页的摘要和出版日期 | RSS 包含旧论文更正和非论文记录；不把更正时间当作论文日期 |
| CVF Open Access | 官方会议档案和论文页摘要 | 连接器保留，供来源检查和日后会议周使用。CVPR 2026 档案日为 2026-05-23，不在每日滚动窗口内，因此已退出每日多模态栏目 |
| Crossref | 官方 works API，出版日期过滤、DOI 去重 | 很多记录不提供摘要；没有摘要的条目不用于深度分析 |
| GitHub | 官方 Releases API | 工作流自带 token，排除草稿和预发布；原有官方 RSS 继续保留 |
| NVIDIA 技术博客 | 官方 RSS | 视作厂商技术资料，而非独立评测；仍需核验测试条件 |

OpenReview 不启用。arXiv 继续保留为补充来源，各来源失败分别记录，不影响其他可用来源。OpenAlex 和 Crossref 按研究方向配置查询；所有结果仍经过栏目关键词、日期窗口及可用摘要过滤，不是直接搬运检索结果。

跨来源去重采用 DOI、规范化 URL 和规范化标题；跨天保存于现有状态文件，继续由共享并发锁保护写入。只有年份或月份的出版日期保守取该周期第一天并标记精度，不用索引更新时间代替出版时间。缺摘要不会由模型补写。

在 Actions 手动运行 **Source connector checks** 可只验证这六类连接器：不调用 Groq、不发布网页、不发 Telegram。ACL/CVF 使用较宽的诊断窗口检验解析器，诊断命中不代表今天有新资料。

OpenAlex 注册免费使用有每日预算及速率限制，以官方账户面板为准；Crossref、ACL、CVF 和 NVIDIA 的公开访问不代表无限请求或可任意转载。GitHub API 也受 token 对应的速率限制。采集使用串行请求、数量上限及退避，网站仅呈现研究解读与原始链接。官方说明：[OpenAlex](https://docs.openalex.org/)、[ACL](https://aclanthology.org/faq/api/)、[CVF](https://openaccess.thecvf.com/)、[Crossref](https://www.crossref.org/documentation/retrieve-metadata/rest-api/)、[GitHub Releases](https://docs.github.com/en/rest/releases/releases)、[NVIDIA](https://developer.nvidia.com/blog/)。

- GitHub Actions：公开仓库使用标准 GitHub-hosted runner 通常免费；私有仓库按账户方案有免费分钟和存储额度，超出后计费。cache 每仓库有独立额度，artifact 计入存储。具体数字会随方案变化，以 Billing 页面为准。
- Groq：有免费计划，但速率和日额度因模型/组织而异；达到任一维度会返回 429。Developer 是付费按量方案，Flex/Batch 等能力可能仅限付费层。
- Telegram Bot API：这里使用普通 HTTPS Bot API；官方没有为这种低频单聊天推送收取 API 费用，但有消息长度和发送速率等限制。
- arXiv：公开 API 不是 SLA 服务。代码设置 User-Agent、串行请求和退避；若扩充来源，应遵守各来源条款、robots 和速率限制。

## 可选增强

若不希望机器人提交污染默认分支，可把状态迁移到独立对象存储（例如带条件写入/版本控制的 S3 兼容桶）或数据库；届时需实现原子 compare-and-swap。不要仅换成 Actions cache，因为 cache key 创建后不可更新且会回收，不能提供长期一致性。

## 网页上的日报状态

只有存在有效文章才显示已发布；没有有效稿不会生成空日报。公开回执 `docs/slot-status.json` 只保留可公开的状态字段，不含待发正文、密钥或内部请求。状态随 Pages 发布更新，不能把状态更新当成新文章或推送。

# 分析模型

仅使用 Groq 生成分析；服务异常时不切换到其他模型，也不发布未通过质量检查的内容。历史文章保留原生成来源。


## AI 知识科普专区

- 专区入口：`docs/knowledge/index.html`（线上 `/knowledge/index.html`）。
- 首篇文章：`docs/knowledge/ai-ecosystem-guide.html`，包含七个生态观察层、73 个代表作品、核心术语及应用场景。
- 内容源文件：`content/knowledge/ai-ecosystem-guide.md`；资料核验日期、产品名称与链接需随文章修订更新。
- 重新生成：`python -m research_bot.knowledge`，使用项目现有 `markdown-it-py` 依赖；同时生成五组示意图的桌面与手机 SVG 版本。
- 图示生成器：`research_bot/knowledge_art.py`；图源位于 `docs/assets/knowledge/`，正文配有图注、替代文本与快速跳转。
- 专区独立于定时简报；首页入口保存在 `research_bot/timeline.py`，导航保存在站点模板中，后续日报生成会保留入口。
