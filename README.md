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

## 自动编辑日（北京时间）

| 时间 | 栏目 | 形式 |
|---:|---|---|
| 09:07 | AI 晨间雷达与免费资源 | AI 动态，并查找当天新的免费 VPS / AI 服务线索 |
| 10:17 | AI 模型、训练与基础研究 | 深度研究 |
| 11:27 | AI 开源项目与工具更新 | 版本与迁移速览 |
| 12:37 | AI 论文午间速览 | 按星期轮换技术方向 |
| 13:47 | Prompt、上下文工程与评测 | 方法与工具简报 |
| 14:07 | 智能硬件技术专题 | 按星期轮换七条研究主线 |
| 15:17 | AI 开发实践与部署 | 以官方资料为依据的实践说明 |
| 16:27 | AI 应用与落地专题 | 按星期轮换应用方向 |
| 17:37 | AI 人物、机构与产业生态 | 可核验生态动态 |
| 18:47 | VORASIO AI 日报 | 当天站内内容汇总，不调用 Groq |

每周七天均按上述时间运行。分钟数刻意避开整点高峰。工作流使用 `timezone: Asia/Shanghai`，无需手算 UTC，也不受夏令时影响。定时执行是“尽力而为”，平台繁忙时仍可能延迟；因此不要把它用于硬实时告警。

首页按日期展示十个时段，可切换日期和筛选研究、开发、快讯、生态。状态区分已发布、暂无新内容、来源摘要和等待更新；等待更新不等于任务失败。暖白、墨绿与香槟金配色适配手机屏幕，动效遵循系统减少动态效果设置。

README 中标记区间是编辑章程的唯一来源，生成提示直接读取它；网站“关于”页仅介绍内容来源与状态。`preview-day.yml` 支持 `test`（默认：只生成审计材料，不发布、不通知、不读写正式去重状态）及 `production`（真实发布）两种模式。定时任务固定使用 production。

“新”指日期窗口内尚未正式发布的资料，不是“程序从未抓过”。今日简报表示今日出版，覆盖各栏目的滚动时间窗口，并不要求所有来源都在今天发表。清理测试内容后应排除对应测试状态，不得保留为正式已读记录。正式投递同时保存逐篇 publication 清单，便于后续精确核对。

Actions 的 `decision-*.json` 分别记录来源失败、无窗口内匹配资料、摘要不足、已经正式发布、分析接口失败、分析校验不通过及准备发布，附候选数量；不能把这些原因统称为“今日没有新内容”。自动校验只是一道门禁，不是事实正确性的保证。

## 仓库结构

```text
.
├── .github/
│   ├── dependabot.yml
│   └── workflows/
│       ├── _editorial.yml       # 小时内容位共用执行器
│       ├── editorial-day.yml    # 每天 10 个时间位的唯一计划入口
│       ├── _research.yml        # 旧研究任务的手动兼容执行器
│       ├── model-research.yml   # 七条研究主线，仅保留手动入口
│       └── run-all.yml          # 仅手动触发的一次性顺序全量运行
├── config/editorial.yml         # 十个内容位与星期轮换规则
├── config/sources.yml           # 主题、时间窗、关键词与来源
├── docs/                        # GitHub Pages 首页、文章与样式
├── research_bot/
│   ├── core.py                  # 采集、过滤、Groq、Telegram、状态
│   └── main.py                  # CLI 编排
├── state/seen.json              # 已成功投递项目的跨天状态
├── reports/                     # 每次报告（仅作为短期 artifact）
├── tests/test_core.py
├── requirements.txt
└── requirements-dev.txt
```

## 来源与筛选

论文研究使用 arXiv 官方 Atom API；开源、开发和生态栏目使用项目 Releases/Commits Atom、GitHub、Google AI 与 Hugging Face 等公开来源。各栏目配置独立的时间窗、关键词、条目上限和分析重点，详见 `config/sources.yml`。

晨间免费资源雷达通过公开搜索 RSS 发现线索，并将其标记为 `resource`。模型必须区分永久免费层、限时试用、赠送额度和待核验线索；仅凭标题不能确认免费。全局状态保证同一链接不会跨天重复推荐。当天没有新的可信条目时，页面由程序固定写入“今日未发现新的、可由公开来源确认的免费资源”，不会让模型补造结果。

采集只接受带有效发布日期、处于窗口内且不超过未来 2 小时的条目。先用 feed ID/GUID/规范化 URL 生成稳定 SHA-256 ID，再执行全局跨栏目去重和栏目历史去重。标题相同但论文 ID 不同会保留；同一论文更新版本仍视为同一项（arXiv Atom ID 稳定）。

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

6. 仓库 **Settings → Pages → Build and deployment → Source** 选择 **GitHub Actions**。工作流用 GitHub 官方 Pages actions 直接上传并部署 `docs/`，同时把生成文章提交回仓库留档。首次发布完成后会得到 `https://<用户>.github.io/<仓库>/`。
7. 可选 Repository variables：

   - `GROQ_MODEL`：默认 `openai/gpt-oss-20b`；模型是否仍可用以及准确额度，以 Groq Console 的 Models / Limits 页面为准。
   - `PUBLIC_BASE_URL`：使用自定义域名或 Pages 地址不是默认形式时设置，末尾不要加 `/`。普通项目 Pages 会自动推导，无需设置。

