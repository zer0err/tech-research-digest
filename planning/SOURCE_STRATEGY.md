# VORASIO 信息来源分层与扩展候选

核对日期：2026-10-26。本文件是来源规划，不代表新增来源已经接入；自动采集许可、授权、限流及全文可用性须逐站验证。MiMo/Groq 是生成服务，不是信息来源。

## 1. 分类维度必须分开

- 来源层：论文原文、书目索引、官方发布、代码与模型、评测、监管标准、社区线索、商业条款。
- 技术主题：模型训练、数据、推理系统、音视频、Agent、机器人、嵌入式、产品可靠性。
- 呈现形式：快讯、研究分析、实践参考、教程、人物资料卡、资源目录。
- 证据类型：作者主张、厂商自测、公开复现、独立评测、法规原文。官方来源不等于独立证明。

## 2. 当前生产配置

| 来源族 | 当前范围 | 作用 | 风险/缺口 | 接入状态 |
|---|---|---|---|---|
| arXiv | 多个技术主题 API | 发现预印本与摘要 | 非同行评审；摘要不足以复述全文实验 | 已配置，可能受可用性影响 |
| OpenAlex | 主题检索 API | 发现与交叉核对书目信息 | 不是另一份独立实验证据；摘要可能缺失 | 已配置 Key |
| Crossref | 主题检索 API | DOI、出版时间、元数据 | 摘要可能缺失；注册/更新时间不是发表时间 | 已配置 |
| ACL Anthology | 论文索引与页面 | NLP 正式论文入口 | 固定抓取少量新条目不保证覆盖；更新集中 | 已配置 |
| CVF Open Access | CVPR 2026 固定入口 | 视觉会议论文 | 当前配置是固定会议日期，通常不在“最新”时间窗 | 已配置但非持续日更源 |
| GitHub Releases | Ollama、Transformers、vLLM、PyTorch、FastAPI、Gradio 等 | 正式版本、迁移与兼容性 | 不应直接从 release 推导完整已验证教程 | 已配置；API 与 Atom 混用 |
| GitHub commits | OpenAI Cookbook、Prompt Engineering Guide | 教程/提示词变更线索 | 当前多为提交标题，常缺足够正文；不能等同正式更新 | 已配置，建议改为读取有效 diff |
| 官方博客 | Google AI、Hugging Face、GitHub、NVIDIA | 官方发布与工程资料 | 多栏目重复订阅；厂商宣传不是独立评测 | 已配置 |
| Bing RSS 搜索 | 免费 VPS、AI 服务检索 | 发现新线索 | 日期、摘要和免费条件不稳定；不得当确认目录 | 已配置，仅线索 |

“已配置”不等于每次都抓取成功。应报告每个来源本轮的成功数、时间过滤数、去重数、摘要不足数及错误，而不是只输出最终文章数量。

## 3. 供选择的扩展方向

| 编号 | 方向 | 候选原始来源 | 优先级 | 建议呈现/频率 | 启用前条件 |
|---|---|---|---|---|---|
| A | 模型与数据资产 | Hugging Face Hub API、模型卡、数据卡、官方发布仓库 | 高 | 模型/数据更新，日检 | 许可、模型版本、硬件需求；卡片性能按作者主张标注 |
| B | 推理与端侧运行时 | ONNX Runtime、llama.cpp、TensorRT-LLM、ExecuTorch 官方仓库 | 高 | 正式版本与迁移提示，日检 | 精选项目白名单；不把普通提交当重大更新 |
| C | 实证评测与成本 | MLCommons/MLPerf、公开评测报告及复现仓库 | 高 | 性能对照专题，周检 | 对齐模型、精度、设备、负载；禁止跨条件直接排名 |
| D | 端侧硬件与固件 | Raspberry Pi 官方新闻、ESP-IDF 官方 Releases；后续评估 Arm/ST 官方入口 | 高 | 硬件/SDK 更新，周检 | 前两项分别为已核对公开新闻与标准仓库接入候选；其余待逐站核验 |
| E | AI 工程教程 | 官方 Cookbook、官方示例仓库、版本化文档 | 高 | 版本化实践参考，周更 | 抓取完整示例/diff；未经隔离环境运行不得写“已验证教程” |
| F | 安全与可靠性 | NIST AIRC、项目安全公告、厂商官方 advisory | 中高 | 安全周报/风险专题 | 区分框架建议与强制法规；公告需确认受影响版本 |
| G | 产业与人物 | 官方研究主页、机构公告、原始访谈 | 中 | 机构动态/人物资料卡，周检 | 事实带日期和出处；不推断立场/关系；不可复制完整访谈 |
| H | 云与部署成本 | CNCF 官方博客、服务商官方价格/免费计划/变更公告 | 中 | 部署与成本变化，周检 | 条款变更检测；区分永久免费层、试用、赠送余额、待核验 |
| I | 社区与 X 言论 | 作者原帖、原始讨论、官方 X API | 后置可选 | “观点与讨论”，按事件 | 独立预算和授权；观点不作性能事实；不绕过登录/反爬 |
| J | 音频与人机交互 | 音频模型官方模型卡、原始论文、官方实现 | 高（若偏硬件） | 语音/音频专题，周检 | 单独记录时延、采样率、语言、许可、测试设备，不能混入一般多模态新闻 |

