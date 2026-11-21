# 重建总进度

2026-11-21 后续开发计划两项通过 0.18.9 候选回归和隔离联验。两条来源检查命令更新命名和使用指引，共享 embedding 增加短时缓存回收与 Windows 用户任务空闲停机。旧索引随同一模型唤醒后可继续查询。[实际验收与候选包](../20261120-follow-up/progress.md)

2026-11-20 在单库试点后，按用户授权完成其余四库的动态端口推广。三个旧业务库先逐表校验历史桥接，本开发仓接管原 schema 3 的 store。五个在用项目均已登记 30 分钟空闲关闭及按需唤醒，恢复点留在项目本机。共享 embedding 沿用已部署的用户任务。[推广与验证](../20261119-windows-user-runtime/progress.md#2026-11-20-推广到其余项目)

2026-11-20 Windows 动态端口已纳入产品接入。定稿 `0.18.8` 用同一 wheel 完成固定和动态隔离回归、新聊天采集至跨聊天回源、原生导出和独立恢复。随后完成一个已授权的存量库试点，以原 store 和 UUID 动态启动和读回，最终设置 30 分钟空闲停机。其余项目的就绪探测通过。用户已取消协调者和读者的固定人数上限，实际组织按工作量、宿主席位和每波发布职责执行，纲领由用户更新。[托管验收](../20261119-windows-user-runtime/progress.md#2026-11-20-动态端口产品接入与单库试点) · [现行派工](../20261115-real-use-rectification/maintenance-waves.md#组织与边界)

本开发仓的 0.18.6 自动维护本次通过普通用户采集和全项目预检，按实际宿主派出一个协调者及一个读者。主业务结束时中止未提交的波次，核无在途发布后释放持有权。语义工作集留待下次维护。

2026-11-20 [下一轮实施与联验](plan.md#下一轮实施与联验)的首轮隔离候选已走通固定端口停机、唤醒和新聊天回源。一个 0.18.7 wheel 完成普通安装、默认全项目自动维护预检、合成聊天的实际发布及另一真实聊天的字节一致回源。动态端口以独立原生探针验证。现有项目库接管和发行留后续。公开最新版与本项目普通客户端均为 0.18.6。[Windows 实测](../20261119-windows-user-runtime/progress.md#2026-11-20-隔离候选包) · [记忆实测](../20261115-real-use-rectification/progress.md)

此前 Windows 托管代码已通过项目库及 CPU embedding 在整机重启后的隔离启动。共享 CUDA embedding 已正式切到用户任务，四个项目已复验。动态端口的 basePack 产品接入、代表性存量机械盘收益和固定端口正式单库试点留专项。[Windows 运行进度](../20261119-windows-user-runtime/progress.md)

本开发仓仍装 0.18.6。本次任务启动时，沙箱内的常规采集遇到 SQLite 14，保留失败回执，未取得原库维护所有权。隔离候选采集使用候选包的单次 Auto Review 路径。

同日一致性复核。固定端口核心联验、获授权的单库试点与动态端口专项验收已分开安排。0.18.7 的采集实证已交接到现行整改，项目入口已转指该专项。旧专项原证留原处，物理归档待核余项及引用。

以下记录保留形成时点，已被最新用户决定替代的方案不再执行。

2026-11-17记忆方案按当时用户选择改为[Gaussian连续降权、低权重保留](../20261115-real-use-rectification/forgetting-options.md)，撤销低效用退出/回收并修正Gaussian累计公式及成本；完整系统前后图共用未改动部分的布局。当时产品仍为 0.16，代码、数据库、原件、纲领和外部项目未改。

2026-11-17记忆后续计划已按用户接受长期全域遗忘的澄清补齐[模糊遗忘选项](../20261115-real-use-rectification/forgetting-options.md)与实际退出闭环；默认线性核，平方/Gaussian作备选，不新增硬主题类别或常驻服务。代码、数据库、业务原件与项目纲领未改；详情沿该任务计划/架构/进度维护。

2026-11-17经[连续遗忘补研](../20261115-real-use-rectification/research/similarity-forgetting-20261117.md)，记忆长期方案改为纯行为KL-NMF＋连续相似度机会年龄，取代旧局部钟主线；认知类比与工程有效性分开，概况/主动提示不被模型训练阻挡。现行方案与状态分别沿该任务计划/架构/进度维护，本轮仅改研究和文档，未改0.16实现、安装或外部项目。以下记录保留各自历史时点。

2026-11-17已按用户长期优先级收敛[记忆长期整改计划](../20261115-real-use-rectification/plan.md)：采集/语义/编译分责，KL-NMF统一行为坐标与可重放局部访问，当前0.16图与目标图分开。技术、批次和实际状态分别沿该任务架构/计划/进度单一维护；本轮只改方案与说明，未实现、安装或操作外部项目。同步修正system失用版本入口与旧研究候选身份。

2026-11-16 已实施并[公开发行0.16真实使用整改](../20261115-real-use-rectification/result.md)：大源快照、M2维护入口／启动清理、C1有限来源组、C2同轮干净接续和S2原位私有版本合同已交付，本项目客户端普通升级且知识／配置不变量保持；真实宿主两阶段及有界Condor账户／工件验证通过。用户限定本项目并追加GitHub push／Release，均已完成，公开附件／Latest已核；共享服务保持0.15，外部项目未操作，token节省未实测。以下条目的“仅计划”保留为当时历史状态。

2026-11-16 已按用户要求整合[当前整改计划](../20261115-real-use-rectification/plan.md)，修正尾部追记与正文／批次的冲突：大源快照和当前成果可见性进入正式批次，C1／C2不再等待S2或外部迁移，S2按布局、R1复用既有真实证据。四图、实施顺序、真实验收与用量假设已归一；只完成计划维护，未实施或操作外部项目。

2026-11-16 已核[协调者／worker通信与组织形态](../20261115-real-use-rectification/research/coordinator-communication-20261116.md)：作者完成报告已紧凑，主问题转向细粒度反复派工、长期历史重放和无过滤全树状态带入；有交稿后改稿的具体返工，也有应保留的语义修复。现有多路径prepare与E可支撑有限来源组，不假定自主领任务或句柄接管能力。C1／C2据此细化，仍只研究和方案，未实施。

2026-11-16 已完成[迁移与长科研任务复盘](../20261115-real-use-rectification/research/robotic-arm-review-20261116.md)：迁移检索／恢复、条件性科学结果和真实Condor重任务都有依据。新增大文本snapshot发布上限，细化最新成果入记忆的时序、长turn原证取回、执行账户／工件／多进程资源范围及用量归属。原位private资料未复现上一项目的额外镜像；推荐按场景选S2。证据补入现行待选整改计划，未实现、迁库或修改外部项目。

2026-11-15 已形成[真实使用整改计划与方案](../20261115-real-use-rectification/plan.md)，包含4张逻辑框图。推荐官方显式跳过新聊天采集、原位来源配置私有范围、收敛协调上下文及复用HTCondor真实重任务接入；保留隐私分类的历史版本、单owner和原生资源权威。当前仅方案文档，选择未定，未实施或迁移外部项目。

2026-11-15 已补[真实业务写作轮接续复盘](research/real-project-review-20261115.md#五后续实际业务轮复用成立资源边界暴露)：从建库可用推进到14页试写稿及可重新编译／绘图的证据包，检索交付、阶段授权更新、单频约束接受及维护收尾均有实际依据。新增暴露原生求解器频率并行与内存边界；本轮Terra主要用于仿真执行，不能沿首轮维护归因。私有镜像和collector入口问题未修复，实际成稿不等于质量／成本净收益或无人工干预能力。

2026-11-15 已完成用户点名的[维护用量与从零建项目复盘](research/real-project-review-20261115.md)：E实际投入使用，但长上下文和短等待仍放大Terra缓存输入；新项目真实功能闭环成立，基础设施／摄入分支约占全队本地total的70.84%。新增明确Origin部署示例问题，并记录私有路径与业务布局的镜像代价、非必需匿名化返工及官方文件维护入口不足。只交分析及问题接续，未实施修复；业务内容未写入公共正文，质量与成本净收益保留未验证。

2026-11-15 工程状态接续：已按用户授权完成0.15.0的cuDNN／32768-token／柔性9 GiB、发布组合E和项目局部ongoing，本项目稳定客户端与共享服务均已升级，见[交付结果](../../archive/20261115-runtime-and-maintenance/result.md)。本目录继续承接跨工具总跟踪；下段“只维护计划／未实施”为实施前历史状态。已完成的独立任务按各自交付结案归档，后续具体需求另按所属任务推进。

更新：2026 年 11 月 15 日（北京时间）。

## 当前阶段

2026-11-15 用户已选E，已整合[cuDNN、E与ongoing最终计划](../../archive/20261115-runtime-and-maintenance/plan.md)：CUDA cuDNN／模型32768 token，文本长度统一token判定并退役64 KiB限制；9 GiB为柔性目标，纯文本初始batch4、图batch1；E仅新增稳定发布helper及同源薄CLI，保留原子工具自由组合，完整cycle及B／C／F新接口退出本轮；ongoing默认实际创建后7天，发现到期整目录归档、不自动续期。已清除待选状态、交稿完成／整聊天结束及固定稿接续／真实改稿重冻等歧义，研究稿标历史比较。本轮只维护计划及入口，源码、prompt、AGENTS、机器配置和共享服务未实施改变，生产仍有原硬限；[案例分析](../../archive/20261115-runtime-and-maintenance/research/d-flexibility-20261115.md)及其普通维护收尾保留。

2026-11-14 已按用户授权交付[0.14.0私有上下文与记忆标记](../../archive/20261114-next-maintenance/result.md)：独立 `private/` Git、默认入同库、固定版本布尔标记、skill/文档与本项目稳定客户端均已落地。源码634项经环境修正后覆盖通过，普通wheel真实流程及恢复库十表对照通过；完整恢复资料保留，旧副本未核范围如实记录。随后按明确授权推送源码并发布[常规版v0.14.0](https://github.com/YS-Pan/basePack/releases/tag/v0.14.0)，三个附件下载哈希通过；公开记忆分享工具仍未建设，本批收尾见[进度](../../archive/20261114-next-maintenance/progress.md)。

2026-11-14已执行[既定交付收尾计划](../../archive/20261114-delivery-closeout/plan.md)，结果见[0.13交付](../../archive/20261114-delivery-closeout/result.md)：记忆调用/脚本覆盖、UUID冻结协议和本项目全量迁移/同步切换、Condor原生职责收敛及共享服务422诊断部署均已完成。源码618项全套通过，普通wheel最短流程、原证/历史/图/交付恢复、真实CPU作业和共享图文/错误定位均有实际依据。随后按用户明确授权推送源码并发布[v0.13.0.dev1开发版](https://github.com/YS-Pan/basePack/releases/tag/v0.13.0.dev1)，三个附件下载哈希通过。用户负责收益、协作效果及新机分发部署反馈，agent未来据证据分析修改；三工具及外部阵列正式库沿其所属项目接续。

2026-11-12 已执行[使用整改计划](../../archive/20261112-usage-rectification/plan.md)：源码与本项目普通客户端升级至0.12.0.dev1，交付任务级直接brief、默认检索请求、精确知识历史与纯访问状态，以及超限输入诊断源码。623项全套通过，原生恢复/反馈跳过项随后8项单独通过；真实阵列副本检索及历史版本/交付恢复通过。外部项目与共享服务未升级，数据原件未清理；质量/成本、服务部署及积压边界沿[整改进度](../../archive/20261112-usage-rectification/progress.md)接续，不把模拟或安装等同语义现行性。

已按用户要求于 2026-11-11 19:01（北京时间）公开发布 [0.9.1 开发版](https://github.com/YS-Pan/basePack/releases/tag/v0.9.1)，附普通 wheel 与 SHA256 校验和；重建包等价检查、隔离普通安装及附件下载校验通过，详见[发布结果](github-publish-result.md#091-开发版)。发布包含现行 0.9.1 功能与维护调查文档，不将候选实验或待实施方案标为已修复。

近期一致性评估、0.9.1 修复及固定维护检查点已验收，历史依据见[归档进度](../../archive/20261111-consistency-review/progress.md)。全项目知识维护继续沿[记忆系统进度](../20261106-memory-system/progress.md)推进。

已结束的 engineering-judgment、0.7.1 整改、0.8.1 接入简化、0.9.0 worker prompt 和 0.9.1 一致性修复任务已整体归档；本目录继续维护跨工具工作，记忆专项继续维护未完成知识目标。

当前唯一 active 路线为 [20261106-basepack](../../../experiments/20261106-basepack/README.md)，源码、构建声明、测试、产品文档、示例及资源和记忆 skill 在该实验工程内维护；根目录保留统一 devDoc 和三项通用技能。本次布局迁移的实际检查与接续见 [迁移结果](../../archive/20261109-project-layout/result.md)，不改变 R9 和记忆功能的完成状态。

2026-11-12 [维护试验及固定范围记忆维护已完成](../20261106-memory-system/maintenance-implementation-result.md)，唯一active源码面向0.10.0.dev1；候选合回后只保留试验入口，源码不长期双维护。该残留入口已于2026-11-14按用户要求清理，历史及原证沿实施结果保留。默认无审计、轻量反馈、程序父/依赖保护、AGENTS动作入口、透明事务分包、B/F、单维护owner及清理已实施。完整候选482通过，原五个跳过项后续全部真实补测通过；本项目新独立客户端已接入，其它项目0.9.1环境和共享服务未改。显式回执767来源全部结案，三条反馈修复，最终提示词已安装且owner释放；捕获边界及后续材料沿记忆专项结果接续，未宣称粗层策略已降低总成本。

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

- array reconstruct 原遗漏的两项 skill 发现入口已按本轮计划补齐，官方 `skills/list` 返回两项 `scope=repo`、`errors=[]`，外部 main 提交 `931634e`。完整目录、引用、冲突与发现核验已纳入产品接入说明；init/core doctor 的职责仍不等同于技能安装与发现验收，见[调查接续](research/array-skill-discovery.md)与[文档结果](../../archive/20261110-onboarding-simplification/documentation-result.md)。
- 文件结构建议已有独立 skill；真实大项目迁移、未来布局及记忆读取效果由用户实际项目反馈接续，agent据具体问题修改；当前责任见[收尾计划](../../archive/20261114-delivery-closeout/plan.md)。
- 分层协作已有指令层初版，[P7](plan.md#p7-分层-agent-组织) 的能力与质量效果按用户真实反馈接续，不再要求agent在本机跑正式对照；可得用量与耗时仍分别记录。

### 2026-11-19 用户反馈复核

对照发布版 `v0.18.6`（`78b3ade`）和 0.18.7 开发源码（`4a034d6`）。下列产品修改均待实施。

- **草案和冻结批次。** 将带固定 `prepare` 的有效草案包成数组，`freeze` 仍抛无文件名的 `TypeError`。成员缺 `path` 时，草案编译、波次提交和直接 `apply` 均仍抛 `KeyError`。建议在各外部入口检查草案形状和成员必填字段，提示文件与 `members[i]`。用同一输出路径再次冻结仍抛 `FileExistsError`，旧文件字节完整。可顺手补换路径或用原冻结批次恢复的提示，保留排他创建。[草案编译与冻结](../../../experiments/20261106-basepack/src/basepack/memory/draft.py)
- **原文与 JSON 编码。** 0.18.5 起，给显式 chunk 的 CRLF 原文填 LF 文本会在冻结时带源路径拒绝。直接 apply 现有冻结包仍只有成员 ID 和不匹配提示。建议补行尾或首差位置，优先提示省略 chunk `text`，继续精确核原文。有效草案加 UTF-8 BOM 仍解析失败，语法错误仍只有行列。建议在外部 JSON 读取处兼容 BOM、给解析异常附路径，文件哈希继续按原字节核验。[原文合同](../../../experiments/20261106-basepack/docs/memory.md#首建与维护) · [JSON 读取](../../../experiments/20261106-basepack/src/basepack/memory/query.py)
- **Condor 与检索预算。** 注入 Condor 探测超时，`doctor --facility condor` 仍退出 1、抛原始 `TimeoutExpired`。建议补命令、等待时间、实际 `CONDOR_CONFIG` 和检查方向，保留失败退出。`rank` 按分数降序逐项尝试，装不下即保留定位并继续，已有回归覆盖。建议只澄清使用说明。[Condor 诊断](../../../experiments/20261106-basepack/src/basepack/project/doctor.py) · [预算回归](../../../experiments/20261106-basepack/tests/test_memory_selection.py)

使用临时文件复现 freeze 和 rank。apply 校验使用隔离配置及模拟 SQL 读取，Condor 探测注入子进程超时，均覆盖两个版本。

## 下一步

0.14工程、本项目升级及用户后续授权的GitHub发行已完成，[本批结果](../../archive/20261114-next-maintenance/result.md)保留恢复、未知历史副本与分享边界；后续需求再沿相关任务接续。三工具独立分发沿[原收尾计划](../../archive/20261114-delivery-closeout/plan.md#四三工具沿既有独立分发方向接续)在各自项目接续；其中的已核状态带有观察日期，不能用迁移任务的历史“未推送”推断外部项目当前状态。

2026-11-13 已完成 AIGC、TTS 与 Codex 用量统计的独立打包、系统 Python 3.13 安装、现有资源归集及已知调用方切换。基础代码随各包，模型首次准备先确认目录；AgentTools 和 basePack 保持可选。中英文检测/统计对照、语音 CPU/GPU 与长文恢复、用量增量及 GUI、HTTP 并存和调度回收均有实际证据；人工听审未做。详见 [迁移结果](../../archive/20261113-agenttools-migration/result.md) 与 [专项记录](../../archive/20261113-agenttools-migration/progress.md)。

2026-11-19 核对用量统计跨项目整改已完成。启动器源留项目根，运行数据随脚本位置。CLI 报告默认随当前目录，缓存默认使用平台用户目录。正式性能复核后保留 v3 缓存格式。执行证据与后续入口见[归档结案记录](../../archive/20261115-codex-usage-launcher/progress.md#结案)。

已执行[实际使用整改计划](../../archive/20261112-usage-rectification/plan.md)，源码及本项目普通客户端为0.12.0.dev1，已交付检索入口、任务级brief、精确知识历史和纯访问状态；真实业务采用、安装与恢复见[验收结果](../../archive/20261112-usage-rectification/acceptance-result.md)。共享服务部署、外部项目修正及长期效果边界沿[整改进度](../../archive/20261112-usage-rectification/progress.md)接续。

已执行[接入、记忆维护与运行简化计划](../../archive/20261110-onboarding-simplification/plan.md)，0.8.0交付脚本增量维护、Codex聊天来源、接口清理、技能发现和英文README；随后按用户选择完成0.8.1保留认证与自动读取凭据。普通wheel369项通过、无跳过，共用客户端及三个项目入口已实际升级，七表逐字段、原凭据及数据库进程保持。新shell直接调用不再手工加载密码；实际覆盖与回退材料见[专项进度](../../archive/20261110-onboarding-simplification/progress.md)和[正式升级结果](../../archive/20261110-onboarding-simplification/credential-installation-result.md)。0.8.0免认证仅保留历史隔离证据，远端推送/发布未执行。

独立 [engineering-judgment skill](../../../skills/engineering-judgment/SKILL.md) 已编写、保留并接入，见[交付结果](../../archive/20261110-engineering-judgment/result.md)。按用户最新要求取消技能测试与按收益去留，效果在长期真实使用中观察；源码和入口已提交 f8bb5b2。

[basePack整改](../../archive/20261110-rectification/progress.md) 已完成故障修复、查询/维护解耦与 CPU/CUDA 适配的源码；随后按用户最新要求删除独立text模式，最终0.7.1普通wheel在Python3.14完整266项通过、无跳过，共用客户端与三个项目已完成向量配置迁移，七表逐字段未变；实际结果沿该进度维护。自动维护在业务期间按来源小批推进，业务结束停止；积压多只限制擅自启动独立手动深维护，不排除正常自动小批。正常浮点差异按等价处理。阵列业务事项仍留其项目。

用户已选择 MIT，[0.6.4 许可补丁](https://github.com/YS-Pan/basePack/releases/tag/v0.6.4) 已发布，GitHub 仓库识别为 MIT；源码、独立包许可证和元数据同步，定向构建/安装及附件下载校验通过，详见 [发布结果](github-publish-result.md#mit-许可补丁-064)。0.6.3 原标签和附件保留，项目记忆不上传。

首次上传 GitHub 已完成：源码推送至 [YS-Pan/basePack](https://github.com/YS-Pan/basePack)，[v0.6.3 开发版](https://github.com/YS-Pan/basePack/releases/tag/v0.6.3) 附普通 wheel 与校验和。源码 201 项回归、纯净安装、真实增量维护、新 shell、新聊天、远端 clone 使用闭环及附件下载校验通过，见 [发布结果](github-publish-result.md)。本项目记忆、数据库、配置、凭据与运行原证均未上传。完整空白 Windows/GPU/Condor 新机部署仍待独立机器验收；项目继续开发，实际使用兼作测试样本。

1. 记忆本轮实施与PPT实测反馈修复均已交付；后续沿 [记忆专项进度](../20261106-memory-system/progress.md) 按实际资料维护。三题业务小对照未见记忆质量优势，完整费用不可核，不宣称成本净收益。
2. 文件结构和分层协作在实际任务中继续验证；联合发布按 [总览 P8](plan.md#p8-联合交付与轻量发布) 执行。
