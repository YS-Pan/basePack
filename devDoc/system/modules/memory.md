# 项目记忆实现

本页描述0.18.0源码：SurrealDB原证与知识图、独立采集、prepare提案编译、单owner发布、严格交付事实及Gaussian行为访问投影。2026-11-18核对，稳定客户端已普通安装0.18.0[behavior]，纯文件宿主probe已closed并由父核通知恢复；真实8条小批仅新鲜预检，作者发布仍待验；已推广至正式18080/store-0.17；首批100候选实际维护已完成，后续全项目维护尚未完成，实际部署与维护边界见[部署合同](../deployment.md)和[实施记录](../../tasks/20261115-real-use-rectification/execution.md)。0.16既有验收见[整改结果](../../tasks/20261115-real-use-rectification/result.md)，历史实现见[记忆专项进度](../../tasks/20261106-memory-system/progress.md)。首建和维护由宿主订阅agent阅读生成，程序提交成功即完成普通批次，默认无额外审计。用户流程见[记忆说明](../../../experiments/20261106-basepack/docs/memory.md)。

## 职责与数据

认证在客户端构造边界统一完成：CLI/Python 共用 ProjectConfig 解析的 username 与 memory_password_file，以 UTF-8 解码文件（兼容 BOM，保留 CRLF/首尾空白）并发送 Basic Authorization；默认文件为实际 memory_dir/password.txt。config show 不读 secret，guide/rank/stop 与 prompt 不创建数据库客户端。password_env 手工桥退出；缺文件、权限或错密保留原错，不生成替代密钥或免认证回退。新库凭据由首次部署显式准备，launcher 读取同一文件；已有库和凭据随普通升级保留。

- [content.py](../../../experiments/20261106-basepack/src/basepack/memory/content.py)读取项目内UTF-8原字节版本与1-based行闭区间，保留CRLF。长单行可用locator的start_col/end_col精确定位，列为Unicode码点的0-based半开区间；prepare提供有界line_slices。结构单元及切片仅供定位，变化检查不生成语义边界。
- [store.py](../../../experiments/20261106-basepack/src/basepack/memory/store.py)通过HTTP查询领域记录，apply走原生WebSocket事务，完整语句按实际RPC消息字节透明分组，统一提交。大文字快照在同一事务内分段传输、组装为完整`source_version.text`，保留原字节、hash和来源版本；中途失败回滚整个批次，原生导出/恢复仍保存完整正文。`prepare`各来源的`snapshot_transport`提前报告原文字节、封装字节、语句数与消息上限，不能通过缩语义chunk或抬常数替代整源处理。没有多后端层或自建MCP，原生CLI负责服务与导出/恢复。
- `source_version` 保存文字原文快照或图片快照引用及接受时路径，新版本身份包含路径、分类及私有规则版本，正文未变而分类改变也保留独立历史；图片原字节在 `memory.data_dir` 下的 assets 中。`member` 同时承载来源层级、智能块/摘要、范围及默认检索表示。`node` 表达实体/决定，`semantic` 使用有属性原生 relation；`change` 保存实际旧记录、时间及宿主可取得的执行信息。
- [images.py](../../../experiments/20261106-basepack/src/basepack/memory/images.py) 保留原图 hash 快照与定位，完整写入并核 hash 后原子发布，已有损坏快照仍报错；[vectors.py](../../../experiments/20261106-basepack/src/basepack/memory/vectors.py) 复用现有 EmbeddingClient 批量编码，查询使用原生 cosine 与排名融合，普通返回省略数值大数组。图文模型和服务沿 R9 共用。
- 原字节 revision 识别来源；input_revision 绑定实际编码输入（文字为 title 加 text，图片为原字节），description_revision 独立跟踪图片识读文字；knowledge_revision 用于逐记录乐观写入，embedding_identity 绑定模型语义空间。apply 核本批改写、退休、更正目标及实际使用的既有依据成员、关系两端的 expected；不核无关条目，保留无关并行。同批新建记录走不存在检查，不能省略已有依赖的版本。

