# 项目记忆实现

源码面向 0.9.0，实现 SurrealDB 上的多层文字、原图向量与语义关系，以及默认全项目维护和随包英文维护提示词。首建和维护由宿主订阅 agent 同读完成。正式 wheel 与完整行为验收状态见 [专项进度](../../tasks/20261106-memory-system/progress.md)，P0 原生接入证据见 [结果](../../tasks/20261106-memory-system/p0-result.md)，用户流程见 [记忆说明](../../../experiments/20261106-basepack/docs/memory.md)。

## 职责与数据

认证在客户端构造边界统一完成：CLI/Python 共用 ProjectConfig 解析的 username 与 memory_password_file，以 UTF-8 解码文件（兼容 BOM，保留 CRLF/首尾空白）并发送 Basic Authorization；默认文件为实际 memory_dir/password.txt。config show 不读 secret，guide/rank/stop 与 prompt 不创建数据库客户端。password_env 手工桥退出；缺文件、权限或错密保留原错，不生成替代密钥或免认证回退。新库凭据由首次部署显式准备，launcher 读取同一文件；已有库和凭据随普通升级保留。

- [content.py](../../../experiments/20261106-basepack/src/basepack/memory/content.py) 读取项目内 UTF-8 原字节版本与 1-based 闭区间，保留 CRLF；结构单元仅供备读，快/深变化检查不生成语义边界。
- [store.py](../../../experiments/20261106-basepack/src/basepack/memory/store.py) 通过原生 HTTP/SurrealQL 操作领域记录与事务；没有多后端层或自建 MCP。原生 CLI 负责服务与导出/恢复。
- `source_version` 保存文字原文快照与图片快照引用；图片原字节在 `memory.data_dir` 下的 assets 中。`member` 同时承载来源层级、智能块/摘要、范围及默认检索表示。`node` 表达实体/决定，`semantic` 使用有属性原生 relation；`change` 保存实际旧记录、时间及宿主可取得的执行信息。
- [images.py](../../../experiments/20261106-basepack/src/basepack/memory/images.py) 保留原图 hash 快照与定位；[vectors.py](../../../experiments/20261106-basepack/src/basepack/memory/vectors.py) 复用现有 EmbeddingClient 批量编码，查询使用原生 cosine 与排名融合，普通返回省略数值大数组。图文模型和服务沿 R9 共用。
- 原字节 revision 识别来源；input_revision 绑定实际编码输入（文字为 title 加 text，图片为原字节），description_revision 独立跟踪图片识读文字；knowledge_revision 用于逐记录乐观写入，embedding_identity 绑定模型语义空间。apply 核本批改写、退休、更正目标及实际使用的既有依据成员、关系两端的 expected；不核无关条目，保留无关并行。同批新建记录走不存在检查，不能省略已有依赖的版本。

## 已有行为

prepare 时包括本批所用依据与关系两端的材料，取得同读的新旧原文、当前与历史相关邻域及 expected 知识版本；邻域包含以所选成员为依据的 node→node 关系，并在 neighborhood.members 补齐相关成员端点与直接依据，关联原文仍需 read 或扩充 prepare 核实。agent 同次决定边界、摘要和有依据关系，apply 核来源与知识版本后原子接受；旧草稿冲突须重新 prepare、共读。程序按原范围取得 chunk，显式文字须逐字一致；更正的 previous 从实际旧记录取得。独立增边保留其它边。

变化检查只发现待维护来源，不改已发布状态。apply 核版本并发布本批变更；未被本批替换的内容保留其实际依据快照，显式退役、更正及受影响关系按状态处理。接受删除保留旧快照与更正，不反复报告已处理删除。

退役成员不再触发当前原文失效、不作为父级传播桥，也不被未变兄弟重绑定改写历史版本；活跃但待核的表示仍参与真实依赖传播，显式复活继续核 expected。修复来源与当时的原生回归见[记录](../../change_log/minor/20261110_145550_fix-retired-memory-invalidation.md)，当前安装状态沿专项进度核实。

vector/hybrid 的 Python 与 CLI 检索统一返回 `matches` 和 `vector_coverage`；hybrid 的文字通道使用原生标题/正文全文，literal 对 path/title/text 做大小写无关的包含匹配，并使直接命中排在语义补充前；返回的 lexical_rank 标识直接命中。literal 只用于 hybrid，vector 下明确报错。read 以 member ID 和可选的依据版本、位置回读保留的原文或原图快照；核语义关系时必须沿 basis 的 source_version 与文字范围或图片 locator 回读 original，stable ID 的当前 member 不能替换已保存的旧依据。快照缺失或损坏直接失败。neighbors 默认过滤 stale 的父子/语义展开，历史复核显式 include_stale。

