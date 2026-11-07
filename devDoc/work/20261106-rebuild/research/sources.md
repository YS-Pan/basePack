# 重建调研依据

本轮以用户 2026 年 11 月 6 日重写的 [原稿](user-plan.original.md) 为意图依据，只读调查旧项目、相关 Codex 聊天和 AgentTools。以下精选证据供后续实施按需阅读；它们不构成新项目的运行依赖。新仓库不需要复制旧原证、聊天或模型。

## 按主题找结论与证据

先按主题选材料，再读所需原文。下表归纳既有调查的身份与适用边界；现行用户要求以项目纲领为准，技术细化保留工程建议的身份。

| 主题 | 结论与身份 | 适用范围或待核事项 | 直接证据 |
| --- | --- | --- | --- |
| 项目方向与隔离 | 用户要求：主动未知提示、低成本、项目局部记忆；通用资源可以显式共用 | 约束新项目目标；旧任务、业务授权和验收结论各自保留原身份 | [项目纲领](../../../project-charter.md)、[原始快照](user-plan.original.md) |
| 继承什么、舍弃什么 | 历史事故与归纳：多层协议、重复发布和维护规则增加了固定开销 | 用于选择短流程和保留事故回归；不证明某种模型或底座是唯一原因 | [维护负担的原因](../legacy-history.md#为什么越来越难推进)、[继承与舍弃](../legacy-history.md#新项目继承与舍弃) |
| 图创建与关系发现 | 历史事故：大量分段提交不等于已建立可用的语义关系 | 新实现仍需用有依据的跨材料关系验证建图行为 | [旧项目近期历史](../legacy-history.md#从实验工作区到复杂的自用系统)、[建图专项原计划](<D:/project/20261024 doc system/docs/plans/20261105-graph-maintenance.md>) |
| 检索、评分与交付 | 历史审计：资料召回、评分实际调用和必要证据交付可能脱节 | 核实真实订阅 agent 链路与最终结果，分别报告缺口 | [测试证据与限制](thread-survey.md#读取到的测试证据与限制)、[真实试用审计](<D:/project/20261024 doc system/docs/context/20261102-live-trial-review/report.md>) |
| 主动性与总成本 | 证据限制：旧小样本、合成检索分数和安装回执未证明普遍净收益 | 在新项目按任务质量、未点名信息发现及全周期成本评估 | [测试证据与限制](thread-survey.md#读取到的测试证据与限制)、[历史总结的证据边界](../legacy-history.md#新项目继承与舍弃) |
| 共享模型与资源协调 | 初步调查观察：已有模型、合作式 GPU 锁和 HTCondor；队列查询当时认证失败 | 原调查保留旧时点；按最新核验继续确认配置、接口和认证 | [初步设施调查](#agenttools-当前可复用部分)、[本次环境核验](../../../current/environment.md) |
| 资源工具复用与并行 | 2026-11-07 先读相关聊天，再核源码：多模态 runtime、批处理、局部热复用和进程清理已存在；跨项目服务与并行预算待改造 | 用户明确 embedding 独立且可与普通 GPU 任务并行；旧整卡互斥策略不继承为新要求 | [专项核对](resource-coordination.md)、[详细计划](../resource-coordination-plan.md) |
| 实施路线与待决项 | 工程建议：最短闭环、一次委托、分数排序、批量 I/O 与最小增量维护 | 底座、包名、动作接口和具体预算按实施核定；不是用户指定值 | [AI 执行计划](../agent-plan.md)、[本轮未决问题](#本轮归纳和未决问题) |

## 范围和阅读方式

广泛检索由四个 GPT6Luna/max subagent 分别调查旧项目思想、较早聊天、近期历史和共享基础设施；另由 GPT6.1Sol/ultra 做架构建议与计划审查。主 agent 读取原用户计划、关键计划与结果、近期聊天的选定用户/最终消息，核对当前 C/G 台账后整合。先筛选再向主 agent 交付，避免灌入全部检索过程。

聊天调查枚举本机 active history 17 页、828 条，以及 archived history 1 页、35 条，按旧项目根 cwd 与 test-runs 子目录筛选到 active 61 条、archived 17 条。这是本轮可见记录，按目录过滤可能漏掉改了 cwd 或位于其他项目的关联聊天，不代表该项目历来全部聊天数量。检索名单不等于读过消息；实际阅读范围与抽样见 [聊天调查记录](thread-survey.md)。

近期历史子任务完整读取 [执行Context存储与多模态升级](codex://threads/01a1a975-2747-72b2-8a00-0a64af80e865) 的 1 turn、[整合线程并制定计划](codex://threads/01a1aad7-851b-7512-b8f1-6f136fac8abb) 的 4 turns、[执行综合精简计划与建图专项](codex://threads/01a1ab10-3aba-7532-acd7-b0bf371ee184) 的 2 interrupted turns，以及 [评估并改进实验文件存储方式](codex://threads/01a1a5d5-1644-7202-a9b5-d2888324d491) 的 1 个短 interrupted turn；均读到该次返回的分页终点。实施聊天一 turn 可含数千项，调查选取其中用户消息、关键过程和结果，不把所有工具输出作为结论。较新的其余咨询聊天未全部逐消息读；主 agent 补读版本调查、0.6 交付及多模态规划的选定消息，基础设施子任务完整翻页读取用户指定聊天。

旧项目近期任务仍活动；本轮结果为观察截面。文档里的工程通过、覆盖数量和模型配置应沿其原时点理解，不能跨版本拼成一次全面验收。

## 战略与旧工程的精选文件

| 文件 | 为什么值得读 |
| --- | --- |
| [用户重写原稿](<D:/project/20261024 doc system/docs/user-plan.md>) | 三工具、主动未知提示、局部记忆、机械盘、低成本、订阅调用和简洁要求；本轮另存原字节快照 |
| [旧研究计划](<D:/project/20261024 doc system/docs/research-plan.md>) | 实验方向和历史决策，仅按有关主题选读 |
| [真实试用审计](<D:/project/20261024 doc system/docs/context/20261102-live-trial-review/report.md>) | 评分未被实际调用、业务新鲜度、遗漏交付、维护/字符成本、I/O 与副本合并冲突 |
| [P0–P2 有限结果](<D:/project/20261024 doc system/20261102 context/docs/RESULTS.md>) | 文件组 5/6 对系统组 4/6；Qwen 专项的有限优势和归因限制 |
| [综合精简计划](<D:/project/20261024 doc system/docs/plans/20261105-project-consolidation.md>) | 分段挤占建图、确定性必读、结构要求遗漏与三端交付负担 |
| [建图详版](<D:/project/20261024 doc system/docs/plans/20261105-graph-maintenance.md>) | 关系共读、跨 worker 汇合、增量与随机重访；只取思想，不照搬宿主状态机 |
| [协调简史](<D:/project/20261024 doc system/docs/history.md>) | 0.8.x 连续修补、根 Git、报告式清理及采用截面 |
| [当前任务台账](<D:/project/20261024 doc system/20261102 context/state/tasks.json>) | 本轮观察 C/G 都为 in_progress；0.8.10 安装不等于全库、来源/索引或联合检索已经完成 |
| [两短资料任务原记录](<D:/project/20261024 doc system/20261102 context/evidence/graph-maintenance/fresh-project-084-empty/evidence/release-checks-086/FOLLOWUP086.json>) | 八个预算窗、九次旧流程失败和 281,052 字符，直接揭示维护固定开销 |

## 关键聊天入口

| 聊天 | 与新计划的关系 |
| --- | --- |
| [概括项目核心目的](codex://threads/01a1760b-16a8-7250-b5ef-d41afec9c07b) | 为什么做项目局部、模块化系统 |
| [规划项目级记忆系统](codex://threads/01a170ab-2c0c-77d2-81df-9a1a802aa551) | 早期需求、实验路线与成本取舍 |
| [实现记忆系统试用版并完成初测](codex://threads/01a17b66-18ef-7f20-8044-a768fa4736ff) | trial 的能力与有限测试；历史分数不能跨方案合并 |
| [规划新记忆系统](codex://threads/01a19b84-9e04-7063-a8ef-f39593561423) | 11 月 2 日 Context 方向与成熟底座 |
| [实施简洁记忆系统与双端升级](codex://threads/01a1a5b7-a92d-7353-9b4e-7d3ea7b77404) | 0.6.0 自用交付、压缩日志补齐；不能保留「375 线程永久缺失」旧结论 |
| [规划记忆系统升级](codex://threads/01a1a93d-5208-7503-95ac-4c520b917e2b) | 统一 VL、图片 prompt、分段回填与图维护偏移 |
| [执行Context存储与多模态升级](codex://threads/01a1a975-2747-72b2-8a00-0a64af80e865) | 0.7.7 原工程范围结案；真实图片效果测试被明确留待其他项目 |
| [整合线程并制定计划](codex://threads/01a1aad7-851b-7512-b8f1-6f136fac8abb) | 建图后继范围、取消旧版复验前置、自动维护限于任务内 |
| [执行综合精简计划与建图专项](codex://threads/01a1ab10-3aba-7532-acd7-b0bf371ee184) | 0.8.x 实施、维护流程修补与未完工作 |
| [调查0.8.10版本迭代原因](codex://threads/01a1ae6f-ce9c-7e32-b8d8-7825aafa0655) | 三个 turn 的版本/范围调查和后继讨论；恢复目录要求的用户指令及流程膨胀的具体事故 |
| [查找 context 目录超大原因](codex://threads/01a19f83-a7a4-77e1-b2ab-17893574b078) | 用户指定的基础设施来源，已完整翻页；模型集中、空 profile、HTCondor 和统一入口未实现 |
| [查找模板中的 subagent 组织建议](codex://threads/01a156e8-e8c6-7bd0-9dbd-622ebf0f33f8) | 协调层的目的和灵活分工 |
| [继续三层 subagent 协作](codex://threads/01a1156f-88a7-7852-b1e8-9c6eada278f1) | 分层管理与按依赖安排并行 |

## AgentTools 当前可复用部分

基础设施 subagent 本轮只读观察 `D:\AgentTools`：顶层有 `models/`、空 `profile/`、`state/`。模型目录保存五套固定版本，逻辑总量约 15.42 GB；并非所有依赖与调度代码均已集中于此。系统 Python 3.13.17 和 169 项依赖闭包是历史部署报告，当前实施前再核实际环境。

五类现有模型为 BGE reranker、E5-large、文字 Qwen3-Embedding-4B、多模态 Qwen3-VL-Embedding-2B、MiniLM。各有版本锁。新项目优先复用所需的一套，不重复安装全部；权重及锁运行状态均不进仓库。

已有 `state/locks/gpu-0.lock` 只服务于遵守同一 OS 文件锁协议的项目 Qwen bridge。锁文件存在不能证明正在占用；它不是全机资源管理器，不约束外部直接 CUDA 程序，也没有 FIFO 队列或统一 CPU/RAM 管理。AgentTools 没有已实现的 agent-run/MCP 统一入口。

本轮 `condor_version` 返回 25.4.0，`condor_status -json` 成功看到本机空闲 slot，16 CPU、约 48 GB RAM、一张 RTX 4060 Ti。`condor_q -json` 返回 `AUTHENTICATE:1005`，当前队列不能核实；读取服务状态也被权限拒绝。旧聊天曾报告 job 14255 退出 0，这是历史提交成功，不能替代当前认证核验。

指定聊天中的精确定位，下面时间已换为北京时间：

- 11 月 4 日 09:40，turn `01a1a436-b689-70a0-9063-c06d3c5b62fe`：GPU 锁、CPU/内存/磁盘协调的实际边界。
- 11 月 4 日 10:29，turn `01a1a464-1fe5-7030-8f0f-85b9d32d5060`：agent-run 未实现与 HTCondor 方案。
- 11 月 4 日 10:57，turn `01a1a47d-b449-7131-afd5-b748ae00f857`：历史轻量提交测试。
- 11 月 4 日 11:02，turn `01a1a482-17d5-7a73-afb2-5d99ad06ecfe`：官方 CLI 与 Python/MCP 接入判断。
- 11 月 3 日 21:14–21:57 的相关用户消息：保留空 profile、复用 pip 缓存、模型集中；实施不应反向补建 packages/profile 管理层。

## 本轮归纳和未决问题

从旧项目吸取的已知必读、更正与过期、按真实质量和全周期成本衡量等想法见上述调研。

其余思想进入执行方案：单一维护源、最短完整闭环先行、简单来源版本、批量 I/O、跨 worker 合并、手动/自动共用、可选审核、分数排序、一次委托、多模态与资源准入分离。没有承接旧的十人固定班组、双 Luna 强制链、三份长期工作树或多级审计协议。

实施仍需解决：宿主实际支持的 agent 调用与启动挂接；底座能否做到少文件/批量写；HTCondor 当前认证；Windows CPU/RAM 声明预留的实际行为；真实业务中主动提示与总成本的净收益。它们已放进执行阶段，不是要求用户先提供额外材料才能交付本轮计划。

GitHub 连接器只读查询 [YS-Pan/basePack](https://github.com/YS-Pan/basePack) 得到 public、默认分支 main、size=0；本轮没有写远端。大小预算是执行计划建议，发布前以实际待提交文件和远端引用核对。