[privacy.py](../../../experiments/20261106-basepack/src/basepack/memory/privacy.py)集中计算布尔字段`private`，表示项目约定的限制分发边界，涵盖隐私、机密及版权/许可受限资料，不细分原因或自动判断许可。根`private/`始终私有，项目`memory.private_scope`可增加原位文件/目录，默认`[]`，`['.']`表示全项目；按规范化路径及目录边界匹配，分类不扩大discovery。freeze固定规则及revision，apply核当前规则并拒绝冻结后规则变化；纯Python freeze显式传`config=memory.config`。成员、节点及关系沿自身来源版本、`basis`与固定知识版本端点传播，有一项私有依据即整条标为true。旧版本依据使用其当时标记，状态更新保留标记；正文仅含可选私有路径引用不触发传播。prepare、检索、brief、知识历史与原证回读交付相应标记，成员和原证的标记分别保留。

私有规则改变沿新来源版本处理，不覆写旧快照分类；编码身份和实际输入未变的向量继续复用。存量补标或原位来源迁移另按确认映射限定范围，旧依据不足时报告未知，缺标不代表已确认为公开，不默认执行全库语义审计。完整库继续保存公私资料，受管快照、聊天和工作包沿[本机目录约定](../project-data-layout.md)保留。标记不提供访问控制或净化原生导出；公开分享副本的筛选工具留待后续。

## 已有行为

prepare固定本批实际读取的来源版本、同读新旧原文、相关邻域和expected知识版本；邻域包含以所选成员为依据的node→node关系，并补齐相关成员端点与直接依据。已有fresh记录已钉的basis/parent/endpoint历史依赖自动按`(ID, knowledge_revision)`保全，缺失旧版本明确报错，不替换为current；当前expected并发保护独立保留，private沿实际版本传播。作者显式选择旧端点仍通过`--historical-versions`的`{id, knowledge_revision}`数组固定，关联原文仍需read或扩充prepare核实。agent同次决定边界、摘要和有依据关系，apply核来源与知识版本后原子接受；冲突须重新prepare并共读。程序按精确范围和locator取得chunk，显式文字须逐字一致；更正的previous来自实际旧记录，独立增边保留其它边。

变化检查只发现待维护来源，不改已发布状态。apply 核版本并发布本批变更；未被本批替换的内容保留其实际依据快照，显式退役、更正及受影响关系按状态处理。接受删除保留旧快照与更正，不反复报告已处理删除。

退役成员不再触发当前原文失效、不作为父级传播桥，也不被未变兄弟重绑定改写历史版本；活跃但待核的表示仍参与真实依赖传播，显式复活继续核 expected。修复来源与当时的原生回归见[记录](../../change_log/minor/20261110_145550_fix-retired-memory-invalidation.md)，当前安装状态沿专项进度核实。

vector/hybrid 的 Python 与 CLI 检索统一返回 `matches` 和 `vector_coverage`；hybrid 的文字通道使用原生标题/正文全文，literal 对 path/title/text 做大小写无关的包含匹配，并使直接命中排在语义补充前；返回的 lexical_rank 标识直接命中。literal 只用于 hybrid，vector 下明确报错。

read 以 member ID 和可选的依据版本、位置回读保留的原文或原图快照。同 source 保留读取该来源任意已发布版本的合同；跨 source 由 change.previous 或其 members 历史证明成员曾属该来源，不要求成员精确接受过请求版本。路径优先使用 snapshot.path；旧快照缺路径时，优先取请求版本的成员历史路径，否则使用已证明同 source 的当前/历史成员唯一路径，多路径歧义报错。不强制改写旧快照，也不宣称能恢复未记录的精确历史路径。核语义关系时必须沿 basis 的 source_version 与文字范围或图片 locator 回读 original，stable ID 的当前 member 不能替换已保存的旧依据。快照缺失或损坏直接失败。neighbors 默认过滤 stale 的父子/语义展开，历史复核显式 include_stale。

成员使用程序生成的UUID。[draft.py](../../../experiments/20261106-basepack/src/basepack/memory/draft.py)的compile_proposals从作者提案的`prepare: {path, file_sha256}`核固定阅读包；作者提供语义选择和局部引用，程序编译source revision、UUID、expected、实际依据闭包与private。现有写入/退役/更正须在prepare中可证，缺依赖、冲突版本、无效依据或私有分类不明均明确失败；编译只跟随已表达的依据，不替作者选择证据。新记录局部引用和跨稿位置在freeze统一解析，生成的prepare_packages、dependency_closure和compiled_private随固定稿保存。改稿产生新文件/hash并重冻，同一冻结批次重放使用原batch_id/UUID。apply继续核原协议及原子接受；身份版本仍为2，0.17新增memory schema 3，旧库按隔离迁移合同切换。不存在的read目标明确报错。