8. 在 Actions 页面逐个用 **Run workflow** 手动测试。确认 Telegram 收到文章链接、`docs/posts/` 和 `state/seen.json` 出现机器人提交、Pages 能打开、报告 artifact 可下载后，再依赖定时任务。新提交部署到 Pages 有短暂延迟，收到通知后若暂时 404，稍后刷新即可。

不要把 key 写进 YAML、日志、`.env` 或提交历史。不要在来自 fork 的不可信 PR 上暴露 secrets。本项目只监听 `schedule` 和手动触发，不监听 `pull_request`。工作流权限收窄到 `contents: write`，用于唯一的状态提交。

## Groq 节流、失败与真实性

- 每个有新资料的时间位最多做一次模型请求；18:47 日报和无新资料时间位不调用 Groq。摘要在送入模型前截断，单次通常输入 4–6 项，默认最大输出 2800 Token。
- 对 HTTP `429/498/500/502/503/504` 最多重试 6 次，优先遵守 `retry-after`，否则指数退避并加随机抖动。
- 免费计划不是“无限免费”：限额按组织、模型和多个维度计量，且官方会调整。代码不硬编码额度；请在 Groq Limits 页面查看账户的实时值。
- 外部摘要被明确标记为不可信数据，以降低提示注入风险。提示要求只据所给摘要分析、逐条用 `[n]` 引用，缺失信息必须明示，不能补造指标。
- 每期最多选择 3 项有正文摘要的资料；模型输出必须包含全部章节和每条来源编号。不完整或截断时缩减为最多 2 项重试一次，仍不合格则仅保留 Actions 审计材料，不发布来源摘要兜底页。
- 无新资料、来源全部失败或模型调用失败时，不发布文章、不发送 Telegram，也不更新已读状态。日报仅汇总当天有效文章，无有效文章就跳过。`allow_empty` 历史配置不再允许绕过此规则。
- GPT-OSS 使用官方支持的 `reasoning_effort=low`，减小有限输出预算被内部推理耗尽的风险。关键结论仍必须打开原始 URL 核验；本系统是研究初筛，不是同行评审替代品。

## 博客与 Telegram 投递

每期完整内容写入 `docs/posts/<日期>-<主题>.html`，同一天手动重跑会覆盖同一地址，首页保留最近 365 期索引。页面是无数据库、无客户端脚本、无追踪器的静态 HTML；Markdown 渲染明确禁用原始 HTML，减少模型输出造成的注入风险。工作流先确认 Pages 部署成功，再发 Telegram 链接，最后提交去重状态；部署失败不会误标为已读。

Telegram 只在 09:07 晨报、12:37 午间速览和 18:47 日报发送“标题、条目数、文章 URL”，其余内容只更新网站，避免频繁打扰。代码仍保留通用分段保护；遇到 429 时遵守 `retry_after`，5xx 指数退避，发送失败则不更新去重状态。

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

- 主计划使用显式 UTC cron（北京时间减 8 小时），网站展示仍是北京时间。这是减少时区依赖，并不保证 GitHub 准点投递。
- 任一主定时事件到达，均扫描当天所有已过计划时间的栏目，而不只运行该事件原本对应的一栏。
- `Catch up overdue editorial slots` 另以 UTC 每小时 19、49 分检查，也可手动运行；只补当天到点而未完成的栏目，不提前发布未来时段。
- `state/slots.json` 保存“北京时间日期＋栏目”回执。已正式发布或已确认无新内容的不再重跑；来源/模型失败或分析不合格间隔至少 60 分钟重试，最多 3 次。文章已准备但投递失败则恢复同一待投递结果，不重新消耗模型额度。
- 网页及 prepared 回执一起提交；Pages 成功、通知成功后标记 published。测试模式不写正式回执。恢复流程共用串行写入锁，Git 推送前先 rebase，冲突时安全失败，不强推覆盖。
- 没有合格内容只持久化审计结果，不生成空文章、不发送空通知。日报汇总有效文章。
- **限制**：两个定时入口都在 GitHub，不能覆盖 GitHub 调度器整体故障；也不自动跨日期补发前一天内容。要求独立容灾，应另配 Cloudflare Workers 等外部定时源调用同一个补偿 workflow。外部时钟也无绝对准点保证。Telegram 超时的极端情况下可能重复送达，API 不提供端到端 exactly-once 保证。

独立 Cloudflare 时钟的部署代码、权限及轮换说明见 [`infrastructure/cloudflare/README.md`](infrastructure/cloudflare/README.md)。代码入库不代表独立时钟已启用；必须完成 Cloudflare 部署、Secret 配置及调度验证。

### 已接入的补充来源

| 来源 | 接入与筛选方式 | 边界 |
|---|---|---|
| OpenAlex | 官方 API，按主题检索及真实出版日期过滤 | 需要 Actions secret `OPENALEX_API_KEY`；通过 Authorization 请求头传递，不写入仓库或 URL |
| ACL Anthology | 官方 RSS 发现论文，再读取论文页的摘要和出版日期 | RSS 包含旧论文更正和非论文记录；不把更正时间当作论文日期 |
| CVF Open Access | 官方会议档案和论文页摘要 | 当前配置 CVPR 2026，档案发布日为 2026-05-23；不在窗口时跳过，不伪装成日更新源。后续会议需更新配置 |
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

