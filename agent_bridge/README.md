# 本机 A2A 审查 Agent

这是实际运行的第二个 Codex 进程，通过官方 A2A Python SDK 提供 A2A 1.0 HTTP+JSON 服务。主控通过 HTTP 发现 Agent Card、提交 Task、轮询状态并读取 review.json Artifact。不是用固定回复模拟另一个模型。

## 已部署位置

- 仅本机地址：`http://127.0.0.1:8787`
- Agent Card：`/.well-known/agent-card.json`
- 提交：`POST /message:send`
- 查询：`GET /tasks/{id}`
- 取消：`POST /tasks/{id}:cancel`
- systemd 用户服务：`vorasio-a2a.service`
- 本机 Bearer 令牌：`~/.config/vorasio-a2a/token`（权限 600，不要提交或粘贴给别人）。客户端自动读取。

这不是公共 API，没有开放公网端口。另一台机器接入需要另行配置 HTTPS、认证和网络，不应直接公开当前监听端口。

## 安装与管理

在项目根目录执行：

```bash
uv venv .venv-a2a
uv pip install --python .venv-a2a/bin/python -r requirements-a2a.txt
.venv-a2a/bin/python -m agent_bridge.manage install
.venv-a2a/bin/python -m agent_bridge.manage status
```

`install` 使用当前用户的 systemd，启用并启动服务。服务复用机器现有 Codex 认证与已选模型/提供商，不复制认证文件、不配置新的 API 密钥；先用 `codex login status` 确认认证可用。管理命令还有 `start` 和 `stop`。改动服务代码后使用 `systemctl --user restart vorasio-a2a.service`，不要在任务运行中重启。

用户服务已设为失败自动重启；机器停止时不能继续处理任务。磁盘和配置保留不等于任务仍在运行，开机后以实际服务状态为准。

## 一次完整协作

1. 主控把业务目标、验收标准、需要的源码与实际检查结果写入本地 Markdown。只放本次审查需要的资料，不包含密钥、客户资料或登录文件。
2. 调用客户端：

```bash
.venv-a2a/bin/python -m agent_bridge.client \
  --input outputs/a2a/review-request.md \
  --output outputs/a2a/round-1.json
```

3. 查看结果中的 `task.id`、`task.contextId`、`task.status` 和 `task.artifacts`。审查结果区分 `pass`、`changes_required`、`insufficient_evidence`。
4. 主控处理真实问题或补充缺少证据，把上一轮意见、修改差异和新增验证结果一起放入新任务包，携带原 `contextId`：

```bash
.venv-a2a/bin/python -m agent_bridge.client \
  --input outputs/a2a/recheck-request.md \
  --context-id '<上一轮 task.contextId>' \
  --output outputs/a2a/round-2.json
```

已结束的任务不能重启；复查创建新 task，沿用 context。后端每轮是新的 Codex 调用，**不会自动读取上一轮私有会话记忆**，所以主控必须明确传递上一轮结果与所需证据。

## 职责与边界

- 第二个 Agent 只审查，不写项目、不发布、不发送外部消息。Codex 使用 read-only sandbox；任务指令要求不调用工具，基于主控提交的证据判断。
- 模型沿用当前机器配置，底层仍可能经过 Magpie 路由。A2A 是 Agent 通信，Magpie 是模型接入；并非同一层。
- 最大输入 160000 字符，模型执行限时 240 秒，一次运行一个模型请求；超时或取消会终止子进程组。
- 客户端轮询限时 360 秒，不会因为超时自动重发。任务创建后即保存检查点，状态未知时使用原 task ID 查询，避免重复模型调用。
- Task Store 暂用 SDK 内存实现，**服务重启后旧 task 无法继续查询**。本地 `outputs/a2a/` 的审查文件与客户端检查点保留，可用于人工恢复任务上下文。
- `outputs/a2a/` 存放任务包、回复、模型事件与用量，已被 Git 忽略，不写入网站。生产跨机器长期运行需扩展持久任务库和恢复机制。
- 测试通过只证明覆盖到的实现；审查结果中的 limits 不得删除或改写成实际线上验证。

## 验证

```bash
uv pip install --python .venv-a2a/bin/python pytest==8.4.2
.venv-a2a/bin/python -m pytest tests/test_a2a_bridge.py -q
.venv/bin/python -m pytest -q
```

协议单测显式使用 fixture backend，不冒充实际 AI。真实模型对话结果另存于 `outputs/a2a/round-1.json` 与 `round-2.json`。普通网站环境没有安装 SDK 时会跳过 A2A 单测，不会改变部署依赖。

官方参考：
- https://a2a-protocol.org/latest/specification/
- https://github.com/a2aproject/a2a-python
- https://learn.chatgpt.com/docs/non-interactive-mode
