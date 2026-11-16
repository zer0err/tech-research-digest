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

## 自动编辑日（Asia/Taipei）

| 时间 | 栏目 | 形式 |
|---:|---|---|
| 09:00 | VORASIO AI 日报 | 当天唯一公开稿。采集各主题来源，合并成一篇；没有合格来源则不发布 |

每周七天同一时刻运行。工作流使用 UTC cron，09:00（UTC+8）对应 `0 1 * * *`。日期、到点判断和采集截止都使用 `Asia/Taipei`。该时区与过去使用的 `Asia/Shanghai` 同为 UTC+8，且都没有夏令时，历史 `+08:00` 时间戳的日历日不变。

采集窗口的有效上界是当天 09:00，而不是补跑时的墙钟。来源过滤本身会把“现在”再放宽 2 小时，所以传给采集器的时钟是 07:00，放宽后刚好停在 09:00。精确到时刻、且晚于 09:00 的条目留到下一期。只标到日期、且该日已经开始的资料可以进入本期。这样早上的一期刊出的是此前的消息，不会把当天下午的新条目写进来。

GitHub Actions 的 cron 可能晚启动。09:00 之后的 catchup 只补这一期，到点即止，不另开时段。这不保证准点送达，也不能在跨过午夜后自动补写前一天。

首页按日期列出日报，旧的分栏地址转到对应日期的日报，不进入归档、搜索、RSS 或站点地图。页面以黑、白和中性灰为主，大字号与留白优先，并跟随系统浅色或深色外观；动效遵循系统减少动态效果设置。

README 中标记区间是编辑章程的唯一来源，生成提示直接读取它；网站“关于”页仅介绍内容来源与状态。`preview-day.yml` 的 `test`（默认）只预览入选条目，不调用模型、不发布、不通知、不写正式去重状态。需要模型试稿时，给 `_editorial.yml` 传入 `analyze=true`。`production` 才真实发布。定时任务固定使用 production。

“新”指日期窗口内尚未正式发布的资料，不是“程序从未抓过”。今日日报表示当天 09:00 这一期，覆盖各主题在截止时刻之前的滚动窗口，并不要求所有来源都在今天发表。清理测试内容后应排除对应测试状态，不得保留为正式已读记录。正式投递同时保存逐篇 publication 清单，便于后续精确核对。

Actions 的 `decision-*.json` 分别记录来源失败、无窗口内匹配资料、摘要不足、已经正式发布、分析接口失败、分析校验不通过及准备发布，附候选数量；不能把这些原因统称为“今日没有新内容”。自动校验只是一道门禁，不是事实正确性的保证。

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

内部角色配置、任务与原始日志放在仓库外；具体本地目录由开发环境维护。CI 审计附件仅导出决策标识与计数，不打包原始报告。

## 来源与筛选

论文研究使用 arXiv 官方 Atom API；开源、开发和生态栏目使用项目 Releases/Commits Atom、GitHub、Google AI 与 Hugging Face 等公开来源。各栏目配置独立的时间窗、关键词、条目上限和分析重点，详见 `config/sources.yml`。

晨间免费资源雷达通过公开搜索 RSS 发现线索，并将其标记为 `resource`。模型必须区分永久免费层、限时试用、赠送额度和待核验线索；仅凭标题不能确认免费。全局状态保证同一链接不会跨天重复推荐。当天没有新的可信条目时，页面由程序固定写入“今日未发现新的、可由公开来源确认的免费资源”，不会让模型补造结果。

采集只接受带有效发布日期、处于窗口内且不超过未来 2 小时的条目。只有日期、没有时刻的条目按整个公历日判断是否与窗口重叠。只有年或月的记录必须整个周期都落在窗口内，否则不收录，避免把不确定日期写成当天新闻。先用 feed ID/GUID/规范化 URL 生成稳定 SHA-256 ID，再按 DOI、去掉版本号的 arXiv 基 ID 和规范化 URL 去重。标题相同但 ID 不同会保留；同一 DOI 或同一 arXiv 基 ID 仍视为同一项。

只有内容生成、博客文件部署以及必要的 Telegram 投递成功后，才写入状态。十个时间位共享并发组，避免同时修改状态和首页；状态最多保留每个主题最近 2000 个 ID 及最近 10000 个全局 ID。报告 artifact 保留 14 天，只用于审计，不承担去重。

> 状态通过机器人提交回默认分支。若默认分支受保护，请为 GitHub Actions 允许写入，或调整规则允许机器人提交 `state/seen.json`。否则消息可能已发出但状态未持久化，下次会重复推送。

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
   后，每天 09:00 的日报会同时推送到 Telegram 和 ntfy，点击 ntfy 通知会打开文章页面。没有合格来源时不发送。

