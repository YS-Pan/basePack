# 重建总进度

更新：2026 年 11 月 10 日（北京时间）。

## 当前阶段

当前唯一 active 路线为 [20261106-basepack](../../../experiments/20261106-basepack/README.md)，源码、构建声明、测试、产品文档、示例及资源和记忆 skill 在该实验工程内维护；根目录保留统一 devDoc 和三项通用技能。本次布局迁移的实际检查与接续见 [迁移结果](../../archive/20261109-project-layout/result.md)，不改变 R9 和记忆功能的完成状态。

资源 R9 已交付 0.5.0 并结案归档，详见 [R9 结果](../../archive/20261107-resource-coordination/r9-result.md)。记忆P0–P5基线及0.6.1修复、安装和真实PPT项目维护实测已交付；质量/成本边界和具体状态只在 [记忆进度](../20261106-memory-system/progress.md) 接续；本页跟踪跨工具状态与公共工作，共性取舍见 [复用优先](plan.md#复用优先)。

## 已完成

- 0.6.2 已交付项目模型等级配置及 `config ai`，并普通安装至稳定客户端；源码外核验和测试范围见 [变更记录](../../change_log/minor/20261110_113515_project-ai-tiers.md)。
- 已形成项目纲领、[简短实施计划](plan.md)、[旧项目近期历史](legacy-history.md) 和 [精选调研](research/sources.md)。
- 开发文档已集中到 `devDoc/`；README 的介绍与入口已合入根目录 AGENTS.md，重建材料集中在本目录。组织变化见 [变更记录](../../change_log/major/20261106_232701_organize-dev-docs.md)。
- 文档维护规则、术语、现行结构与环境说明已补齐，交接与调研结论索引已完善；实际结果和检查见 [文档整理结果](result.md)。
- 已按用户选定名称统一为 `devDoc/system/`、`devDoc/tasks/` 和项目根 `artifacts/`，同步文档引用、技能示例、本机脚本及 Git 边界，见 [变更记录](../../change_log/minor/20261107_144504_rename-documentation-directories.md)。
- 已建立 [file-structure skill](../../../skills/file-structure/SKILL.md)，支持开发文档与实验路线两类布局；根目录单套 devDoc、始终保留 archive、active 路线收敛及统一 artifacts/runs 的现行约定见 [专项说明](file-organization-plan.md)。来源和初版验证见 [专项调研](research/file-layouts.md)，纲领正文保持原文。
- 已按用户要求将该技能改名为 `file-structure`，同步源码目录、元数据、文档引用与本机发现联接；纲领保持原样，见 [改名记录](../../change_log/minor/20261107_150816_rename-file-structure-skill.md)。
- 已按用户要求重新筛查高星项目、独立口碑和公开实测，建立 [agent-team skill](../../../skills/agent-team/SKILL.md) 指令层初版，以纲领为目标，参考项目只提供机制。[专项记录](research/agent-team.md) 区分第三方证据、本机行为检查和待完成的 P7 对照。
- 已将记忆计划 P0–P5 拆入 `20261106-memory-system`，将资源计划、部署布局和专项调研迁入 `20261107-resource-coordination`；两任务各有 plan/progress，原综合执行计划的共性工作与 P7/P8 归入 [总览](plan.md)。
- 资源 R0–R5 已完整交付共享embedding、Condor入口及公共包/配置，普通wheel源码外联合验收通过；供记忆任务后续复用的接口见 [结果](../../archive/20261107-resource-coordination/result.md)。产品README、使用/管理员说明与resources skill已建立，状态只维护在对应 [进度](../../archive/20261107-resource-coordination/progress.md)。
- 资源后续 R6 已按用户要求切换为通用 Condor 节点容量与同卡显存累计记账，0.2.0 普通 wheel、四作业共享及 embedding 联合验收完成；见 [专项结果](../../archive/20261107-resource-coordination/native-condor.md)。
- 资源 R7 已交付0.3.0普通wheel与Condor原生提交转换；用户只填官方GPU字段，站点内部资源由Condor管理。四项同卡、第五项排队、默认整池、取消与embedding联合实测通过，见 [R7结果](../../archive/20261107-resource-coordination/standard-submit-result.md)。
- R8 的源码归组、实例目录、接口整理与统一迁移已经交付，详细结果从 [资源进度](../../archive/20261107-resource-coordination/progress.md) 读取；R8 设计与验收保留为历史依据。
- 先前完成现成库/软件调查与 [R9 复用路线](../../archive/20261107-resource-coordination/plan.md#r9-复用优先的资源实现)，随后已实际落地 Sentence Transformers＋LitServe＋Shawl，退役旧模型/服务与一次性迁移实现；交付和失败修正见 R9 结果。记忆后续接入结果见专项进度。
- 已补充 [后续维护的简化](plan.md#后续维护的简化)：原生环境与接口、上游补丁替代、旧接口/迁移退役、数据导出和可复用的小型回归；资源与记忆计划给出实际交付及按需复查条件，不增加当前实施前置。
- 已按用户要求将一次性测试和临时材料的默认位置设为项目根 `tmp/`，按任务结束后随时可清除处理；`artifacts/` 保留有长期复核需要的材料。规则见 [文档维护约定](../../documentation.md)，前次材料迁移映射现位于 `artifacts/runs/tmp-reorganization-20261108/moves.json`；此次路径变动与旧路径回查见 [迁移结果](../../archive/20261109-project-layout/result.md)。
- 已根据 main `5d72275` 重评 [记忆计划](../20261106-memory-system/plan.md)，完成源码与官方底座能力静态复核，补齐启动实收、真实评分、增量/恢复、图与图片向量、HDD 及成本验收；当时仅交付文档；本轮已进入实际实现与安装，现状见专项进度。
- 按用户多层次要求重新联网调研并更新记忆方案，保留 [多层调研](../20261106-memory-system/research/multilevel-retrieval.md) 与旧代码核查；后续按已提交纲领加入同读智能分块，并收敛首期 SurrealDB。记忆实施规则在专项维护，总览删去重复阶段依赖，两个任务目录保留职责分工。

## 阻碍与待核

- array reconstruct 的 0.6.2 迁移只复制了两项 skill 原件，缺少 `.agents/skills` 发现入口；当前 init/core doctor 同样不覆盖技能安装与发现验收。已完成版本、时间与隔离复现调查，修复待实施，见[调查记录及 Issue 草稿](research/array-skill-discovery.md)。
- 文件结构建议已有独立 skill；真实大项目迁移、未来布局及记忆读取效果继续按实际任务验证，记忆自用验收见 [独立任务](../20261106-memory-system/plan.md#devdoc-自用与读取轮数)。
- 分层协作已有指令层初版，[P7](plan.md#p7-分层-agent-组织) 仍需真实广读任务的能力与成果质量对照。主上下文、团队总用量和耗时单独记录，允许增加用量换取质量提升。

## 下一步

独立 [engineering-judgment skill](../../../skills/engineering-judgment/SKILL.md) 已编写、保留并接入，见[交付结果](../20261110-engineering-judgment/result.md)。按用户最新要求取消技能测试与按收益去留，效果在长期真实使用中观察；源码和入口已提交 f8bb5b2。

[basePack整改](../20261110-rectification/progress.md) 已完成故障修复、查询/维护解耦与 CPU/CUDA 适配的源码；0.7.0 普通 wheel 在 Python 3.14 完整回归 255 项通过、无跳过，共用客户端升级与最终实际结果沿该进度维护。自动维护随业务结束停止，积压只提醒；正常浮点差异按等价处理。阵列业务事项仍留其项目。

用户已选择 MIT，[0.6.4 许可补丁](https://github.com/YS-Pan/basePack/releases/tag/v0.6.4) 已发布，GitHub 仓库识别为 MIT；源码、独立包许可证和元数据同步，定向构建/安装及附件下载校验通过，详见 [发布结果](github-publish-result.md#mit-许可补丁-064)。0.6.3 原标签和附件保留，项目记忆不上传。

首次上传 GitHub 已完成：源码推送至 [YS-Pan/basePack](https://github.com/YS-Pan/basePack)，[v0.6.3 开发版](https://github.com/YS-Pan/basePack/releases/tag/v0.6.3) 附普通 wheel 与校验和。源码 201 项回归、纯净安装、真实增量维护、新 shell、新聊天、远端 clone 使用闭环及附件下载校验通过，见 [发布结果](github-publish-result.md)。本项目记忆、数据库、配置、凭据与运行原证均未上传。完整空白 Windows/GPU/Condor 新机部署仍待独立机器验收；项目继续开发，实际使用兼作测试样本。

1. 记忆本轮实施与PPT实测反馈修复均已交付；后续沿 [记忆专项进度](../20261106-memory-system/progress.md) 按实际资料维护。三题业务小对照未见记忆质量优势，完整费用不可核，不宣称成本净收益。
2. 文件结构和分层协作在实际任务中继续验证；联合发布按 [总览 P8](plan.md#p8-联合交付与轻量发布) 执行。
