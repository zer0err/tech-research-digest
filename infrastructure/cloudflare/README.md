# 独立漏跑补偿时钟

Cloudflare Worker 只调用 GitHub `catchup.yml`，不接触 Groq/Telegram 密钥，也不采集或生成文章。

- 北京时间 09:11–23:41，每半小时执行一次，约 30 次/天；不绑定 vorasio.com，不修改现有 DNS。
- 发现补偿 workflow 已排队或执行中则跳过。正式栏目回执继续由 GitHub 校验，防重复生成。
- 无公开 HTTP 触发入口；`workers_dev` 和预览 URL 关闭。日志仅输出状态、时间或 HTTP 错误码。
- GitHub 限流及部分 5xx 最多重试 3 次；超时或其他失败由下次定时执行重试。Token 失效时拒绝执行。
- 依赖 GitHub API/Actions 可用，不承诺端到端准点；双平台失效、凭据过期仍需人工处理。

## 凭据与部署

1. 使用 Cloudflare 官方 Wrangler 完成 OAuth 登录：`npx wrangler login`。
2. 在 GitHub Settings → Developer settings → Personal access tokens → Fine-grained tokens 创建专用 Token：只选择 `zer0err/tech-research-digest`，Repository permissions 仅 `Actions: Read and write`（Metadata 自动只读）。设置到期时间，并在到期前轮换。不要使用账户范围的现有 CLI Token。
3. 在此目录执行 `npx wrangler secret put GITHUB_DISPATCH_TOKEN`，在隐藏输入中填 Token；或在 Worker 设置的 Variables and Secrets 中保存为 **Secret**。不要填进 TOML、仓库或聊天。
4. 在此目录执行 `npx wrangler deploy`。如首次 secret 操作提示创建 Worker，可允许创建同名 Worker。
5. 在 Cloudflare Worker 的 Triggers/Logs 核对 cron 及调度结果，并在 GitHub Actions 检查对应 `workflow_dispatch` 记录。Cron 配置传播可能需要最多约 15 分钟。

本地验证：`node --test worker.test.mjs`。构建验证：`npx wrangler deploy --dry-run`。

## 费用与停用

使用 Workers Free，不启用付费方案或 KV/D1/R2。30 次/天很低，但免费计划有 CPU、子请求、触发器数量等限制，并非无限免费；失败会体现在 Cloudflare 调度日志。GitHub 的空补偿仍会运行一次轻量 plan job，公开仓库标准 runner 适用其免费政策；私有仓库会消耗分钟。

停用：将 `wrangler.toml` 中 `crons` 改为 `[]` 后部署，或在 Cloudflare 删除此 Worker；同时撤销专用 GitHub Token。此操作不影响网站或 GitHub 原有补偿。

官方文档：[Cron](https://developers.cloudflare.com/workers/configuration/cron-triggers/)、[免费限制](https://developers.cloudflare.com/workers/platform/limits/)、[Secrets](https://developers.cloudflare.com/workers/configuration/secrets/)、[GitHub workflow dispatch](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event)。
