# AI 领域报告：分模块、可续跑试点

本工具只写本地输出，不接入正式发布、通知或去重状态。覆盖十个领域，模块清单见 research_bot/domain_report.py。

## 使用

查看完整覆盖地图，不调用模型：

```bash
.venv/bin/python -m research_bot.domain_report
```

准备 evidence.json，键为模块 ID，值为明确分配的资料列表。每项需要 uid、title、url、published、summary、source，可选 kind、doi、date_precision。由编辑明确分配，避免关键词匹配造成假覆盖。

```json
{
  "agents": [{
    "uid": "replace-with-source-id",
    "title": "替换为真实资料标题",
    "url": "https://example.com/replace-with-real-source",
    "published": "2026-11-09",
    "summary": "替换为真实来源摘要；这里不是可用于报告的证据。",
    "source": "替换为真实来源名称"
  }]
}
```

先审核资料覆盖，再生成指定模块：

```bash
.venv/bin/python -m research_bot.domain_report --evidence evidence.json
.venv/bin/python -m research_bot.domain_report --evidence evidence.json --generate --modules agents knowledge
```

生成需要 GROQ_API_KEY；模型遵循现有 GROQ_MODEL 配置。使用 MiMo 时传 --provider mimo，并设置 MIMO_API_KEY 和 MIMO_FALLBACK_ENABLED=true。

默认目录 outputs/ai-domain 包含 index.md 覆盖总览、manifest.json 检查点及各模块 Markdown。状态分别为 needs_evidence、ready、generated、rejected、failed。未选中的模块不会调用模型。资料或 provider 变化时重新生成；generated 内容只经过结构校验，不能称为已核实。

## 编辑与分批阅读

每个模块采用：核心判断、问题与技术路线、证据与比较、应用与局限、验证行动、参考资料。跨来源按问题综合，不逐篇堆叠。

可分五批阅读：基础模型与训练；推理效率与开发基础设施；Agent 与知识增强；多模态与机器人；评测安全与产品应用。先交付覆盖总览，再逐批提供模块内容；当前不发送任何外部消息。

模块内容仍采用现有短报预算。资料太多时，应先细分子模块或编辑证据包；本试点不宣称已实现全文抓取、自动事实核验或无限长上下文。

## 验证边界

离线单元测试覆盖：缺证据不调用、检查点复用、资料变更重生成、模块失败隔离、无效编号拒绝。尚无真实模型对比、语义支持性验证和线上发布验证；需在配置密钥并准备真实证据后完成。
