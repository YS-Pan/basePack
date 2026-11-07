# 重建进度

更新：2026 年 11 月 7 日（北京时间）。

## 当前阶段

重建大阶段进行中，文件结构与分层协作 skill 初版已建立，记忆及资源协调运行工具待实施。2026 年 11 月 7 日用户指定下一阶段先做资源协调，按 [专项计划 R0–R5](resource-coordination-plan.md) 推进，不等待记忆系统。P0 的 Git 仓库和忽略规则已具备；已完成一次 [只读环境核验](../../system/environment.md)，运行接入、底座选型与产品骨架待完成。P0–P8 保留为原实施步骤编号，当前先推进 P6；文件结构工具按 [专项计划](file-organization-plan.md) 独立推进。

## 已完成

- 已形成项目纲领、[简短实施计划](plan.md)、[旧项目近期历史](legacy-history.md) 和 [精选调研](research/sources.md)。
- 开发文档已集中到 `devDoc/`；README 的介绍与入口已合入根目录 AGENTS.md，重建材料集中在本目录。组织变化见 [变更记录](../../change_log/major/20261106_232701_organize-dev-docs.md)。
- 文档维护规则、术语、现行结构与环境说明已补齐，交接与调研结论索引已完善；实际结果和检查见 [文档整理结果](result.md)。
- 已按用户选定名称统一为 `devDoc/system/`、`devDoc/tasks/` 和项目根 `artifacts/`，同步文档引用、技能示例、本机脚本及 Git 边界，见 [变更记录](../../change_log/minor/20261107_144504_rename-documentation-directories.md)。
- 已建立 [project-layouts skill](../../../skills/project-layouts/SKILL.md)，支持开发文档与实验分包两类布局；来源和初版验证见 [专项调研](research/file-layouts.md)。[纲领建议稿](charter-file-layout-proposal.md) 供用户自行填写，正文保持原文。
- 已按用户要求重新筛查高星项目、独立口碑和公开实测，建立 [agent-team skill](../../../skills/agent-team/SKILL.md) 指令层初版，以纲领为目标，参考项目只提供机制。[专项记录](research/agent-team.md) 区分第三方证据、本机行为检查和待完成的 P7 对照。
- 已按用户要求先读旧项目 [相关 Codex 聊天再核代码](research/resource-coordination.md)，确认多模态 runtime、批处理、项目局部热复用、超时与进程清理可提取；跨项目统一实例、共享取消、普通任务薄入口与真实并行仍待实现。
- 已据用户“embedding 与其他 GPU 任务独立、可并行”的纠正重写 [资源协调计划](resource-coordination-plan.md)：提取旧能力，以固定显存预留衔接独立服务与 Condor，替代原模型 worker 入 Condor 和整卡轮流方案。本次完成阅读和计划修订，未运行测试/模型、修改机器配置或提交计算任务。
- 已规划 [安装位置与项目配置布局](deployment-layout-plan.md)：代码统一进系统 Python，模型和共享服务状态在 AgentTools，Condor 独立安装；项目 basepack.toml 引用机器配置，项目数据放 .basepack。规划包含 AGENTS 读取入口、初始化模板与未来 GitHub 接入说明，尚未建立实际配置或安装包。

## 阻碍与待核

- 11 月 6 日 HTCondor 状态与队列查询因缺少配置源退出，尚未进入旧调查记录的认证阶段；11 月 7 日只读复核已看到注册表配置入口，但未重跑查询。接手先核配置来源，再验证查询与提交，详见 [环境说明](../../system/environment.md)。
- 检索底座、包名和动作接口待 P0 确定。旧项目的任务状态与验收结论继续作为历史依据。
- `devDoc` 少轮读取已纳入 [P1/P3/P4 自用与验收](agent-plan.md#devdoc-自用与读取轮数)；预期由本次任务的记忆闭环一并缓解，实际往返、信息完整性与合计用量尚未验证。
- 文件结构建议已改为独立 skill，记忆工具可按需引用；真实大项目迁移、未来布局和记忆检索效果按实际任务继续验证。
- 分层协作已提供短 skill；P7 仍需对照真实广读任务的能力范围与成果质量，主上下文、团队总用量和耗时另行记录。按 [性能定义](../../terminology.md) 验收，允许增加用量换取更好的结果。

## 下一步

1. 执行资源专项 R0：先交付系统 Python 包和项目/机器配置入口，再按复用清单提取最小 runtime/服务接口，替换旧整卡锁与门槛，实测 embedding 峰值预算；分别核通独立服务与当前 Condor 配置、认证和真实作业。
2. R1/R2 分别交付跨项目独立 embedding 服务和普通重任务薄入口；R3 验证预算内真实并行，再完成生命周期回归与安装说明，实际结果更新 [系统说明](../../system/overview.md)。
3. 资源工具之后继续记忆 P0–P5：底座比较、可安装记忆骨架、文字闭环及向量/图等；在本页记录实际检查与余项。
