# 系统实现概览

本仓库已提供两项可独立使用的 skill：[file-structure](../../skills/file-structure/SKILL.md) 用于推荐或整理开发文档和实验工程布局；[agent-team](../../skills/agent-team/SKILL.md) 按任务规模组织主 agent、协调 agent 与执行 agent，使用宿主已有的订阅 subagent 能力。

已交付 `basepack` Python 包和公共入口：`init` 从随包模板接入项目，`config show` 显示实际路径与安装来源，`doctor` 按设施进行只读检查。安装与项目接入见 [使用说明](../../docs/setup-project.md)，配置解析唯一实现为 [config.py](../../src/basepack/config.py)。系统 Python 的 editable 与普通 wheel 已实测，详细证据见 [资源进度](../tasks/20261107-resource-coordination/progress.md)。

资源 R0–R5 已完整交付，0.2.0 将普通容量迁到通用 Condor 节点；0.3.0 的标准提交合同进一步由 schedd 统一转换官方 GPU 字段，内部资源名与额度只由 Condor 配置维护。固定多模态模型继续由独立服务跨项目共用。当前部署和验收状态见 [资源进度](../tasks/20261107-resource-coordination/progress.md)，实现边界见 [资源模块](modules/resources.md)；历史条件分别见 [R6 通用节点结果](../tasks/20261107-resource-coordination/native-condor.md) 和 [R0–R5 交付](../tasks/20261107-resource-coordination/result.md)。记忆检索、建图和数据库尚未交付。分层组织已提供指令层初版；参考与行为检查见 [专项记录](../tasks/20261106-rebuild/research/agent-team.md)，复杂广读的质量与总成本对照仍待完成。

旧项目和机器上已有设施是参考与可复用资源，调查范围见 [调研依据](../tasks/20261106-rebuild/research/sources.md)；其能力不代表本项目已完成实现或验收。

当前结构与外部边界见 [架构说明](architecture.md)，实际开发入口与核验限制见 [环境说明](environment.md)，概念歧义查 [项目术语](../terminology.md)。本页随实现落地指向对应模块说明；工作分别从 [记忆进度](../tasks/20261106-memory-system/progress.md)、[资源协调进度](../tasks/20261107-resource-coordination/progress.md) 接续，跨工具状态见 [重建总进度](../tasks/20261106-rebuild/progress.md)。