6. 仓库 **Settings → Pages → Build and deployment → Source** 选择 **GitHub Actions**。工作流用 GitHub 官方 Pages actions 直接上传并部署 `docs/`，同时把生成文章提交回仓库留档。首次发布完成后会得到 `https://<用户>.github.io/<仓库>/`。
7. 可选 Repository variables：

   - `GROQ_MODEL`：默认 `openai/gpt-oss-20b`；模型是否仍可用以及准确额度，以 Groq Console 的 Models / Limits 页面为准。
   - `PUBLIC_BASE_URL`：使用自定义域名或 Pages 地址不是默认形式时设置，末尾不要加 `/`。普通项目 Pages 会自动推导，无需设置。

8. 在 Actions 页面逐个用 **Run workflow** 手动测试。确认 Telegram 收到文章链接、`docs/posts/` 和 `state/seen.json` 出现机器人提交、Pages 能打开、报告 artifact 可下载后，再依赖定时任务。新提交部署到 Pages 有短暂延迟，收到通知后若暂时 404，稍后刷新即可。

不要把 key 写进 YAML、日志、`.env` 或提交历史。不要在来自 fork 的不可信 PR 上暴露 secrets。本项目只监听 `schedule` 和手动触发，不监听 `pull_request`。工作流权限收窄到 `contents: write`，用于唯一的状态提交。

## Groq 节流、失败与真实性

- 每个有新资料的主题最多做一次模型请求，结果写入同一篇日报，不另发分栏页。没有合格来源的主题不调用 Groq，整天都没有合格来源时不发布。摘要在送入模型前截断。每个主题默认最多分析 3 项，上限是 `config/editorial.yml` 的 `analysis_item_limit`，栏目 `max_items` 不能超过它。默认最大输出 2800 Token。
- 对 HTTP `429/498/500/502/503/504` 最多重试 6 次，优先遵守 `retry-after`，否则指数退避并加随机抖动。
- 免费计划不是“无限免费”：限额按组织、模型和多个维度计量，且官方会调整。代码不硬编码额度；请在 Groq Limits 页面查看账户的实时值。
- 外部摘要被明确标记为不可信数据，以降低提示注入风险。提示要求只据所给摘要分析、逐条用 `[n]` 引用，缺失信息必须明示，不能补造指标。
- 每期最多选择 3 项有正文摘要的资料；模型输出必须包含全部章节和每条来源编号。不完整或截断时缩减为最多 2 项重试一次，仍不合格则仅保留 Actions 审计材料，不发布来源摘要兜底页。
- 无新资料、来源全部失败或部分来源失败导致零条可用结果、或模型调用失败时，不发布文章、不发送 Telegram，也不更新已读状态。日报汇总当天有效文章，无有效文章则发布每日状态。没有单独的空文章开关。
- GPT-OSS 使用官方支持的 `reasoning_effort=low`，减小有限输出预算被内部推理耗尽的风险。关键结论仍必须打开原始 URL 核验；本系统是研究初筛，不是同行评审替代品。

## 博客与 Telegram 投递

每期完整内容写入 `docs/posts/<日期>-<主题>.html`，同一天手动重跑会覆盖同一地址，首页保留最近 365 期索引。页面是无数据库、无客户端脚本、无追踪器的静态 HTML；Markdown 渲染明确禁用原始 HTML，减少模型输出造成的注入风险。工作流先确认 Pages 部署成功，再发 Telegram 链接，最后提交去重状态；部署失败不会误标为已读。

Telegram 每天仅在 **09:00（Asia/Taipei，UTC+8）** 之后发送一条日报，包含标题、来源数量和网页链接。当天没有合格来源时不发布，也不发送状态通知。历史回放和历史迁移不发送通知。正式投递前检查当前日期、09:00 时间门禁，以及 `daily_notifications` 里是否已经有这一天。

`state/seen.json` 的 `daily_notifications` 按 Asia/Taipei 日期记录 Telegram 成功回执；同日重跑不重复发送。已经迁移的历史日期写有 `migrated` 标记且不会补发。可选 ntfy 同时收到同一条新日报，其失败仅记日志，不再触发额外 Telegram。维护异常与 MiMo 使用情况只记 Actions 日志和现有审计材料。GitHub Actions 为尽力调度，09:00 是计划时间，部署或调度延迟可能使消息稍晚到达。

## 本地测试

