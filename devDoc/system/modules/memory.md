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

变化检查只发现待维护来源，不改已发布状态。apply 核版本并发布本批变更；未被本批替换的内容保留其实际依据快照，显式退役、更正及受影响关系按状态处理。接受删除保留旧快照与更正，不反复报告已处理删除。

当前 main 已修正退役成员隔离：退役表示不再触发当前原文失效、不作为父级传播桥，也不被未变兄弟重绑定改写历史版本；活跃但待核的表示仍参与真实依赖传播，显式复活继续核 expected。此修正尚未重建或安装，已发布0.6.4和本机0.6.2客户端仍有旧行为；[修复与原生回归](../../change_log/minor/20261110_145550_fix-retired-memory-invalidation.md)记录实际边界。

文字查询使用原生标题/正文全文，literal 显式调用原生包含匹配。read 以 member ID 和可选的依据版本、位置回读保留的原文或原图快照；快照缺失或损坏直接失败。neighbors 默认过滤 stale 的父子/语义展开，历史复核显式 include_stale。

记录 ID 的单一转换入口统一原始字符串 key 与底座返回的规范 ID，保留数字 key 的类型及字符串转义；同一身份同时用于 SQL 与 Python 的 expected/依据集合比较。有限解码只覆盖现行字符串/整数合同，底座仍通过原生 type::record 构造记录。缺少文字成员起止行时，apply 在写入前报出成员、批次位置及字段；不存在的 read 目标明确报错。输入方式与最小批次见用户流程及随包 skill。

brief、search 和 read 只读取已发布状态及其依据版本，不扫描原件或触发维护。brief 交付 mandatory、项目地图与按配置模式检索的相关线索；stale mandatory 仍交付并标待核。changes 由维护显式调用，发现来源变化不改已发布记录，避免旧检查覆盖新接受态。

向量绑定实际输入版本及 embedding_identity；默认 vector，text/hybrid 可显式选择。search 和 brief 的相关通道报告已发布范围内相同 identity 的兼容与待建数量；缺少兼容向量时明确报错，真实空范围与空命中保持可辨。旧 text 库通过 embed 补建后切换 vector；CPU/CUDA 的相同语义 identity 共用向量。纯 text 发布无需编码；vector/hybrid 模式先准备候选向量，并在同一短事务发布内容和匹配向量。输入版本与 identity 未变化的向量可复用。

宿主提供开始/完成事件与可取消子任务时，可独立启动低优先级小批维护。`apply --control` 和 `stop --control` 使用任务独有控制文件同步仲裁：停止先到则不提交，已获得提交资格的事务完成或回滚；停止失败保留错误且仍取消 worker。控制不终止共享服务或已开始的共享推理，迟到结果不被采用。缺少宿主能力时不可宣称自动生命周期已启用。

[selection.py](../../../experiments/20261106-basepack/src/basepack/memory/selection.py) 按真实 worker 分数排序，去重复身份/原文覆盖，按文字预算交付完整内容与省略入口；词法距离不冒充 agent 分数。已安装 [skill](../../../experiments/20261106-basepack/src/basepack/memory/SKILL.md) 驱动一次检索委托，宿主按 `config ai --purpose retrieval` 的结果派工（默认 tier1），没有模型 API 或后台 agent。

memory init 安装原生 schema 并绑定项目 UUID，同时在项目 instructions 加入 brief 与已安装 skill 入口；普通 init 不建库。新进程按生成入口从当前配置取得 password_env 和实际密码文件，再加载进程环境；memory.password_file 可选，省略时采用当前 memory_dir/password.txt 的公开约定。入口同时定位本项目 launcher、cwd 和日志；凭据内容不写入生成文本。数据库进程必须按项目独立物理目录启动，多聊天共用该进程。绑定核查防止误连另一项目；数据路径的实际归属仍须部署命令正确配置。
