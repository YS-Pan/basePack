# 重建总进度

更新：2026 年 11 月 8 日（北京时间）。

## 当前阶段

重建大阶段继续进行。资源 R0–R7 已交付，当前先按 R8 完成公共包/资源模块维护，再接续记忆闭环；本轮只重新整理计划，没有修改实现。分步状态只维护在 [资源进度](../20261107-resource-coordination/progress.md) 和 [记忆进度](../20261106-memory-system/progress.md)，本页保留跨工具、文件结构与分层协作入口，顺序和发布条件见 [重建总览](plan.md)。

## 已完成

- 已形成项目纲领、[简短实施计划](plan.md)、[旧项目近期历史](legacy-history.md) 和 [精选调研](research/sources.md)。
- 开发文档已集中到 `devDoc/`；README 的介绍与入口已合入根目录 AGENTS.md，重建材料集中在本目录。组织变化见 [变更记录](../../change_log/major/20261106_232701_organize-dev-docs.md)。
- 文档维护规则、术语、现行结构与环境说明已补齐，交接与调研结论索引已完善；实际结果和检查见 [文档整理结果](result.md)。
- 已按用户选定名称统一为 `devDoc/system/`、`devDoc/tasks/` 和项目根 `artifacts/`，同步文档引用、技能示例、本机脚本及 Git 边界，见 [变更记录](../../change_log/minor/20261107_144504_rename-documentation-directories.md)。
- 已建立 [file-structure skill](../../../skills/file-structure/SKILL.md)，支持开发文档与实验分包两类布局；来源和初版验证见 [专项调研](research/file-layouts.md)。[纲领建议稿](charter-file-layout-proposal.md) 供用户自行填写，正文保持原文。
- 已按用户要求将该技能改名为 `file-structure`，同步源码目录、元数据、文档引用与本机发现联接；纲领保持原样，见 [改名记录](../../change_log/minor/20261107_150816_rename-file-structure-skill.md)。
- 已按用户要求重新筛查高星项目、独立口碑和公开实测，建立 [agent-team skill](../../../skills/agent-team/SKILL.md) 指令层初版，以纲领为目标，参考项目只提供机制。[专项记录](research/agent-team.md) 区分第三方证据、本机行为检查和待完成的 P7 对照。
- 已将记忆计划 P0–P5 拆入 `20261106-memory-system`，将资源计划、部署布局和专项调研迁入 `20261107-resource-coordination`；两任务各有 plan/progress，原综合执行计划的共性工作与 P7/P8 归入 [总览](plan.md)。
- 资源 R0–R5 已完整交付共享embedding、Condor入口及公共包/配置，普通wheel源码外联合验收通过；供记忆任务后续复用的接口见 [结果](../20261107-resource-coordination/result.md)。产品README、使用/管理员说明与resources skill已建立，状态只维护在对应 [进度](../20261107-resource-coordination/progress.md)。
- 资源后续 R6 已按用户要求切换为通用 Condor 节点容量与同卡显存累计记账，0.2.0 普通 wheel、四作业共享及 embedding 联合验收完成；见 [专项结果](../20261107-resource-coordination/native-condor.md)。
- 资源 R7 已交付0.3.0普通wheel与Condor原生提交转换；用户只填官方GPU字段，站点内部资源由Condor管理。四项同卡、第五项排队、默认整池、取消与embedding联合实测通过，见 [R7结果](../20261107-resource-coordination/standard-submit-result.md)。
- 已将本轮架构评审和两侧目录要求收敛为 [R8.0–R8.4](../20261107-resource-coordination/plan.md#实施批次)，同步命名、模块边界、迁移和必要回归；这是计划维护完成，R8 实现尚未开始。

## 阻碍与待核

- 文件结构建议已有独立 skill；真实大项目迁移、未来布局及记忆读取效果继续按实际任务验证，记忆自用验收见 [独立任务](../20261106-memory-system/plan.md#devdoc-自用与读取轮数)。
- 分层协作已有指令层初版，[P7](plan.md#p7-分层-agent-组织) 仍需真实广读任务的能力与成果质量对照。主上下文、团队总用量和耗时单独记录，允许增加用量换取质量提升。

## 下一步

1. 按资源 R8 分步实施并一次完成普通 wheel 迁移验收；现行 0.3.0 继续按使用文档操作，远端发布按用户指令执行。
2. 记忆 P0 的选型与资料准备可并行；公共接入形成后推进 P1 文字闭环，具体状态从 [记忆进度](../20261106-memory-system/progress.md) 接续。
3. 文件结构和分层协作在实际任务中继续验证；联合发布按 [总览 P8](plan.md#p8-联合交付与轻量发布) 执行。