推荐首批 A+B+C+E；若聚焦智能硬件，改为 A+B+D+J，C 作为共同评测基础。不应同时把十项都变成每日独立栏目。

## 4. 统一来源登记字段

每个 source 至少登记：`id`、`publisher`、`source_family`、`official_url`、`access_method`、`auth_secret_name`（只存名称）、`cost_policy`、`rate_policy`、`license_review`、`terms_checked_at`、`topics`、`primary_section`、`evidence_type`、`expected_update_frequency`、`max_items`、`fetch_status`。

每个 item 至少登记：来源项目 ID、规范 URL、DOI/arXiv ID/仓库 tag、标题、作者/机构、原始发表时间、更新时间、首次发现时间、采集时间、时间精度、摘要/全文可用性、正文 hash、版本、语言、来源证据类型、许可、主栏目、关联栏目、已报道文章 URL。

“来源族”与“证据等级”不能合并：同一论文在 arXiv/OpenAlex/Crossref 出现三次，仍只是一项研究，不是三份独立支持。

## 5. 筛选、去重与发布建议

1. 同一事件指定一个主栏目；其他栏目只关联链接或做明确增量分析。索引跨源归并，不把重复记录送进模型。
2. 快讯以原始发布时间为主；常青教程另设复核日期，不能伪装成今日新闻。补跑以昨日截止时间筛选目前可访问资料，不声称还原昨日快照。
3. 来源抓取和模型生成解耦：日内收集共享候选池，时段只消费合适材料，不必每小时重新抓全站。
4. 自动化日报可以每日发布有效汇总，深度专题按“材料充分才发”。不为填满时间线反复放宽日期或重复报道。
5. 免费资源改用结构化目录与变更监测，新增/条件改变才推送；没有新增如实说明，不承诺每日必有不同的免费服务。
6. 教程从“标题摘要”升级为原文、示例、版本和最小验证；未运行的内容称实践参考。引文与数值校验仍保留。
7. 来源中断与没有新内容分开统计；AI 兜底只能改善生成可用性，无法补出不存在的证据。

## 6. 官方核对入口

- Hugging Face API：https://huggingface.co/docs/hub/en/api
- Hugging Face 限流：https://huggingface.co/docs/hub/main/rate-limits
- OpenAlex 费用：https://help.openalex.org/access/pricing/ （当前账户有每日免费 API 用量，额度不是永久不变的请求次数）
- GitHub API 限流：https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api
- MLCommons：https://mlcommons.org/benchmarks/
- Raspberry Pi 官方新闻及 RSS 入口：https://www.raspberrypi.com/news/
- NIST AIRC：https://airc.nist.gov/
- CNCF 官方博客：https://www.cncf.io/blog/
- X API 计费：https://docs.x.com/x-api/getting-started/pricing （按使用量计费，不作为默认免费来源）

公开可读不等于允许任意转载或批量抓取。除已核对 API/RSS 的具体入口外，候选站点启用前应继续检查 robots、条款、格式稳定性与摘要授权。此前明确排除的 OpenReview 不接入。