[publish.py](../../../experiments/20261106-basepack/src/basepack/memory/publish.py)提供稳定 Python 组合 helper，`memory publish` CLI 调同一实现。有序完成稿引用为 path/file_sha256/assignment；publisher 根据具体 assignment 的显式交付和自有宿主句柄声明完成，程序不从文件或聊天结束推断它。helper 核文件 SHA256，复用 draft.py 的 freeze/validate/独占保存，再调用原 Memory.apply；没有另一套发布事务或作者状态库。短结果报告写入/invalidated 数量，本地详细 result 是原 DB batch receipt 的投影。首次从完成稿生成新 frozen；显式 `--frozen` 接续原 batch_id/UUID，包括本地结果写失败后的恢复。文件字节 SHA256 和 apply 的规范化 batch_hash 分开；改稿才经当前 prepare/阅读产生新 path/hash 与 freeze。未知提交继续原 marker/owner 合同，不自动重试或 release。其余原子工具仍可由 agent 用普通 Python 自由组合，语义修订归原作者，宿主继续负责实际派工和事件等待。

brief、search、read、neighbors和access-hints只读取已发布状态及其依据版本，不扫描原件、触发维护或补写行为投影。brief不搜索或连接embedding；task只是标签。`startup_overview`在图节点、项目摘要和受管聊天摘要三路结构入口中交错选有界代表，默认六条，每条正文最多800字符并标text_truncated。正limit时非mandatory工作集按`min(max(limit×8,24),96)`取样，默认最多48条，只对这些候选计算精确access-hints；组内优先访问区间上界再下界，跨节点类型/项目顶层目录/聊天组交错，低权重无硬过滤。所选clues保留实际区间、支持度、模型、事实/编译游标及状态。overview_sampling披露候选数和rotation_utc_date，UTC日只确定无持久状态的展示轮换，不改变J/C/hits/年龄，不构成日历遗忘。

overview_groups/overview_count及clues_omitted_count披露库存与遗漏，unmapped_sources最多三条项目/聊天交错入口，并保留总数和遗漏数；已有未读缺口另交付，不把未映射等同未读。brief仍需读取现有概要和投影，有界候选只限制精确Gaussian核计算，不承诺常数总成本或完整语义覆盖。mandatory独立保留，stale mandatory仍交付并标待核。known_unsynced比较已登记来源与表示/依据的接受版本，未发现变化保持未知，false不证明现行。changes由维护显式调用，发现变化不改已发布记录。

向量绑定实际输入版本及 embedding_identity；仅支持 vector/hybrid，默认 vector。search 报告已发布范围内相同 identity 的兼容与待建数量，brief 明示未检查；缺少兼容向量时明确报错，真实空范围与空命中保持可辨。旧 text 配置须先改为 vector 或 hybrid，再 embed 补建索引；CPU/CUDA 的相同语义 identity 共用向量。apply 先准备候选向量，并在同一短事务发布内容和匹配向量；模型失败保留原错误并停止本批，不发布无匹配向量的内容。输入版本与 identity 未变化的向量可复用。

`memory collect`独立执行Codex归属与原件保全，不取得维护owner；回执记录捕获范围、正文hash及缺口，失败保留原错和失败回执。绑定Codex的`memory maintain`必须明确选择`--collection <receipt>`或`--retained`，后者只声明消费已保留原件，freshness未知；没有skip-codex-collection旁路。load_collection核项目身份、路径清单和当前字节hash，prepare随后固定本批实际读取版本，apply再核版本；该观察不锁定文件，也不构成全项目不可变快照。

maintain默认从项目Git清单加source_scope发现原件，并加入根`private/`独立Git的已跟踪及未忽略新文件；非Git项目按声明范围发现。默认全项目接续已登记、删除、pending和保留聊天来源；显式`--scope`按路径边界实际限制新发现、已登记及删除来源，不再仅限制新文件发现。范围外pending保持未处理，组外依赖只为本批闭包核实。零行且无活动知识时仅登记来源；清空旧正文仍处理旧成员和依赖。机械候选须按依据闭合，不能证明闭合则转语义；短结果与完整回执分别报告工作集、discovery缺口、机械证据和语义余项。枚举、机械更新或回执成功不证明全项目语义覆盖或最终磁盘全fresh。

