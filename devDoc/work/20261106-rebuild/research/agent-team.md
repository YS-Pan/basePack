# 分层 agent skill：参考与验证

2026 年 11 月 7 日。目标来自 [项目纲领](../../../project-charter.md#ai-agent的组织体系)：扩大可处理的材料范围、集中各角色上下文，由协调层接走日常派工。外部项目只提供参考，不替代这些要求。[agent-team skill](../../../../skills/agent-team/SKILL.md) 独立编写，使用宿主订阅 subagent，无第三方框架依赖。

## 筛选结果

按 star、独立使用反馈和公开实测分别核查，优先采用可追溯材料。star 是关注度，社区案例是个体经验，兼容性测试与最终任务效果也分别处理；未发现同时证明“三层更优且更省 Codex 订阅”的成熟通用方案。

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

口碑有具体正评，也有成本异议：[HN 用户](https://news.ycombinator.com/item?id=48768209) 称新版减少独立任务的人工照看，但未明确 Codex；[Codex 用户讨论](https://www.reddit.com/r/codex/comments/1utg8yn/has_superpowers_made_codex_gpt56_slower_for_you/) 反映小任务也经历长计划和多轮审阅。均为个体经验，不据此认定普遍好评或省钱。

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
- 结果正确区分周五文字演示、未完成的现场 CPU 图片链路、下周二最早可测试与完整验收日期待定；没有将开发者成功缓存或文字小样本当作完整交付。原始 fixture 与报告留在本机忽略目录 `.work/agent-team-smoke/`。
- 本次开始时用户已有的纲领修改未纳入本次提交；纲领 SHA-256 与开始时一致。本版没有安装第三方代码、配置全局 skill 入口或新增模型 API。

以上是两个小场景的行为检查，未测试超大材料容量、不同模型的路由、断线恢复或团队总成本。P7 的真实广读对照仍需结合记忆工作开展，尚不作收益承诺。
