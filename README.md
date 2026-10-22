# VORASIO AI × 智能硬件研究

基于 GitHub Actions、Groq 和 Telegram 的自动化研究系统。系统采集公开技术资料，经过日期过滤与全局去重后生成带来源编号的中文研究简报，发布到 GitHub Pages；Telegram 仅发送文章标题和网页链接。

## 运行时间（北京时间）

| 任务 | 频率 | 工作流 |
|---|---:|---|
| AI 模型、训练与基础研究 | 每天 10:00 | `model-research.yml` |
| 高效 AI、模型压缩与端侧适配 | 周一、周四 14:00 | `efficient-ai.yml` |
| 推理引擎、编译器与嵌入式系统 | 周二 14:00 | `inference-systems.yml` |
| AI 芯片、计算架构与硬件平台 | 周三 14:00 | `ai-hardware.yml` |
| 多模态感知、音视频与人机交互 | 周五 14:00 | `multimodal.yml` |
| Agent、机器人与具身智能 | 周二、周六 16:00 | `embodied.yml` |
| 智能硬件产品化、可靠性与安全 | 周日 14:00 | `product-safety.yml` |

工作流使用 GitHub 官方支持的 `timezone: Asia/Shanghai`，无需手算 UTC，也不受夏令时影响。定时执行是“尽力而为”，平台繁忙时可能延迟；因此不要把它用于硬实时告警。

## 仓库结构

```text
.
├── .github/
│   ├── dependabot.yml
│   └── workflows/
│       ├── _research.yml        # 共用执行器
│       ├── model-research.yml   # 七个独立定时入口
│       ├── efficient-ai.yml
│       ├── inference-systems.yml
│       ├── ai-hardware.yml
│       ├── multimodal.yml
│       ├── embodied.yml
│       ├── product-safety.yml
│       └── run-all.yml          # 仅手动触发的一次性顺序全量运行
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

当前来源均为 arXiv 官方 Atom API，按模型、高效化、推理系统、芯片、感知、具身智能和产品可靠性分别检索；
各栏目配置独立的关键词、回看窗口、条目上限和分析重点，详见 `config/sources.yml`。

采集只接受带有效发布日期、处于窗口内且不超过未来 2 小时的条目。先用 feed ID/GUID/规范化 URL 生成稳定 SHA-256 ID，再执行全局跨栏目去重和栏目历史去重。标题相同但论文 ID 不同会保留；同一论文更新版本仍视为同一项（arXiv Atom ID 稳定）。

只有 Groq 分析、博客文件生成且 Telegram 链接发送成功后，才写入状态。七个定时入口共享并发组，避免同时修改状态和首页；状态最多保留每个主题最近 2000 个 ID及最近 10000 个全局 ID。报告 artifact 保留 14 天，只用于审计，不承担去重。

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

- 每次任务只做一次模型请求，输入最多 6 或 8 篇，降低 RPM/TPM/RPD/TPD 消耗。
- 对 HTTP `429/498/500/502/503/504` 最多重试 6 次，优先遵守 `retry-after`，否则指数退避并加随机抖动。
- 免费计划不是“无限免费”：限额按组织、模型和多个维度计量，且官方会调整。代码不硬编码额度；请在 Groq Limits 页面查看账户的实时值。
- 外部摘要被明确标记为不可信数据，以降低提示注入风险。提示要求只据所给摘要分析、逐条用 `[n]` 引用，缺失信息必须明示，不能补造指标。
- 模型输出仍可能出错。关键结论必须点开报告末尾原始 URL 核验；本系统是研究初筛，不是同行评审替代品。

## 博客与 Telegram 投递

每期完整内容写入 `docs/posts/<日期>-<主题>.html`，同一天手动重跑会覆盖同一地址，首页保留最近 365 期索引。页面是无数据库、无客户端脚本、无追踪器的静态 HTML；Markdown 渲染明确禁用原始 HTML，减少模型输出造成的注入风险。工作流先确认 Pages 部署成功，再发 Telegram 链接，最后提交去重状态；部署失败不会误标为已读。

Telegram 只收到“标题、条目数、文章 URL”，远低于普通文本 4096 字符上限。代码仍保留通用分段保护；遇到 429 时遵守 `retry_after`，5xx 指数退避，发送失败则不更新去重状态。

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

- GitHub Actions：公开仓库使用标准 GitHub-hosted runner 通常免费；私有仓库按账户方案有免费分钟和存储额度，超出后计费。cache 每仓库有独立额度，artifact 计入存储。具体数字会随方案变化，以 Billing 页面为准。
- Groq：有免费计划，但速率和日额度因模型/组织而异；达到任一维度会返回 429。Developer 是付费按量方案，Flex/Batch 等能力可能仅限付费层。
- Telegram Bot API：这里使用普通 HTTPS Bot API；官方没有为这种低频单聊天推送收取 API 费用，但有消息长度和发送速率等限制。
- arXiv：公开 API 不是 SLA 服务。代码设置 User-Agent、串行请求和退避；若扩充来源，应遵守各来源条款、robots 和速率限制。

## 可选增强

若不希望机器人提交污染默认分支，可把状态迁移到独立对象存储（例如带条件写入/版本控制的 S3 兼容桶）或数据库；届时需实现原子 compare-and-swap。不要仅换成 Actions cache，因为 cache key 创建后不可更新且会回收，不能提供长期一致性。

