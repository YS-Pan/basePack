# 系统实现概览

本仓库已提供两项可独立使用的 skill：[file-structure](../../skills/file-structure/SKILL.md) 用于推荐或整理开发文档和实验工程布局；[agent-team](../../skills/agent-team/SKILL.md) 按任务规模组织主 agent、协调 agent 与执行 agent，使用宿主已有的订阅 subagent 能力。

记忆、资源协调的产品运行功能尚未实现，目前没有本仓库的软件包安装入口、记忆命令或记忆数据库。分层组织已提供指令层初版；参考与行为检查见 [专项记录](../tasks/20261106-rebuild/research/agent-team.md)，复杂广读的质量与总成本对照仍待完成。

旧项目和机器上已有设施是参考与可复用资源，调查范围见 [调研依据](../tasks/20261106-rebuild/research/sources.md)；其能力不代表本项目已完成实现或验收。

当前结构与外部边界见 [架构说明](architecture.md)，实际开发入口与核验限制见 [环境说明](environment.md)，概念歧义查 [项目术语](../terminology.md)。本页随实现落地指向对应模块说明；工作分别从 [记忆进度](../tasks/20261106-memory-system/progress.md)、[资源协调进度](../tasks/20261107-resource-coordination/progress.md) 接续，跨工具状态见 [重建总进度](../tasks/20261106-rebuild/progress.md)。
