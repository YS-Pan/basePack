# 记忆底座静态复核

2026 年 11 月 9 日，供 [P0](../plan.md#p0-收敛底座与数据合同) 选择试验入口。只读核对当前源码、官方文档、发布记录和固定版本源码；未安装候选、运行原型或操作共享服务。以下区分能力证据与待验取舍，最终选择仍须本机同样本验证。

## 当前事实与取舍

基线 main `5d72275` 只有公共接入与资源工具。[CLI](../../../../experiments/20261106-basepack/src/basepack/__main__.py) 无记忆动作；[init](../../../../experiments/20261106-basepack/src/basepack/project/init.py) 和 [配置测试](../../../../experiments/20261106-basepack/tests/test_config.py) 表明 memory 仅预留项目内路径，不创建数据库。资源 [R9](../../../archive/20261107-resource-coordination/r9-result.md) 已交付公开 HTTP 客户端与新向量身份，不能再把传输协议待定当作记忆选型前提。

按用户本次要求，**Basic Memory、SQLite CLI + FTS5 + sqlite-vec、SurrealDB 原生本地 MCP 均为正式候选**，替代上一轮先 SurrealDB、SQLite 对照、Basic Memory 后备的顺序。Basic Memory 复用记忆应用，SQLite 提供部署简洁基线，SurrealDB 集中数据库能力；按同一完整工作流比较总维护量，当前不预设赢家。原生 MCP 和单一 embedding 接口差异都不足以单独决定取舍。

| 已核版本 | 官方能力证据 | 尚需项目承担及本机核实 |
| --- | --- | --- |
| [SurrealDB 4.0.0](https://github.com/surrealdb/surrealdb/releases/tag/v4.0.0)，11 月 3 日发布 | Windows 发行、[原生 MCP](https://surrealdb.com/docs/build/ai-agents/mcp/embedded)、独立关系、全文、外部向量和导入/导出 | 来源/版本/定位、更正与条件、语义身份、变化清单仍需短 schema/SQL/skill；本地 server、中文、恢复和磁盘代价待验 |
| [SQLite 3.54.1](https://sqlite.org/changes.html)，10 月 16 日；[sqlite-vec 0.1.9](https://github.com/asg017/sqlite-vec/releases/tag/v0.1.9)，3 月 31 日 | Windows [CLI](https://sqlite.org/cli.html)、事务、FTS5、递归查询、备份；vec0 接收预计算向量 | 来源、图边语义、依据、更正、索引一致性及迁移均需维护 SQL/schema；CLI 加短 skill 即可，不为 MCP 另写服务 |
| [Basic Memory 1.0.0](https://github.com/basicmachines-co/basic-memory/releases/tag/v1.0.0)，10 月 29 日 | 原生 CLI/MCP、Markdown、观察/关系、搜索/上下文、文件同步及本地文本 embedding provider | 正式应用复用候选；公开图文向量接入、关系依据/更正表达、项目局部配置和 HDD 成本需核，不直接继承旧项目适配与验收 |

## 按记忆工作流比较

| 比较项 | Basic Memory | SQLite 方案 | SurrealDB |
| --- | --- | --- | --- |
| 交付层次 | 已有记忆应用，可复用笔记、观察、关系和工具流程 | 数据库与扩展，应用规则由本项目实现 | 多模型数据库，应用规则由本项目实现 |
| 来源与变化 | 笔记、定位、校验和、文件同步已有入口；外部业务原件的版本依据仍需接入 | 来源表/定位/变化检测需定义，复用原生事务与索引 | 来源记录/定位/变化检测需定义，复用原生事务与索引 |
| 关系与上下文 | 已有带类型的笔记链接、关系 context 和上下文工具；关系修改走笔记编辑，复杂条件/更正与多依据需验 | 边表与递归 SQL 可做图查询，简单邻域无需另造图执行器 | 原生关系边和遍历更直接，语义规则仍需定义 |
| 存储与部署 | Markdown 加应用数据库，文件同步和恢复集合需核 | 项目内数据库、CLI，无数据库服务；向量扩展单独管理 | 项目内存储；同项目多聊天连接一个本地 server，计入实例管理 |
| 图文向量 | 现成文本 provider 与当前服务存在接入缺口，需核最薄接法 | 扩展可存外部向量，身份和原图定位由集成保存 | 可存外部向量，原生近似索引可按规模使用；身份和原图定位由集成保存 |
| 应比较的成本 | 少写应用代码能否抵消接入适配、文件 I/O 和上游约束 | 少组件能否抵消自维护 schema/SQL/同步和查询流程 | 原生图/向量/MCP 能否抵消额外进程、配置及升级维护 |

Basic Memory 的现成功能见 [观察与关系](https://docs.basicmemory.com/concepts/observations-and-relations)、[工具合同](https://docs.basicmemory.com/reference/mcp-tools-reference)；SQLite 原生 [递归图查询](https://sqlite.org/lang_with.html#queries_against_a_graph) 说明“无专门图数据库”不等于需要自写图执行器。三者都需要宿主 agent 共读建图、启动交付和实际评分；Basic Memory 的上下文工具不自动证明这些行为已按本项目要求执行。

## 决策相关的能力边界

**SurrealDB。** 原生 MCP 支持 stdio embedded 或本地 server 的 `/mcp`；多聊天共享同一库应连接同一个本地 server，不能各起 embedded 进程打开同一路径。4.0 使用 SurrealKV，[平台支持](https://github.com/surrealdb/surrealkv#platform-support) 将 Windows 标为 Tier 2（构建、跳过原生测试）；有 Windows 包不能代替本机稳定性证据。[文件引擎](https://surrealdb.com/docs/running/file-backed) 与 [MCP 文档](https://surrealdb.com/docs/build/ai-agents/mcp/embedded) 是 P0 运行依据。

外部模型产生数字数组，由库原生 [保存与查询向量](https://surrealdb.com/docs/learn/data-models/vector-search/embedding-pipelines)；[关系边](https://surrealdb.com/docs/reference/query-language/statements/relate) 有独立记录及数据。它们可以承载项目合同，但不会自动生成来源定位、语义判断或审计。[逻辑备份](https://surrealdb.com/docs/manage/self-hosted/backups-and-recovery) 只导出当前记录；要恢复的修改依据必须显式保存，不能依赖引擎旧版本恰好仍在。

**SQLite。** [FTS5](https://sqlite.org/fts5.html#tokenizers) 的 unicode61 不提供中文词切分，trigram 的 MATCH 对不足三个 Unicode 字符无匹配；短词扫描等行为须在决定中说明代价。vec0 稳定版支持 2048 维预计算向量，但按穷举评估；[ANN 首发](https://github.com/asg017/sqlite-vec/releases/tag/v0.1.10-alpha.1) 属于预发布，不能把当前在线文档的新能力归给稳定版。多进程同机操作仍是单 writer，先使用短事务，冲突直接返回；[在线备份](https://sqlite.org/backup.html) 或 CLI `.backup` 可避免只复制活跃 WAL 数据库主文件的遗漏。[WAL 合同](https://sqlite.org/wal.html) 需随恢复样例核对。

**Basic Memory。** 文字闭环较完整，Markdown 本身不是排除理由。固定版本的 [provider 契约](https://github.com/basicmachines-co/basic-memory/blob/v1.0.0/src/basic_memory/repository/embedding_provider.py) 接收文本，也有可选的 `identity_key()` 身份能力；不能笼统说整个软件无法表达自定义身份。现成 [OpenAI provider](https://github.com/basicmachines-co/basic-memory/blob/v1.0.0/src/basic_memory/repository/openai_provider.py) 发送 model 与字符串 input，默认身份没有当前共享服务的权重/预处理身份；[配置工厂](https://github.com/basicmachines-co/basic-memory/blob/v1.0.0/src/basic_memory/repository/embedding_provider_factory.py) 只提供内置 provider，不能把协议存在推成已有公开插件注册配置。[内部向量协议](https://github.com/basicmachines-co/basic-memory/blob/v1.0.0/src/basic_memory/repository/semantic_vector_index.py) 也不等于公开 CLI/MCP 的预计算图文向量入口。

文本可能通过公开 OpenAI 兼容端点加薄 HTTP 适配接现有 `/predict`，不一定改 Basic Memory 源码；将完整 embedding_identity 映射为不可复用的 model alias，也可能利用现成身份失效机制触发重建。这些是源码支持的集成推断，尚未运行，不能据此宣称图片向量已接通。P0 要核实际适配范围，把代码、升级耦合与它省下的应用代码共同计算；公开原始图片向量入口仍有缺口。优先公开扩展，私有补丁或第二知识维护源的真实代价必须写明，不因文字成功放弃完整图文目标。

[关系格式](https://github.com/basicmachines-co/basic-memory/blob/v1.0.0/src/basic_memory/markdown/schemas.py) 可保存 context，`bm_edit` 编辑关系行后由上游同步图，不能说依据或修改必须私有改库。它没有独立 edge UUID/CRUD，且 [bm_context](https://github.com/basicmachines-co/basic-memory/blob/v1.0.0/src/basic_memory/mcp/tools/context.py) 不交付关系 context，追证仍需读所属笔记。P0 以原生关系或独立断言笔记表达条件/多依据，核稳定定位与更正；额外笔记带来的文件量计入 HDD 成本，不先锁成自有边表。

1.0 的 [CLI 源码](https://github.com/basicmachines-co/basic-memory/blob/v1.0.0/src/basic_memory/cli/commands/tool.py) 使用 `bm tool read/write/search`，MCP 为 `bm_*`；部分在线说明保留旧命名，实施应按固定版本帮助核对。[配置合同](https://docs.basicmemory.com/reference/configuration) 已公开支持 `BASIC_MEMORY_CONFIG_DIR` 隔离配置和默认应用数据库，`BASIC_MEMORY_MCP_PROJECT` 约束会话项目；可用它们规划项目内实例，本机移动/隔离/恢复仍需实测。

[语义搜索说明](https://docs.basicmemory.com/concepts/semantic-search) 与 [v1 依赖](https://github.com/basicmachines-co/basic-memory/blob/v1.0.0/pyproject.toml) 明确自动生成文本向量，FastEmbed/sqlite-vec 为核心依赖，旧 `semantic_search_enabled` 开关已移除。不能假设 Basic Memory 能纯文字启动且完全不接 embedding：P0 需先核模型/provider 和自动索引行为，避免试验时意外下载模型或另起一份共享模型。其可选本地/API reranker 也不替代本项目要求的订阅 agent 给分。

## P0 如何消除未知

先固定同一资料集与完整目标，核 Basic Memory 的现成记忆流程及公开 embedding 接法、SQLite 的必要 SQL、SurrealDB 的原生查询与实例代价，再按不确定性选择最短原型。比较可分批，最终只保留一套产品接入，不为三者各建完整应用。除 [计划的数据与行为合同](../plan.md#最小行为与数据合同)，样例重点包含：

1. 中文单字、两字、长词、精确编号及中英混合；SurrealDB 的 [分析器](https://surrealdb.com/docs/reference/query-language/statements/define/analyzer) 与 SQLite 各方案都需实际测，不能只凭 Unicode/FTS 标签放行。
2. 少量预计算 2048 维文本/图片向量、身份不同的负例、原图/页定位；P0 核存取，真实本地图文语义留 P2，不切现有模型服务。
3. 原有节点上增改边而保留其它边、更正/失效与旧依据回查、恢复到另一目录；显式保存的修改记录也必须恢复。
4. 两个聊天连接同一项目的读写与冲突，以及另一个项目的实际隔离；数据物理位置仍属各项目，不能以服务器 namespace 代替归属核查。
5. 冷/热启动、批量维护、文件数和读写；小样例只筛明显代价，代表性语料及真实 HDD 验收留 P4。

按实际新增代码、SQL/skill/配置、额外进程和运行维护共同选唯一底座；原型数量按消除差异的需要调整，不沿用“最多两条”排除本次新增候选。关键能力缺口未解决时保留失败与代价后调整方案，不用 P1 文字成功替代完整范围判断。官方资料只支持上述静态能力，Windows、并发、中文召回、HDD 与净收益目前都没有本机记忆验收证据。
