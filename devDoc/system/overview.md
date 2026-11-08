# 系统实现概览

当前唯一 active 路线是 [20261106-basepack](../../experiments/20261106-basepack/README.md)。本路线的源码、构建声明、测试、用户文档、示例和 resources skill 一起位于实验工程；根 devDoc 维护现行实现与活动工作，根两项通用技能独立交付。配置及安装边界见 [部署合同](deployment.md)。

本仓库已提供两项可独立使用的 skill：[file-structure](../../skills/file-structure/SKILL.md) 用于推荐或整理开发文档和实验工程布局；[agent-team](../../skills/agent-team/SKILL.md) 按任务规模组织主 agent、协调 agent 与执行 agent，使用宿主已有的订阅 subagent 能力。

`basepack` 0.4.0 的公共入口包括：`init` 从随包模板接入项目，`migrate` 显式升级旧项目配置，`config show` 显示实际路径与安装来源，`doctor` 按设施只读检查。项目接入源码和模板统一在 [project/](../../experiments/20261106-basepack/src/basepack/project)，配置解析唯一实现为 [config.py](../../experiments/20261106-basepack/src/basepack/project/config.py)。项目 schema 2 配置和详细操作入口分别为 `.basepack/config.toml`、`.basepack/instructions.md`，根 AGENTS 只保留短指针；机器配置保持 schema 1。安装与项目接入见 [使用说明](../../experiments/20261106-basepack/docs/setup-project.md)，实际部署与验收状态统一见 [资源进度](../tasks/20261107-resource-coordination/progress.md)。

资源接口现为 `jobs`/CondorClient 和明确接收 MachineConfig 的 EmbeddingClient；机器管理通过 `embedding --machine-config <file> serve|status|stop` 独立于项目。固定模型、请求服务与进程所有权分开，向量语义身份、协议版本和部署指纹各有合同。普通 GPU 申请仍由 schedd 转换官方字段，容量、内部资源名与额度只由 Condor 配置维护，实现边界见 [资源模块](modules/resources.md)。历史条件见 [R6 通用节点结果](../tasks/20261107-resource-coordination/native-condor.md)、[R7 标准提交结果](../tasks/20261107-resource-coordination/standard-submit-result.md) 和 [R0–R5 交付](../tasks/20261107-resource-coordination/result.md)。记忆检索、建图和数据库尚未交付。分层组织已提供指令层初版；参考与行为检查见 [专项记录](../tasks/20261106-rebuild/research/agent-team.md)，复杂广读的质量与总成本对照仍待完成。

旧项目和机器上已有设施是参考与可复用资源，调查范围见 [调研依据](../tasks/20261106-rebuild/research/sources.md)；其能力不代表本项目已完成实现或验收。

当前结构与外部边界见 [架构说明](architecture.md)，实际开发入口与核验限制见 [环境说明](environment.md)，概念歧义查 [项目术语](../terminology.md)。本页随实现落地指向对应模块说明；工作分别从 [记忆进度](../tasks/20261106-memory-system/progress.md)、[资源协调进度](../tasks/20261107-resource-coordination/progress.md) 接续，跨工具状态见 [重建总进度](../tasks/20261106-rebuild/progress.md)。
