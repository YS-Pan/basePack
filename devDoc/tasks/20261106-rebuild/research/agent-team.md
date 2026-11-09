# 分层 agent skill：参考与验证

路径追溯（2026-11-09）：下文保留当时的运行路径；选留原证现归根 `artifacts/runs/<原批次>/`，位置映射见[布局迁移结果](../../../archive/20261109-project-layout/result.md)。

2026 年 11 月 7 日。目标来自 [项目纲领](../../../project-charter.md#ai-agent的组织体系)：扩大可处理的材料范围、集中各角色上下文，由协调层接走日常派工。外部项目只提供参考，不替代这些要求。[agent-team skill](../../../../skills/agent-team/SKILL.md) 独立编写，使用宿主订阅 subagent，无第三方框架依赖。

## 筛选结果

按 star、独立使用反馈和公开实测分别核查，优先采用可追溯材料。star 是关注度，社区案例是个体经验，兼容性测试与最终任务效果也分别处理。协作效果以 [性能定义](../../../terminology.md) 中的任务能力与成果质量为准；第三方用量和耗时保留为代价记录，是否节省用量不作为采用或验收条件。

star 为 2026-11-07 00:51:44 北京时间的 GitHub REST 快照，OpenHands 为同次调查稍早查询；每行链接到元数据来源。旧 GSD 已归档，后继仓库单独计数。

| 项目 | stars | 证据及本次取舍 |
| --- | ---: | --- |
| [Superpowers](https://api.github.com/repos/obra/superpowers) | 313,443 | 有独立 Codex A/B、官方行为评估和正负用户反馈。主要参考窄任务说明、上下文隔离与明确整合职责。 |
| [GSD 旧库](https://api.github.com/repos/gsd-build/get-shit-done) / [GSD Core](https://api.github.com/repos/open-gsd/gsd-core) | 64,155 / 11,297 | 当前 Core 默认分支为 `next`。参考协调者依赖派工与状态交接；公开兼容性测试不等于分层性能评测。 |
| [oh-my-codex / OMX](https://api.github.com/repos/Yeachan-Heo/oh-my-codex) | 33,728 | Codex 专用，有配置实验和带日志的故障修复。参考完成/失败状态及等待；暂不引入其 tmux 运行时。 |
| [OpenHands](https://api.github.com/repos/OpenHands/OpenHands) | 92,809 | 有任务分数、成本、耗时及轨迹。作为效果证据参考；其 API/SDK 不作为订阅调用依赖。 |
| [Ruflo](https://api.github.com/repos/ruvnet/ruflo) | 81,062 | 高星，但所查 [benchmark 规格](https://github.com/ruvnet/ruflo/blob/perf/sota-comparator-benchmarks/docs/benchmarks/sota-workload-spec.md) 包含 stub LLM 模式，主要测框架开销；[执行 provider](https://github.com/ruvnet/ruflo/blob/main/v3/%40claude-flow/cli/src/mcp-tools/agent-execute-core.ts) 也非原生 Codex 订阅。本次不作主要实现依据。 |

## 实测、口碑与适用范围

### Superpowers

[实际并行派工 skill](https://github.com/obra/superpowers/blob/main/skills/dispatching-parallel-agents/SKILL.md) 按独立问题域分工，提供自足而聚焦的目标、范围和预期输出。[SDD](https://github.com/obra/superpowers/blob/main/skills/subagent-driven-development/SKILL.md) 的叶子执行者限制与固定审阅流程不适合作为本项目的通用组织约束。

独立作者的 [AgentStackBench](https://github.com/Nobbettt/AgentStackBench) 使用已认证本地 CLI，可复用订阅。[实验配置](https://github.com/Nobbettt/AgentStackBench/blob/main/results/run_suites/codex-superpowers-mounted/public-artifacts/experiment.json) 与 [汇总数据](https://github.com/Nobbettt/AgentStackBench/blob/main/results/run_suites/codex-superpowers-mounted/public-artifacts/summary.json) 公开：500 个维护任务，两组同用 GPT-5.4/high，解决率 45.6% → 47.8%。[作者报告](https://norbert-laszlo.medium.com/can-a-plugin-improve-codex-benchmarking-the-superpowers-plugin-05d020066565) 判断差异不显著，平均 token 约 1.56M → 2.18M、耗时 6m13s → 7m26s；token 增加主要来自 cached input。它评价的是当时完整技能快照，不证明当前模型或三级组织的收益。

[官方 Codex 效率实验](https://github.com/prime-radiant-inc/superpowers-evals/blob/main/docs/experiments/2026-07-28-codex-efficiency-campaign.md) 保留 scorer、负结果和归因修正。其中跨四类语料观察到的九次 depth-2 派工，均是执行者另派 reviewer，同时控制者也为同一任务派 reviewer。由此借鉴的是明确复核负责人、消除重复，而非禁止协调者继续分层。其短等待反复超时的调查支持使用宿主事件/等待机制，具体工具与时长按当前接口处理。

口碑有具体正评，也有成本异议：[HN 用户](https://news.ycombinator.com/item?id=48768209) 称新版减少独立任务的人工照看，但未明确 Codex；[Codex 用户讨论](https://www.reddit.com/r/codex/comments/1utg8yn/has_superpowers_made_codex_gpt56_slower_for_you/) 反映小任务也经历长计划和多轮审阅。均为个体经验，不能替代任务能力与成果质量的对照；额外开销本身不否定性能提升。

### GSD / GSD Core

[execute-phase](https://github.com/open-gsd/gsd-core/blob/next/gsd-core/workflows/execute-phase.md) 展示协调者分析依赖、分波次派工并汇总；[agent contracts](https://github.com/open-gsd/gsd-core/blob/next/gsd-core/references/agent-contracts.md) 明确成果与阻塞交接。[Codex parity 测试 #860](https://github.com/gsd-build/get-shit-done/issues/860) 记录迁移者的 20 多项 transcript-first 测试及工具、路径和交接缺口，是兼容性证据。

[用户的安全改造案例](https://www.reddit.com/r/ClaudeCode/comments/1qnh2db/i_finally_decided_to_use_gsd_for_claude_code/) 给出研究、实施和整合后补缺的实际过程，同帖也有阶段推进与研究开销的抱怨；这是 Claude Code 经验，未公开严格对照。[Codex capability](https://github.com/open-gsd/gsd-core/blob/next/capabilities/codex/capability.json) 含外部 CLI/worktree 模式，不能把完整 GSD 当作当前聊天原生三级能力。只借依赖与交接，保留本项目的动态层级。

### OMX

[team](https://github.com/Yeachan-Heo/oh-my-codex/blob/main/skills/team/SKILL.md) 与 [worker](https://github.com/Yeachan-Heo/oh-my-codex/blob/main/skills/worker/SKILL.md) 有任务领取、mailbox、完成和失败报告。team 明确禁止 nested Team；[README](https://github.com/Yeachan-Heo/oh-my-codex) 主推 macOS/Linux CLI，原生 Windows/App 支持较弱。

[Astra 配置实验](https://github.com/Yeachan-Heo/oh-my-codex/blob/main/ASTRA_EVAL_RESULTS.md) 有六个 fixture、四组配置、24 次 run，但无原生 Codex 对照。[mission](https://github.com/Yeachan-Heo/oh-my-codex/blob/main/missions/astra-default-evaluation/mission.md) 说明只检查返回文字，不能证明实际编辑或运行测试；[records](https://github.com/Yeachan-Heo/oh-my-codex/blob/main/missions/astra-default-evaluation/records.json) 的 `requiredChecksPassed` 全为空，不能据此背书验收或节省比例。

[Issue #3149](https://github.com/Yeachan-Heo/oh-my-codex/issues/3149) 有用户日志和维护者复现：通用续跑逻辑也唤醒子 agent，放大了开销；对应 PR #3180 已合入修复。本 skill 只借“下级达到委托终点即返回、下一阶段由负责者接续”，不把已修复故障当作当前版本的普遍缺陷。

### 补充效果证据

OpenHands 公开的同模型、同 agent v1.15.0 记录中，[普通 agent](https://github.com/OpenHands/openhands-index-results/blob/main/results/claude-opus-4-6/scores.json) 与 [subagents](https://github.com/OpenHands/openhands-index-results/blob/main/alternative_agents/openhands_subagents/claude-opus-4-6/scores.json) 都为 76.8%，后者每题 API 成本 $0.85 对 $0.77、平均耗时 262 对 207 秒。运行日期不同，不能视为严格消融，也不能换算为 Codex 订阅费用。

广读任务另有 [Anthropic Research 一手经验](https://www.anthropic.com/research/multi-agent-research-system)：内部研究评估报告 90.2% 的提升，但未公开完整题集和轨迹；多 agent 约为聊天 15 倍 token，这个基线不是单 agent。它支持按任务可分解性选择组织方式，不支持给本 skill 写收益承诺。

## 本版设计与验证

本版保留动态组织、一次委托、协调层管理分支、干净任务上下文、定向共读、输出负责人、事件等待和精选交接。模型按难度与宿主能力选择，审阅按实际需要安排；需要续接时沿用项目进度材料。

Codex 的调用边界参照 [官方 subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents) 与 [skills](https://learn.chatgpt.com/docs/build-skills)。本版只分发 skill 与 UI 元数据；没有引入 API、队列、数据库或跨进程运行时，也没有修改宿主全局配置。

实际检查：

- 标准 `quick_validate.py` 通过；UI YAML、UTF-8、本次文档的本地链接与锚点、`git diff --check` 通过。
- 小任务：独立新上下文 agent 使用 skill 修改隔离笔记标题，未派工；主 agent 按完整预期字节核对，其余内容、换行与编码保留。
- 三级协作：主 agent 一次把交付评估交给新上下文协调者；协调者自行派两个只读执行者，分别阅读需求/状态与排期/检查记录，再共读相关原文并独自汇总。四份材料共 20 行，报告的 15 处来源定位可达，原材料哈希未变。根只核对团队记录和最终报告，不为孙级任务逐项派工。
- 结果正确区分周五文字演示、未完成的现场 CPU 图片链路、下周二最早可测试与完整验收日期待定；没有将开发者成功缓存或文字小样本当作完整交付。原始 fixture 与报告留在本机忽略目录 `artifacts/agent-team-smoke/`。
- 本次开始时用户已有的纲领修改未纳入本次提交；纲领 SHA-256 与开始时一致。本版没有安装第三方代码、配置全局 skill 入口或新增模型 API。

以上是两个小场景的行为检查，未测试超大材料容量、不同模型的路由、断线恢复或团队总成本。P7 的真实广读对照仍需结合记忆工作开展，重点验证任务能力与成果质量是否提升，并单独记录代价。

## 2026-11-09：实际审计与交接规则修订

本轮完整读取 20 个既有主聊天（含一个附属分支）和 113 个协作子线程，共 285 个 turn；排除本次审计和自动审批线程。聊天经 App 全部分页读取，组织树按实际父子来源重建；继承日志里的祖先调用不重复计数。原始派工正文存在加密、大工具输出存在截断，重要结论另核选定原证；没有将列举摘要当作消息审阅。

实际交付中的独立验收发现过排队 52 秒被报告为 0、迁移覆盖业务文件等缺陷，并推动修复。R8 有 9 个直属、5 个孙级 agent，局部协调者确实承担了分支管理，见 [R8 交付](../../../archive/20261107-resource-coordination/maintenance-result.md)。但主 agent 仍承担不少日常管理，部分下级已查明的关键前提未进入上级表达。11 月 7 日英文版发布后，审计范围内的 71 个子 agent 中，57 个继承历史、14 个使用新上下文，均使用 Sol；相关任务继承背景可以合理，这些数据本身不能证明注意力干扰或模型选择错误。任务、宿主主动派工模式和用户指令不同，缺少同题对照，不能据此量化技能的独立收益。

本轮再查的实现支持几项小改动：[Pi 的默认新上下文解析](https://github.com/nicobailon/pi-subagents/blob/3ff4f75545edf2695d5ea82bf46a1ea9ef2008a8/src/shared/fork-context.ts#L83-L86)是工具层默认值；[Superpowers 的约束传递问题](https://github.com/obra/superpowers/issues/2493)与[完成报告问题](https://github.com/obra/superpowers/issues/2451)说明，原则写在文档里仍可能未进入实际 brief 或报告；[Anthropic 的工程记录](https://www.anthropic.com/research/multi-agent-research-system)采用保存原产物、向协调者传引用来减少多层转述失真。外部机制是参考，没有安装这些项目，也没有把其效果当作本技能验收。

修订将既有原则落实到显式上下文选择、任务用途和约束、分支派工负责人、原产物交接、短回传及消费成果时的整合动作；具体规则只维护在 [skill](../../../../skills/agent-team/SKILL.md)。文件沿用各项目约定，小结果可以直接返回；本项目的临时、文档和留存边界继续由[文档维护约定](../../../documentation.md)维护。技能名、触发描述、UI 元数据和项目内发现联接继续适用，交付仍只有指令与原有元数据，无新增脚本、依赖、配置或服务。

本轮完成标准技能校验、UTF-8 与相关本地链接检查、独立只读差异审阅和 `git diff --check`；未新增行为测试或重跑部署。上述改动是指令调整，P7 的真实广读能力与质量对照仍未完成。
