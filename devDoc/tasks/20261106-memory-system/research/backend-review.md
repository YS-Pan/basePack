# 记忆底座静态复核

2026 年 11 月 9 日，供 [P0](../plan.md#p0-收敛底座与数据合同) 选择试验入口。只读核对当前源码、官方文档、发布记录和固定版本源码；未安装候选、运行原型或操作共享服务。以下区分能力证据与待验取舍，最终选择仍须本机同样本验证。

## 当前事实与取舍

基线 main `5d72275` 只有公共接入与资源工具。[CLI](../../../../experiments/20261106-basepack/src/basepack/__main__.py) 无记忆动作；[init](../../../../experiments/20261106-basepack/src/basepack/project/init.py) 和 [配置测试](../../../../experiments/20261106-basepack/tests/test_config.py) 表明 memory 仅预留项目内路径，不创建数据库。资源 [R9](../../../archive/20261107-resource-coordination/r9-result.md) 已交付公开 HTTP 客户端与新向量身份，不能再把传输协议待定当作记忆选型前提。

静态优先顺序为 **SurrealDB 原生本地 MCP → 必要时 SQLite CLI + FTS5 + sqlite-vec**，P0 至多做两个小原型。理由是前者原生覆盖图、全文、外部向量与 MCP，有望减少胶水；后者组件少，可用作自维护 SQL 与服务代价的对照。这是工程推断，不是已证明 SurrealDB 更省代码或已选定产品底座。

| 已核版本 | 官方能力证据 | 尚需项目承担及本机核实 |
| --- | --- | --- |
| [SurrealDB 4.0.0](https://github.com/surrealdb/surrealdb/releases/tag/v4.0.0)，11 月 3 日发布 | Windows 发行、[原生 MCP](https://surrealdb.com/docs/build/ai-agents/mcp/embedded)、独立关系、全文、外部向量和导入/导出 | 来源/版本/定位、更正与条件、语义身份、变化清单仍需短 schema/SQL/skill；本地 server、中文、恢复和磁盘代价待验 |
| [SQLite 3.54.1](https://sqlite.org/changes.html)，10 月 16 日；[sqlite-vec 0.1.9](https://github.com/asg017/sqlite-vec/releases/tag/v0.1.9)，3 月 31 日 | Windows [CLI](https://sqlite.org/cli.html)、事务、FTS5、递归查询、备份；vec0 接收预计算向量 | 来源、图边语义、依据、更正、索引一致性及迁移均需维护 SQL/schema；CLI 加短 skill 即可，不为 MCP 另写服务 |
| [Basic Memory 1.0.0](https://github.com/basicmachines-co/basic-memory/releases/tag/v1.0.0)，10 月 29 日 | 原生 CLI/MCP、Markdown、观察/关系、搜索/上下文、文件同步及本地文本 embedding provider | 公开入口缺少预计算图文向量接入，与当前服务的协议/身份有差距，暂降为后备；不能直接继承旧项目的适配和验收 |

## 决策相关的能力边界

**SurrealDB。** 原生 MCP 支持 stdio embedded 或本地 server 的 `/mcp`；多聊天共享同一库应连接同一个本地 server，不能各起 embedded 进程打开同一路径。4.0 使用 SurrealKV，[平台支持](https://github.com/surrealdb/surrealkv#platform-support) 将 Windows 标为 Tier 2（构建、跳过原生测试）；有 Windows 包不能代替本机稳定性证据。[文件引擎](https://surrealdb.com/docs/running/file-backed) 与 [MCP 文档](https://surrealdb.com/docs/build/ai-agents/mcp/embedded) 是 P0 运行依据。

外部模型产生数字数组，由库原生 [保存与查询向量](https://surrealdb.com/docs/learn/data-models/vector-search/embedding-pipelines)；[关系边](https://surrealdb.com/docs/reference/query-language/statements/relate) 有独立记录及数据。它们可以承载项目合同，但不会自动生成来源定位、语义判断或审计。[逻辑备份](https://surrealdb.com/docs/manage/self-hosted/backups-and-recovery) 只导出当前记录；要恢复的修改依据必须显式保存，不能依赖引擎旧版本恰好仍在。

**SQLite。** [FTS5](https://sqlite.org/fts5.html#tokenizers) 的 unicode61 不提供中文词切分，trigram 的 MATCH 对不足三个 Unicode 字符无匹配；短词扫描等行为须在决定中说明代价。vec0 稳定版支持 2048 维预计算向量，但按穷举评估；[ANN 首发](https://github.com/asg017/sqlite-vec/releases/tag/v0.1.10-alpha.1) 属于预发布，不能把当前在线文档的新能力归给稳定版。多进程同机操作仍是单 writer，先使用短事务，冲突直接返回；[在线备份](https://sqlite.org/backup.html) 或 CLI `.backup` 可避免只复制活跃 WAL 数据库主文件的遗漏。[WAL 合同](https://sqlite.org/wal.html) 需随恢复样例核对。

**Basic Memory。** 文字闭环较完整，Markdown 本身不是降级理由。固定版本的 [provider 契约](https://github.com/basicmachines-co/basic-memory/blob/v1.0.0/src/basic_memory/repository/embedding_provider.py) 接收文本；[OpenAI provider](https://github.com/basicmachines-co/basic-memory/blob/v1.0.0/src/basic_memory/repository/openai_provider.py) 发送 model 与字符串 input，其身份没有任意外部权重修订/身份字段。[内部向量协议](https://github.com/basicmachines-co/basic-memory/blob/v1.0.0/src/basic_memory/repository/semantic_vector_index.py) 不是公开 CLI/MCP 扩展点。因此“可配置本地 OpenAI 兼容端点”不能推成“直接接任意 HTTP、多模态向量及 embedding_identity”。为它写私有 provider、内部表适配或第二向量库会增加维护面，当前缺少这样做更合算的证据。

1.0 的 [CLI 源码](https://github.com/basicmachines-co/basic-memory/blob/v1.0.0/src/basic_memory/cli/commands/tool.py) 使用 `bm tool read/write/search`，MCP 为 `bm_*`；部分在线说明保留旧命名，实施应按固定版本帮助核对。项目 scope 也不证明数据库物理位于项目内，须核 [配置目录](https://docs.basicmemory.com/reference/configuration) 和备份集合；中文能力同样以本项目样例判定。

## P0 如何消除未知

先用 SurrealDB 的正式发行与原生接口做最短往返，再根据具体失败决定是否跑 SQLite。除 [计划的数据与行为合同](../plan.md#最小行为与数据合同)，样例重点包含：

1. 中文单字、两字、长词、精确编号及中英混合；SurrealDB 的 [分析器](https://surrealdb.com/docs/reference/query-language/statements/define/analyzer) 与 SQLite 各方案都需实际测，不能只凭 Unicode/FTS 标签放行。
2. 少量预计算 2048 维文本/图片向量、身份不同的负例、原图/页定位；P0 核存取，真实本地图文语义留 P2，不切现有模型服务。
3. 原有节点上增改边而保留其它边、更正/失效与旧依据回查、恢复到另一目录；显式保存的修改记录也必须恢复。
4. 两个聊天连接同一项目的读写与冲突，以及另一个项目的实际隔离；数据物理位置仍属各项目，不能以服务器 namespace 代替归属核查。
5. 冷/热启动、批量维护、文件数和读写；小样例只筛明显代价，代表性语料及真实 HDD 验收留 P4。

按实际新增代码、SQL/skill/配置、额外进程和运行维护共同选唯一底座。若两条路线均存在目标级缺口，保留失败及代价后再定替代方案，不增加第三套长期实现。官方资料只支持上述静态能力，Windows、并发、中文召回、HDD 与净收益目前都没有本机记忆验收证据。
