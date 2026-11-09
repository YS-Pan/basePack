# 项目记忆实现

当前源码已实现 SurrealDB 上的多层文字、原图向量与语义关系；实际首建由宿主订阅 reader 完成。已安装的资源版 0.5.0 尚未包含本轮记忆代码，正式 wheel 与完整行为验收状态见 [专项进度](../../tasks/20261106-memory-system/progress.md)。P0 原生接入证据见 [结果](../../tasks/20261106-memory-system/p0-result.md)，用户流程见 [记忆说明](../../../experiments/20261106-basepack/docs/memory.md)。

## 职责与数据

- [content.py](../../../experiments/20261106-basepack/src/basepack/memory/content.py) 读取项目内 UTF-8 原字节版本与 1-based 闭区间，保留 CRLF；结构单元仅供备读，快/深变化检查不生成语义边界。
- [store.py](../../../experiments/20261106-basepack/src/basepack/memory/store.py) 通过原生 HTTP/SurrealQL 操作领域记录与事务；没有多后端层或自建 MCP。原生 CLI 负责服务与导出/恢复。
- `source_version` 保存原文快照；`member` 同时承载来源层级、智能块/摘要、范围及默认检索表示。`node` 表达实体/决定，`semantic` 使用有属性原生 relation；`change` 保存实际旧记录、时间及宿主可取得的执行信息。
- [images.py](../../../experiments/20261106-basepack/src/basepack/memory/images.py) 保留原图 hash 快照与定位；[vectors.py](../../../experiments/20261106-basepack/src/basepack/memory/vectors.py) 复用现有 EmbeddingClient 批量编码，查询使用原生 cosine 与排名融合，普通返回省略数值大数组。图文模型和服务沿 R9 共用。
- 原字节 revision 识别来源，input_revision 识别编码文字，knowledge_revision 用于逐记录乐观写入；embedding_identity 留作向量空间合同，四者互不替代。prepare 返回 expected，apply 只核本批改写目标，避免旧草稿覆盖新更正且允许无关成员并行。

## 已有行为

prepare 提供同读的新旧原文与邻域；agent 同次决定边界、摘要和有依据关系，apply 核来源与知识版本后原子接受。程序按原范围校验 chunk，不接受改写原词；更正的 previous 从实际旧记录取得。独立增边保留其它边。

变化检查与 apply 按原文范围、包含及摘要依据使受影响知识失效；文件增长也使全文摘要待核，未变叶块可复用。节点含义或依据改变时旧关联边待核，本批显式复核的边可恢复。接受删除保留旧快照与更正，不反复报告已处理删除。

文字查询使用原生标题/正文全文，literal 显式调用原生包含匹配。brief 返回必保留信息、线索与缺口，stale 只能作待核。read 严格核对应版本原文；neighbors 返回父子和语义连接供 worker 回源。

向量绑定实际输入版本及 embedding_identity，写入前后核源版本；同维数不同身份或旧输入不参与当前查询。默认 hybrid 直接融合全部粒度，缺兼容索引明确失败，text 模式仍可独立使用。原图向量与描述不同；恢复保留的文字/图片后可重新编码。超限与超时沿共享服务原错，不截断、不重试、不停共享服务。

[selection.py](../../../experiments/20261106-basepack/src/basepack/memory/selection.py) 按真实 worker 分数排序，去重复身份/原文覆盖，按文字预算交付完整内容与省略入口；词法距离不冒充 agent 分数。已安装 [skill](../../../experiments/20261106-basepack/src/basepack/memory/SKILL.md) 驱动一次检索委托，宿主负责实际派工，没有模型 API 或后台 agent。

memory init 安装原生 schema 并绑定项目 UUID，同时在项目 instructions 加入 brief 与已安装 skill 入口；普通 init 不建库。数据库进程必须按项目独立物理目录启动，多聊天共用该进程。绑定核查防止误连另一项目；数据路径的实际归属仍须部署命令正确配置。
