# SurrealDB 首期适用性复核

2026 年 11 月 9 日更新。按用户当前决定，**首期只使用 SurrealDB**；[P0](../plan.md) 验证其能否承载记忆合同，验证后推进同一实现。此前三者调查保留为历史依据，不安排备选安装、适配或并行原型。出现真实阻碍时，报告具体冲突、证据与影响，再评估替代。

本页保留实施前的官方文档、发布记录和固定版本源码复核；其后已完成 [P0 本机原生接入](../p0-result.md)，下面能力差距与检查项按静态调查时点理解。实际状态见 [进度](../progress.md)，目标以 [项目纲领](../../../project-charter.md#记忆系统) 为准。

## 当前范围与职责

全文、本地图文向量、语义图和多层次表示均保留。文件、章节、段落分别成为可寻址检索成员；原文块向量与章节/文件摘要向量共同参与检索，结构包含、摘要来源和跨材料语义关系分别表达。检索要融合候选、处理父子内容重叠，并回到对应版本的原文或图片；具体合同只在 [实施计划](../plan.md) 维护，机制依据见 [多层调研](multilevel-retrieval.md)。

宿主订阅 agent 在同次阅读中确定智能分块边界，产出摘要、节点和边；软件保存边界、定位及依据，并调用共享 embedding 服务。SurrealDB 负责持久化、事务、索引和查询，不自动理解分块或生成摘要、语义边。本路线不引入新的 LLM API，也不把分块另建成先于语义阅读的全量流程。

资源 [R9](../../../archive/20261107-resource-coordination/r9-result.md) 已交付公开 HTTP 客户端与向量语义身份；接入复用该成果，P0 以少量预计算向量核存取，真实本地图文语义留 P2。项目知识及数据库留在对应项目内，软件、依赖与模型按现行部署合同显式共用。

## SurrealDB 的能力证据与项目差距

| 已核能力 | 对本项目的适用边界 |
| --- | --- |
| [4.0.0 正式版](https://github.com/surrealdb/surrealdb/releases/tag/v4.0.0)，2026-11-03 发布；[Windows 安装](https://surrealdb.com/docs/running/installation/windows) 后可离线运行 | 固定版本、持久路径与新目录启动仍需 P0 实测。SurrealKV 的 [Windows 平台等级](https://github.com/surrealdb/surrealkv#platform-support) 为 Tier 2：有构建，原生测试跳过；发行包不是本机稳定性证据。 |
| 原生 [CLI/MCP](https://surrealdb.com/docs/build/ai-agents/mcp/embedded) 提供查询与记录/关系操作，支持 stdio embedded 或本地 server 的 `/mcp` | 同项目多聊天连接一个本地 server，数据库物理目录属于该项目；各聊天另开 embedded 进程访问同一路径不能作为并发方案。P0 计入实例启动、路径、端口与进程管理成本，不自写数据库 MCP。 |
| [外部向量](https://surrealdb.com/docs/learn/data-models/vector-search/embedding-pipelines)、[独立关系边](https://surrealdb.com/docs/reference/query-language/statements/relate) 与图遍历 | 原文、摘要和图片向量可由外部生成后保存。成员身份、层级、原文范围、来源版本、embedding_identity、边的条件/依据与修改记录仍需短 schema/SQL/skill；原生图能力不等于已完成语义建图。 |
| 全文、[排名融合](https://surrealdb.com/docs/learn/data-models/vector-search/hybrid-search) 与精确/近似向量检索 | 原生融合不自动完成跨层候选配额、父子覆盖去重或摘要回源。中文单字/两字/长词及中英混合须用实际样例核 [分析器](https://surrealdb.com/docs/reference/query-language/statements/define/analyzer)；不能只凭 Unicode/FTS 标签放行。近似索引按实际规模需要采用。 |
| [事务内事件](https://surrealdb.com/docs/learn/schema-management/events-and-triggers/defining-events) 可处理记录变化，访问变更前后值 | 事件只执行显式规则，导入不触发。原件变化检测、受影响祖先摘要与语义边的依赖、待维护状态和检索过滤仍须项目定义；摘要重写与边复核由 agent 完成。优先用同一批量维护事务复用这些能力。 |
| [逻辑导出/恢复](https://surrealdb.com/docs/manage/self-hosted/backups-and-recovery) 与 [文件引擎](https://surrealdb.com/docs/running/file-backed) | 导出只有当前记录；修改依据与历史必须显式保存，不能依赖引擎旧版本恰好仍在。直接复制数据库目录须先关闭使用者；原件、派生图片及数据库的备份集合另须明确。SurrealKV 的 LSM/压实有额外 I/O，冷/热启动、批量读写及 HDD 代价待验。 |

## P0 要取得的适用性证据

P0 围绕 SurrealDB 跑最小完整资料集，复用原生 CLI/MCP 和查询能力，仅补实际缺口。样例与完成条件以计划为准，关键未知为：

1. 新目录安装、持久化重启、离线查询与两个项目隔离；同项目两个聊天通过一个本地 server 读写，冲突和失败能定位。
2. 中文、编号与中英混合检索返回正确来源；少量预计算 2048 维文本/图片向量、身份不同的负例及原图/页定位得到正确结果，不切换现有模型服务。
3. 同一长文件的文件/章节/段落身份、智能边界及原文范围，章节/文件摘要与各层向量能共同检索；父子展开、摘要回源和重叠去重不丢必要证据。分块、摘要和图关系同次阅读的实际行为依计划验收。
4. 原有节点增改边时保留其它边；局部来源变化使相关祖先摘要及依赖旧依据的边退出当前结论，维护后恢复正确检索，未变兄弟可复用；旧依据与人工更正仍可回查。
5. 备份恢复到另一目录后，成员身份、层级、原文定位、显式修改记录、摘要与边的依据仍对应。记录数据库、原件及派生内容的实际备份/恢复流程。
6. 记录新增代码、SQL/skill/配置、额外进程、文件数及冷/热读写。小样例筛明显代价，代表性规模和真实 HDD 验收留 P4；安装成功或节点数量不替代功能验收。

这些检查决定当前实现如何收敛，不用于预排三套原型。本机 P0 接入证据现已取得，真实语义与完整记忆行为仍按专项逐阶段验收。若出现无法满足目标的真实阻碍，先报告复现条件和必要代价，再讨论基座。

## 历史比较依据

以下是本次收敛前的静态调查，保留用于解释已有判断及必要时复核，不是当前执行路线。

| 历史路线与版本 | 仍有价值的调查结论 |
| --- | --- |
| [SQLite 3.54.1](https://sqlite.org/changes.html)（2026-10-16）加 [sqlite-vec 0.1.9](https://github.com/asg017/sqlite-vec/releases/tag/v0.1.9)（2026-03-31） | [CLI](https://sqlite.org/cli.html) 与短 skill 可直接使用；[递归图查询](https://sqlite.org/lang_with.html#queries_against_a_graph) 可处理邻域与层级，无须另造图执行器。稳定 vec0 可存 2048 维预计算向量，按穷举评估；[ANN 首发](https://github.com/asg017/sqlite-vec/releases/tag/v0.1.10-alpha.1) 属预发布。来源、关系语义、多层表示、融合与失效规则均需自维护 SQL/schema。 |
| [Basic Memory 1.0.0](https://github.com/basicmachines-co/basic-memory/releases/tag/v1.0.0)（2026-10-29） | 已有 [笔记/观察/关系、读取/搜索/上下文与局部编辑](https://docs.basicmemory.com/reference/mcp-tools-reference)、文件同步及文本向量索引，可省应用代码；Markdown 本身不是排除理由。[配置](https://docs.basicmemory.com/reference/configuration) 公开支持 `BASIC_MEMORY_CONFIG_DIR` 将配置及默认数据库放入项目内。完整目标的接入代价与文件 I/O 先前均未实测。 |

SQLite 的 [FTS5](https://sqlite.org/fts5.html#tokenizers) 不提供默认中文词切分，trigram 的 MATCH 对不足三个 Unicode 字符无匹配；[WAL](https://sqlite.org/wal.html) 同机多进程仍是单 writer，活跃库应使用 [在线备份](https://sqlite.org/backup.html) 或 CLI `.backup`，不能只复制主文件。这些是历史边界，不构成当前实施任务。

Basic Memory 的公开 metadata 和关系 context 能表达来源、范围及依据，编辑关系行后由上游更新图；并非必须私有改库。但没有独立 edge UUID/CRUD，[context 输出](https://github.com/basicmachines-co/basic-memory/blob/v1.0.0/src/basic_memory/mcp/tools/context.py) 也不交付关系 context。[搜索](https://github.com/basicmachines-co/basic-memory/blob/v1.0.0/src/basic_memory/mcp/tools/ranked_search.py) 面向 notes/observations/relations，章节读取不是独立章节搜索；[原生分块](https://github.com/basicmachines-co/basic-memory/blob/v1.0.0/src/basic_memory/repository/semantic_chunking.py) 与 [章节投影](https://github.com/basicmachines-co/basic-memory/blob/v1.0.0/src/basic_memory/repository/note_section_repository.py) 不等于稳定章节/段落成员。独立 note 建模能复用公开功能，文件量仍有代价；工具名称可回查 [v1 CLI 源码](https://github.com/basicmachines-co/basic-memory/blob/v1.0.0/src/basic_memory/cli/commands/tool.py)。

其 [provider 协议](https://github.com/basicmachines-co/basic-memory/blob/v1.0.0/src/basic_memory/repository/embedding_provider.py) 有可选 `identity_key()`；限制在现成 [OpenAI provider](https://github.com/basicmachines-co/basic-memory/blob/v1.0.0/src/basic_memory/repository/openai_provider.py) 与 [配置工厂](https://github.com/basicmachines-co/basic-memory/blob/v1.0.0/src/basic_memory/repository/embedding_provider_factory.py)，不能说整个应用无法保存自定义身份。公开 OpenAI 兼容端点加 HTTP 适配可能接入现有文本服务；model alias 映射完整语义身份仍是未运行推断，[内部向量协议](https://github.com/basicmachines-co/basic-memory/blob/v1.0.0/src/basic_memory/repository/semantic_vector_index.py) 不是公开预计算图文向量入口。[语义搜索](https://docs.basicmemory.com/concepts/semantic-search) 自动建向量且关闭开关已移除，不能假设纯文字索引无需 embedding。这些历史接法均未实施。
