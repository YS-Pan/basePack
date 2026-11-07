# 拆分记忆系统与资源协调任务

按用户要求，在 `devDoc/tasks/` 建立两个独立任务，各自维护 plan/progress。原 `20261106-rebuild` 保留重建总览、公共历史、文件结构与分层协作工作及联合发布条件，移除原综合 agent-plan，避免继续维护重复的工具实施步骤和状态。

| 原位置 | 现维护位置 |
| --- | --- |
| 原综合执行计划中的记忆目标、接口、P0–P5 与自用验收 | [记忆系统计划](../../tasks/20261106-memory-system/plan.md) 和 [进度](../../tasks/20261106-memory-system/progress.md) |
| resource-coordination-plan.md | [资源协调 plan.md](../../tasks/20261107-resource-coordination/plan.md) |
| deployment-layout-plan.md | [资源任务的部署合同](../../tasks/20261107-resource-coordination/deployment-layout-plan.md)，记忆任务引用同一维护源 |
| research/resource-coordination.md | [旧实现专项核对](../../tasks/20261107-resource-coordination/research/legacy-implementation.md) |
| research/sources.md 中初次 AgentTools 设施调查正文 | [设施调查](../../tasks/20261107-resource-coordination/research/infrastructure.md)，保留原时点观测 |
| 原总进度中的资源事项、阻碍和下一步 | [资源任务进度](../../tasks/20261107-resource-coordination/progress.md) |

跨任务依赖仍为资源 R0 先交付公共包/配置入口、R1 提供共享 embedding 客户端，记忆 P0/P1/P2 接入；两项产品各自验收。建设顺序和实现状态保持，未实施运行工具。更新 AGENTS、系统说明、术语、调研索引与历史记录的相关链接，纲领和原始快照保持原位置、原字节及 Git 保护。

检查本地链接/锚点、UTF-8、TOML 示例、阶段归属与 Git 差异；核对资源迁移正文及初次设施证据保留，确认 P0–P5、R0–R5、P7/P8 各有维护入口。文档迁移未运行模型、提交计算任务或修改机器配置。
