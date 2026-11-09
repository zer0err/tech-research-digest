# 项目协作入口

产品使命与编辑章程以 README.md 的 EDITORIAL_CHARTER 标记区间为准。

- 接任务、交接、审查或发布前，阅读 [研发流程](planning/DEVELOPMENT_WORKFLOW.md)。
- 实现前确定任务编号、唯一交付负责人、验收条件、基准 SHA 和修改范围；内部任务使用仓库外的任务目录，格式见 [任务模板](planning/TASK_TEMPLATE.md)。本地目录位置由工作区配置提供，公开仓库不保存机器绝对路径。
- 开始和交接前检查 Git 状态；在任务分支修改，只编辑自己的 worktree，保留他人未提交内容。角色名称不代表在线、授权或已完成审查。
- 修改生成页面前找到生成源，同时维护必要产物。按变更影响验证，并记录实际提交、命令、结果与未验证范围。
- 提交和上传 artifact 前检查公开边界；内部任务包、原始日志、认证信息及未发布课程不进入公开 Git、Pages 或 CI artifact。

课程工作阅读 [课程需求](planning/COURSE_PLATFORM_REQUIREMENTS.md)；A2A 审查阅读 [能力与证据边界](agent_bridge/README.md)。