安装agent取得不含主agent、包含后代的宿主容量及来源并写入AI配置；实时可用席位另传。[prompts.py](../../../experiments/20261106-basepack/src/basepack/memory/prompts.py)保存finite-wave-v1布局、单一Terra身份、reader上限及AI快照；容量不足以提供reader和恢复名额时保留阻塞，不补默认无reader协调者。`memory prompt`只读配置／模板／固定回执渲染唯一协调者，不读凭据、不连库或模型；宿主仍须实际派工，Luna由wave create返回完整spawn_arguments，旧逐组派工／pending-dispatch已被替代，旧组织receipt不会静默转换。

[waves.py](../../../experiments/20261106-basepack/src/basepack/memory/waves.py)和[wave_cli.py](../../../experiments/20261106-basepack/src/basepack/memory/wave_cli.py)维护项目本地`memory_dir/maintenance/wave.json`，固定任务、worker、初始化／执行回执、通知及publication intent。Terra每波首turn规划独立语义任务并显式选`--readers N`较小固定池，N受任务数及保存reader上限限制；长组先发，依赖前波新发布知识者留下一波。task.paths限当前stage.remaining.paths；无stage时限receipt.workset.included（含本轮授权的stable来源），read_paths只供额外共读，draft.sources与member.path不越paths；图／feedback-only可paths=[]，新发现来源不自动纳入接受。

Terra预登记并实际启动全部Luna，交固定初始化回执后结束turn。Luna首turn事件等待go，未封口不能领取或退队；原父任务保留句柄和Terra恢复席位，核其真实空闲及成员启动／失败终态后seal并发一次go。Luna原子claim→脚本task-prompt→阅读与正常修稿→固定引用submit循环；无任务时退队与活动数变更原子进行。最后正常退队者保存执行回执、取得唯一票，再实际followup同一Terra；普通早退只留消息，程序资格不等于宿主已受理。

Terra第二turn按汇总固定引用、覆盖和异常编译／唯一发布，正常不逐稿全文复读或增加语义审计；固定publication结果后即FINAL，不等通知ack。原父任务核Terra FINAL及最后Luna的ack／宿主终态后机械wave close。通知结果未知保留pending与owner；notification-recover仅按通知者已结束及已核宿主证据补记，不重发followup。已确认publisher终态、无提交且无在途publication时，publication-failed固定原错并终止旧intent，未发稿留有限修复波；未知提交保留原intent/frozen/owner核实。

主任务约十分钟以内保留brief并跳过整个自动maintain；长任务在宿主支持生命周期时并行启动，子任务不递归维护，显式维护不受门槛限制。owner在预检前原子取得，冲突报告原持有者；结束stop、取消自有后代，核发布终态后release。领取、通知处理和发布均核owner/control/wave及stop；已在途followup可能迟唤醒，第二turn先核停止并拒绝发布。异常worker、全体消失或残留claimed由原父据宿主事实恢复，不超时抢回。HTTP查询和反馈不要求owner；CLI apply使用自有control，Python apply省略时仅在空闲项目取得短期owner。控制不终止共享服务或已开始推理。语义派工前失败，仅本进程自有且确认无派工／在途／未明发布时才stop/release，清理错误与原错一并保留；独立采集失败与此链分开，他人owner及未明状态保持。