建议 Python 3.13：

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
pytest -q
ruff check .
```

不使用 secrets 的真实采集预览：

```bash
python -m research_bot.main --topic model_research --dry-run
```

完整本地投递前，在当前 shell 临时设置三个环境变量，再去掉 `--dry-run`。不要把变量值复制到 issue、截图或 Actions 日志。

## 服务边界与成本

### 调度可靠性与漏跑恢复

执行与发布时区固定为 `Asia/Taipei`（UTC+8，无夏令时）。网页上的发布时刻也固定显示为当天 09:00，不按阅读设备时区改日。文章 URL 使用该日历日。

- 主计划使用显式 UTC cron（Asia/Taipei 减 8 小时），对应 `0 1 * * *`。这并不保证 GitHub 准点投递。
- 定时事件和 catchup 都只检查 `daily_report` 这一期。旧的分栏时段不再发布。
- `Catch up overdue editorial slots` 另以 UTC 每小时 19、49 分检查，也可手动运行；只补当天 09:00 已到且尚未完成的日报，不在 09:00 之前发布，也不跨日补写。
- `state/slots.json` 保存“Asia/Taipei 日期＋daily_report”回执。已正式发布的不再重跑。当天没有合格来源时记为 `empty_digest`，不再编造一页。来源/模型失败或分析不合格间隔至少 60 分钟重试，最多 3 次。文章已准备但投递失败则恢复同一待投递结果，不重新消耗模型额度。间隔写在 `config/editorial.yml`。
- 网页及 prepared 回执一起提交；Pages 成功、通知成功后标记 published。测试模式不写正式回执。恢复流程共用串行写入锁 `editorial-state-writer-v1`，catchup 规划使用 `editorial-catchup-planner-v1`。Git 推送前先 rebase，冲突时安全失败，不强推覆盖。
- 采集仍读取 `config/sources.yml` 的全部主题，但只把通过校验的小节写进一篇日报。按主题的预览工作流继续是 dry-run，不发布分栏页。
- **限制**：两个定时入口都在 GitHub，不能覆盖 GitHub 调度器整体故障；也不自动跨日期补发前一天内容。要求独立容灾，应另配 Cloudflare Workers 等外部定时源调用同一个补偿 workflow。外部时钟也无绝对准点保证。Telegram 超时的极端情况下可能重复送达，API 不提供端到端 exactly-once 保证。

独立 Cloudflare 时钟的部署代码、权限及轮换说明见 [`infrastructure/cloudflare/README.md`](infrastructure/cloudflare/README.md)。代码入库不代表独立时钟已启用；必须完成 Cloudflare 部署、Secret 配置及调度验证。

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

# 时间线任务状态

任务固定按东八区执行，网页按访客浏览器时区显示。只有存在有效文章才显示“已发布”；资料已经报道过表示“今日无新增”，不代表当天文章已经发布。来源不足、分析未通过、执行异常和延迟分别说明，历史无文章时段默认折叠。缺少历史执行记录时明确显示“无可核验结果”，不补造文章或结果。

安全裁剪后的任务回执保存在 `docs/slot-status.json`，不包含待发布正文、密钥或内部请求。即使本次没有文章，也会部署状态更新；页面每分钟重新读取回执。已观察到超过一小时的延迟或重试耗尽时记录维护日志，不额外发送消息；任务完全没有启动时，仍依赖独立调度兜底，不能保证即时提醒。

# MiMo 备用模型

Groq 为主模型。可选 GitHub Secret `MIMO_API_KEY`，以及仓库 Variable `MIMO_FALLBACK_ENABLED=true` 才启用小米 `mimo-v2.6-flash` 兜底；默认关闭。接口固定为官方 `https://api.xiaomimimo.com/v1/chat/completions`（按量付费 API，不是 Token Plan 接口）。请先确认费用与账户额度，不要把限流上限误认为免费额度，程序无法保证只消耗赠送余额。

Groq 调用异常或第一次分析未通过校验时切换；MiMo 同样必须通过原有质量检查，不会直接发布。每次实际尝试 MiMo 请求后，记录 Actions 日志，不单独发送 Telegram。MiMo 单次不自动重试，关闭深度思考，输出最多 4000 token；每轮准备最多两次 MiMo 请求，受原有时段重试次数限制。不得在聊天、仓库或日志中保存 Key。

官方文档：https://mimo.mi.com/docs/zh-CN/quick-start/summary/first-api-call


## AI 知识科普专区

- 专区入口：`docs/knowledge/index.html`（线上 `/knowledge/index.html`）。
- 首篇文章：`docs/knowledge/ai-ecosystem-guide.html`，包含七个生态观察层、73 个代表作品、核心术语及应用场景。
- 内容源文件：`content/knowledge/ai-ecosystem-guide.md`；资料核验日期、产品名称与链接需随文章修订更新。
- 重新生成：`python -m research_bot.knowledge`，使用项目现有 `markdown-it-py` 依赖；同时生成五组示意图的桌面与手机 SVG 版本。
- 图示生成器：`research_bot/knowledge_art.py`；图源位于 `docs/assets/knowledge/`，正文配有图注、替代文本与快速跳转。
- 专区独立于定时简报；首页入口保存在 `research_bot/timeline.py`，导航保存在站点模板中，后续日报生成会保留入口。
