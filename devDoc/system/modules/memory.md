# 项目记忆实现

0.6.4 源码实现 SurrealDB 上的多层文字、原图向量与语义关系，首建和维护由宿主订阅 reader 同读完成。正式 wheel 与完整行为验收状态见 [专项进度](../../tasks/20261106-memory-system/progress.md)，P0 原生接入证据见 [结果](../../tasks/20261106-memory-system/p0-result.md)，用户流程见 [记忆说明](../../../experiments/20261106-basepack/docs/memory.md)。

## 职责与数据

- [content.py](../../../experiments/20261106-basepack/src/basepack/memory/content.py) 读取项目内 UTF-8 原字节版本与 1-based 闭区间，保留 CRLF；结构单元仅供备读，快/深变化检查不生成语义边界。
- [store.py](../../../experiments/20261106-basepack/src/basepack/memory/store.py) 通过原生 HTTP/SurrealQL 操作领域记录与事务；没有多后端层或自建 MCP。原生 CLI 负责服务与导出/恢复。
- `source_version` 保存文字原文快照与图片快照引用；图片原字节在 `memory.data_dir` 下的 assets 中。`member` 同时承载来源层级、智能块/摘要、范围及默认检索表示。`node` 表达实体/决定，`semantic` 使用有属性原生 relation；`change` 保存实际旧记录、时间及宿主可取得的执行信息。
- [images.py](../../../experiments/20261106-basepack/src/basepack/memory/images.py) 保留原图 hash 快照与定位；[vectors.py](../../../experiments/20261106-basepack/src/basepack/memory/vectors.py) 复用现有 EmbeddingClient 批量编码，查询使用原生 cosine 与排名融合，普通返回省略数值大数组。图文模型和服务沿 R9 共用。
- 原字节 revision 识别来源；input_revision 绑定实际编码输入（文字为 title 加 text，图片为原字节），description_revision 独立跟踪图片识读文字；knowledge_revision 用于逐记录乐观写入，embedding_identity 绑定模型语义空间。apply 核本批改写、退休、更正目标及实际使用的既有依据成员、关系两端的 expected；不核无关条目，保留无关并行。同批新建记录走不存在检查，不能省略已有依赖的版本。

## 已有行为

prepare 时包括本批所用依据与关系两端的材料，取得同读的新旧原文、当前与历史相关邻域及 expected 知识版本；邻域包含以所选成员为依据的 node→node 关系，并在 neighborhood.members 补齐相关成员端点与直接依据，关联原文仍需 read 或扩充 prepare 核实。agent 同次决定边界、摘要和有依据关系，apply 核来源与知识版本后原子接受；旧草稿冲突须重新 prepare、共读。程序按原范围取得 chunk，显式文字须逐字一致；更正的 previous 从实际旧记录取得。独立增边保留其它边。

变化检查与 apply 按原文范围、包含及摘要依据使受影响知识失效；真实失效同步刷新 knowledge_revision，文件增长也使全文摘要待核，未变叶块可复用。节点含义或依据改变时旧关联边待核，本批显式复核的边可恢复。接受删除保留旧快照与更正，不反复报告已处理删除。

当前 main 已修正退役成员隔离：退役表示不再触发当前原文失效、不作为父级传播桥，也不被未变兄弟重绑定改写历史版本；活跃但待核的表示仍参与真实依赖传播，显式复活继续核 expected。此修正尚未重建或安装，已发布0.6.4和本机0.6.2客户端仍有旧行为；[修复与原生回归](../../change_log/minor/20261110_145550_fix-retired-memory-invalidation.md)记录实际边界。

文字查询使用原生标题/正文全文，literal 显式调用原生包含匹配。read 仅接受 member ID，严格核对应版本原文；图像 read 返回独立的快照路径与原件缺失标记。原图缺失时可读保留快照，原图版本变化或快照缺失直接失败。neighbors 默认过滤 stale 的父子/语义展开，历史复核显式 include_stale。

记录 ID 的单一转换入口统一原始字符串 key 与底座返回的规范 ID，保留数字 key 的类型及字符串转义；同一身份同时用于 SQL 与 Python 的 expected/依据集合比较。有限解码只覆盖现行字符串/整数合同，底座仍通过原生 type::record 构造记录。缺少文字成员起止行时，apply 在写入前报出成员、批次位置及字段；不存在的 read 目标明确报错。输入方式与最小批次见用户流程及随包 skill。

brief 快检已登记原件及 source_scope：未变文件仅查元数据，已变材料才读原文定位失效，显式 deep 再哈希完整声明范围。它直接交付全部未退休 mandatory、相关线索及短项目地图；stale mandatory 仍交付但标待核。状态明细限量并带总数，sources 提供全量元数据供手动抽样。宿主按当前任务预算维护小批，程序不常驻派发语义 agent；已标待核条目不重复写同一失效日志。

向量绑定实际输入版本及 embedding_identity，写入前后核源版本；同维数不同身份或旧输入不参与当前查询。CLI 显式 --mode 优先，否则严格读取项目 memory.search_mode；新项目默认 text，已有项目升级时显式补项。hybrid 直接融合全部粒度，当前范围无兼容向量时明确提示 embed 或 text，空范围正常返回空。brief 的 vector_pending 由当前记录派生，报告未编码或输入过期；服务身份在实际查询时核对。原图编码与描述分开，只有描述改写时原图向量可复用。查询和历史快照省略派生向量大数组；恢复保留表示与图片快照后可重建，仍须核业务原件存在且版本一致。超限与超时保留共享服务原错，不截断、不重试、不停共享服务。

[selection.py](../../../experiments/20261106-basepack/src/basepack/memory/selection.py) 按真实 worker 分数排序，去重复身份/原文覆盖，按文字预算交付完整内容与省略入口；词法距离不冒充 agent 分数。已安装 [skill](../../../experiments/20261106-basepack/src/basepack/memory/SKILL.md) 驱动一次检索委托，宿主按 `config ai --purpose retrieval` 的结果派工（默认 tier1），没有模型 API 或后台 agent。

memory init 安装原生 schema 并绑定项目 UUID，同时在项目 instructions 加入 brief 与已安装 skill 入口；普通 init 不建库。新进程按生成入口从当前配置取得 password_env 和实际密码文件，再加载进程环境；memory.password_file 可选，省略时采用当前 memory_dir/password.txt 的公开约定。入口同时定位本项目 launcher、cwd 和日志；凭据内容不写入生成文本。数据库进程必须按项目独立物理目录启动，多聊天共用该进程。绑定核查防止误连另一项目；数据路径的实际归属仍须部署命令正确配置。