固定候选中的来源组由Luna作者负责理解、关系及普通修复，共享图写目标唯一归属；保留mandatory、覆盖、gaps、feedback和实际接受版本。同稿FINAL不重复处理，改稿用新path/hash。接受后新增变化和回执外来源留下一有限范围；执行回执不证明语义接受、全范围完成或最终磁盘fresh。[stages.py](../../../experiments/20261106-basepack/src/basepack/memory/stages.py)只接受finite-wave-v1，在当前wave已closed后核handoff.wave_id、完整scope分割、固定稿／发布结果引用及本run全部实际启动worker（含历史wave）及本阶段publisher的ended句柄，沿原owner/control返回干净新协调者与剩余范围。它不作为逐任务恢复Terra的默认循环，也不执行0.17旧组织stage。详见[有限wave设计](../../tasks/20261115-real-use-rectification/maintenance-waves.md)及[产品流程](../../../experiments/20261106-basepack/docs/memory.md#有限任务池与两段式-terra)。

[feedback.py](../../../experiments/20261106-basepack/src/basepack/memory/feedback.py)在新增feedback表持久保存观察版本、漏检查询和处理结果；报告可并发，无需维护owner，未决报告进入needs_semantic及固定回执。修复先据当前版本apply，再由owner解决报告；旧报告不覆盖新版，未决不假关闭，原生导出恢复保留。检索只做业务所需阅读，发现问题就报告；只有用户明确的审计意图启动手动审计。

[reviewed.py](../../../experiments/20261106-basepack/src/basepack/memory/reviewed.py)把非空来源实际已读范围的无新增/重复处置及已读待细化保存在source_version，核相关表示版本。有效处置抑制未变首建，来源/依赖变化重新入队；部分范围不代表整源。粗层表示仍保留精选原文依据和mandatory，未读缺口不伪作已读。非空parent纳入共用版本和解析检查；依赖临时写guard防止快照隔离写偏斜，逻辑版本和未变历史不增加。

[selection.py](../../../experiments/20261106-basepack/src/basepack/memory/selection.py)按worker一次综合分数排序，去重考虑成员、依据版本、位置和实际内容；按文字预算交付内容与省略入口，不二次乘访问权重。[retrieval.py](../../../experiments/20261106-basepack/src/basepack/memory/retrieval.py)唯一维护请求、工作目录、稳定delivery_id及请求加slot的派工身份；prompts仅复用渲染入口。retrieval-dispatch/retrieval-prompt返回默认tier1及实际模型/推理强度，不绑定维护receipt/control/owner，零席位由主agent执行同一完整流程。新问题用新请求及干净历史，重试复用原请求；没有模型API、常驻agent或另一套槽位登记表。

memory init安装原生schema并绑定项目UUID、member identity 2和memory_schema_version=3，同时刷新项目入口；普通项目init不建库。已绑定库缺失或不符schema 3时，新版memory init及普通读写明确拒绝；离线桥在全字段verify后由finalize显式设置标记，再用新版init安装schema，保留已有J。每个任务一次brief，后续shell只初始化参数。客户端和launcher读取同一密码文件，配置只接受回环endpoint。数据库按项目独立物理目录/进程启动，多聊天共享；UUID核查防误连，实际数据归属仍由部署配置保证。

## 知识历史与最终交付

[history.py](../../../experiments/20261106-basepack/src/basepack/memory/history.py)按 `id + knowledge_revision` 返回精确知识表示，和 `source_version` 的原证回读分开。schema 的同步事件在知识版本推进时保留前后像，覆盖显式接受、失效、更正、退役及关系重建；向量不进入历史。已有未归档版本使用安装基线事件 0，未来新版本保存实际出生事件；首次归档旧版不能重置其已衰减权重。init 不全量扫描或补造旧版本；旧 change.previous 中可证明的前像仍可读，存量缺口明确报告。关系 `endpoint_versions` 与层级 `parent_version` 指向观察版本；历史 neighbors 精确展开已固定端点，未留 pin 的存量旁路另外标为未知，不能用当前 stable ID 替代旧端点。`claim_type`、`conditions` 由作者接受，不按日期或热度自动推断替代。

[access.py](../../../experiments/20261106-basepack/src/basepack/memory/access.py)用独立短事务记录宿主确认的实际交付，单位为member/node/semantic的精确知识版本。稳定delivery_id原子去重，同ID清单或context改变报错。首次确认含空清单均推进严格事实J，非空事件才推进机会C；重试两者均不推进。context必含anchors、knowledge_cutoff、query、episode、candidates、budget、policy、model；每个锚点保存唯一逻辑ID、精确版本、alpha与base_quality，当前规则为去重后等份，总和为1。内部检索轮次、search/read/rank均不产生交付。未知提交保留同ID核验，已提交事实不因投影失败撤销。

`memory retrieve --question`准备默认全项目/6000字请求，缺问题返回needs_input；scope是项目相对路径前缀，业务条件写question。返回prepared/started=false，宿主实际派工并接收。worker先运行`retrieval-start --request`，在行为候选进入前固定基础搜索结果、原始锚点/份额/基础质量和知识观察截点，再固定本请求的行为候选；同请求多轮复用，修改请求后不得继续原锚点包。worker回读原文及必要历史/图，保留实际观察候选数组，再一次综合评分并rank。`retrieval-receipt --request --ranked --candidates --output`从固定上下文及排序结果形成待确认delivery，候选文件为数组，须包括基础/行为候选及最终交付版本；主agent实收核清单后才调用delivery。评分、原证范围和知识版本分别保存，node/semantic不伪造路径。CLI不自动启动agent，也没有宿主最终交付回调。

make_delivery_receipt在context.access_observations逐条保留base、behavior和followup实际返回的access_model、access_compiled_j、access_fact_j及access_interval，并标明来源及精确知识版本；同版本多次读取的不同快照均保留。context.model固定的是行为候选发现所用模型，后续回读若遇并发模型切换，可带不同访问快照，不能用context.model覆盖这些实际观察。

## 行为表示与访问投影

[behavior_model.py](../../../experiments/20261106-basepack/src/basepack/memory/behavior_model.py)只用真实共同交付逻辑ID篮子训练无正则KL-NMF，重复篮子按n/d频率忠实聚合；空篮子与单项篮子不提供共交付证据。训练记录支持度、求解器、依赖版本、尺度规则及截点，默认rank=8。行为模型不使用正文、query、LLM分数或旧权重，不因低权重过滤训练ID；普通修订继续同逻辑ID，精确版本有效性另核。训练所需numpy/scipy/scikit-learn由可选behavior extra提供，缺依赖明确失败，不阻挡基础采集、发布和检索。

[behavior_projection.py](../../../experiments/20261106-basepack/src/basepack/memory/behavior_projection.py)默认epsilon=0.001、beta=0.2、strength=8，均为工程初值，不是效果最优结论。对各原始锚点分别计算Gaussian再按原alpha加权；未知向量或锚点份额形成区间，已知份额不重新归一。只有非空交付累计C、已知锚点质量H和未知质量R；命中版本先累计本事件，再重置其标量基准和真实hits。每精确版本保存C/H/R对应标量基准，首次接受记录事实头j_enter并形成h=0先验，不冒充使用。权重不依赖日历，不传播命中，旧版不奖励新版。

`behavior-compile`在当前固定模型中按严格J增量推进，返回fact_j与compiled_j；未编译或冷启动保留unknown/pending/lagging状态。access-hints和behavior-candidates只读一致投影，不隐式训练、重放或写状态；delivery记账后显式接续编译，派生失败保留事实及原错。`behavior-train`保存不可变`memory_dir/behavior/<sha256>.json`，用原始交付和首次接受事实全史重放，在乐观事务中原子切换模型及投影；旧请求保留其实际模型及原始锚点，晚确认按当前提交顺序编译。旧事件缺原始锚点仍可提供真实共交付，机会质量保持unknown；不补造历史曝光或精确接受截点。

低权重不触发正文、依据、历史、图、向量删除或训练ID退出，不设置GC/forgotten状态。所有保留材料仍有基础检索资格，实际交付可刷新该精确版本；mandatory独立交付。模型工件、事实及备份仍受private的限制分发边界约束，数值形式不构成公开副本。精确Gaussian按实际非零锚点质量计算，不保存全库相似矩阵；当前实现不承诺大规模性能或长期业务收益，效果沿真实使用反馈维护。

## Codex 来源边界

`collect`读取宿主提供的项目ID和完整注册根或配置绑定；缺少绑定明确报告binding_unavailable，文件维护不依赖成功采集。采集通过Codex App Server受支持的线程与消息分页，显式项目ID优先；缺ID时以根目录及Git worktree/common-dir判断归属，其他注册根冲突或无cwd留待核。采集回执及framed原件保存身份和观察边界；maintain明确选择成功collection回执或retained，语义回执/reader提示交接项目ID、采集信息及保留目录。受管UTF-8文件沿同一来源版本维护，采集不等于语义接受；历史来源、附件、继承身份与精确回源按实际能力及验收报告。查询不触发采集。

`memory freshness` 只读项目归属、分页、采集回执及原文比较，不取 owner、不写原件或发布；按相关候选和用户点名聊天补读，跨项目引用用宿主读取。最新捕获及可关联预检提供线索，预检 pending 为历史快照，不是当前语义状态；回执时间、端点及 updatedAt 不能单独证明全局正文覆盖。输出保留未摄入、待语义、补读及未知。