记录 ID 的单一转换入口统一原始字符串 key 与底座返回的规范 ID，保留数字 key 的类型及字符串转义；同一身份同时用于 SQL 与 Python 的 expected/依据集合比较。有限解码只覆盖现行字符串/整数合同，底座仍通过原生 type::record 构造记录。缺少文字成员起止行时，apply 在写入前报出成员、批次位置及字段；不存在的 read 目标明确报错。输入方式与最小批次见用户流程及随包 skill。

brief、search 和 read 只读取已发布状态及其依据版本，不扫描原件或触发维护。brief 交付 mandatory、项目地图与按配置模式检索的相关线索；stale mandatory 仍交付并标待核。changes 由维护显式调用，发现来源变化不改已发布记录，避免旧检查覆盖新接受态。

向量绑定实际输入版本及 embedding_identity；仅支持 vector/hybrid，默认 vector。search 和 brief 的相关通道报告已发布范围内相同 identity 的兼容与待建数量；缺少兼容向量时明确报错，真实空范围与空命中保持可辨。旧 text 配置须先改为 vector 或 hybrid，再 embed 补建索引；CPU/CUDA 的相同语义 identity 共用向量。apply 先准备候选向量，并在同一短事务发布内容和匹配向量；模型失败保留原错误并停止本批，不发布无匹配向量的内容。输入版本与 identity 未变化的向量可复用。

`memory maintain` 默认以项目 Git 清单（已跟踪与未忽略的未跟踪文件）加 source_scope 显式包含项发现原件；非 Git 项目使用声明范围。已登记来源、历史 pending/未接受范围与可归属 Codex 原件持续参与，`--scope` 只覆盖新文件发现。完整回执保存深比较与机械等价证据；短结果报告 discovery 边界/缺口、receipt、control 及 worker 派工元数据。历史 stale 不能仅因最后一次事件为 detected_change 就恢复；枚举与机械更新不证明完整语义覆盖。

`memory prompt --receipt <receipt> --control <control>` 只读项目配置、随包英文模板和回执，返回 prompt、角色、档位、实际模型映射及可重复运行的 render_command；不读取凭据、不连库或模型、不写控制与状态。默认 coordinator/tier2，`--role reader --paths ...` 默认 reader/tier1；显式 `--tier` 仅改模型档位。宿主先把返回的模型/推理强度设到派工接口，再给子 agent 一条英文启动句及命令，由其执行并遵循 prompt；角色详细逻辑在模板单一维护。

宿主提供开始/完成事件与可取消子任务时，异步启动默认维护，业务不等待。协调者持续拥有下一批、reader 与统一发布的责任，直到业务停止、候选耗尽或实际阻碍；单个 reader 或批次完成不结束分支。所有 apply 复用任务 control，采用回执聊天截点；下一轮再处理当前聊天追加内容。`apply --control` 和 `stop --control` 同步仲裁：停止先到则不提交，stop 不等待已获准提交的事务；业务完成后宿主取消协调者及全部后代。停止失败保留原错且仍取消 agent。控制不终止共享服务或已开始的共享推理。缺少宿主能力时不可宣称自动生命周期已启用；旧候选无需手动深维护才可接续。

[selection.py](../../../experiments/20261106-basepack/src/basepack/memory/selection.py) 按真实 worker 分数排序，去重复身份/原文覆盖，按文字预算交付完整内容与省略入口；词法距离不冒充 agent 分数。已安装 [skill](../../../experiments/20261106-basepack/src/basepack/memory/SKILL.md) 驱动一次检索委托，宿主按 `config ai --purpose retrieval` 的结果派工（默认 tier1），没有模型 API 或后台 agent。

memory init 安装原生 schema 并绑定项目 UUID，同时在项目 instructions 加入 brief 与已安装 skill 入口；普通 init 不建库。新进程按生成入口直接使用显式配置读取 brief，客户端与 launcher 读取同一密码文件，配置只接受回环 endpoint。入口同时定位本项目 launcher、cwd 和日志。数据库进程必须按项目独立物理目录启动，多聊天共用该进程。绑定核查防止误连另一项目；数据路径的实际归属仍须部署命令正确配置。

## Codex 来源边界

`maintain` 可读取宿主提供的项目 ID 和完整注册项目根目录清单，或使用配置的绑定；缺少绑定时报告不可用并继续文件维护。采集通过 Codex App Server 受支持的线程与消息分页，显式项目 ID 优先；缺失 ID 时以项目根目录及 Git worktree/common-dir 判断归属，其他注册根冲突或无法取得 cwd 留待核。采集的受管 UTF-8 文件进入同一维护路径，采集不等于语义接受；历史来源、附件、继承身份与精确回源仍按实际能力和验收结果报告。查询不触发采集。
