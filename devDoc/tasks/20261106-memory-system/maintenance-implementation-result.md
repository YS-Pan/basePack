# 维护改造实施结果

2026-11-11—12（北京时间）。状态：改造、候选收敛、本项目安装、清理及固定回执的显式记忆维护均已完成；维护所有权已释放。

## 授权与范围

用户要求完整阅读[调查知识维护未自动并行](codex://threads/01a1c97f-f5db-76c0-852f-b1db986b02f7)，执行其修改，再进行记忆维护。本轮以该聊天最后确定的[维护计划](automatic-maintenance-plan.md)为准：在独立候选试验默认无审计、使用反馈、父引用检查、入口刷新、透明事务分包、已阅处置、粗层策略、单维护所有权及目录治理。D、通用性能优化E排除，已有C沿用。项目纲领保持原文。

## 实施与验收

- 候选从固定0.9.1基线`490b1c219ef92b625dd3075a0516ce6c761c5f80`独立建立并验证，38项实现/回归/依赖变更合回唯一active路线`experiments/20261106-basepack`，版本0.10.0.dev1。合回时，候选目录只留结案README，受测源码ZIP及收敛哈希保存在原证中，不长期双写源码；该残留入口于2026-11-14退役，见[目录退役](#候选路线历史与目录退役)。
- 已交付父项解析/依赖并发guard、AGENTS托管入口与升级刷新、原生事务透明分消息、默认无审计、持久使用反馈、来源已阅/重复与待细化处置、单owner维护及工作包进入根tmp。CLI apply显式传control，Python省略时仅在空闲项目取短期owner；反馈报告可并发，发布由单owner负责。
- 完整候选源码套件482 passed、5 skipped，280.57秒；实际导入候选src，隔离SurrealDB4.0.0内存实例。完整stdout未另存，工具结果及条件已整理；五个跳过项后续在active源码、独立数据库及共享模型配置下全部通过（13.44秒），涵盖图像/向量、原生恢复、特殊ID与overflow。事务后续专项14通过、反馈含新旧表原生恢复8通过，保留原日志。代码测试属于开发验收，普通知识批次不追加审计。
- 普通任务子agent只收到业务问题及生成AGENTS，实际brief、取得owner、预检、派协调者、stop/取消/release；释放前未另观测协调者终止，后续宿主状态为interrupted。停止control和空发布列表保证旧任务不能继续发布，不把事后状态冒充当时观察。
- 本项目普通安装在`D:/AgentTools/envs/basepack-client-0.10/`，只修改本项目runtime.python与入口；原共用客户端仍为0.9.1。最终wheel SHA256为`f9036c12ea38fdaf024b66252354174139834accaf7ecdab2b4c9cc53a769040`，50个包文件与安装和active源码逐字节相同。刷新前后原UUID`464948e9-d41e-420f-966b-ebaa602fd9bc`、七表计数、三条fresh mandatory及托管块外字节已核；共享模型、数据库进程/目录/原凭据及其它项目入口未改。
- 目录治理先核活动使用、实际配置与当前/历史来源；未以文件夹名字作为删除依据。具体结果见下节。

旧客户端背景维护的真实413批次在新客户端单次Python apply成功：相同batch、3来源、29成员、1节点、1边，无invalidated。旧HTTP SQL为1,254,584字节；新原生事务一个query消息为1,271,022字节，2.559秒，未手工拆批或调整HTTP服务限额。本例未达到新消息分组上限，多消息原子性由隔离专项证明。该次生产写入为项目SurrealKV上的一个合法实测，未扩张成完整磁盘负载验收。

升级前因明确回退目的生成一套当前原生export（109,952,442字节）及原件/assets压缩包（2,990,047字节）和配置/入口快照，存于`upgrade-before/`；原凭据仍在既有password_file，未复制到原证目录。没有复制整套旧备份或重新叠加历史备份。

## 策略比较与限制

同档位两作者各读五份共1,163字符原件；细/粗完整输出6,726/7,955字符，不能证明更省。无变化对照baseline/candidate为3/0语义候选、915/125字符回执、0.109/0.178秒，未计已阅/延期处置建立成本，单次候选反而较慢。粗层摘要漏排队例外但原文块保留，跨源仅形成共同出现/佐证，未证明因果；拼接不相邻原句的连续chunk被实际apply拒绝，source/member均无半发布。程序能拒绝伪造原文，不证明摘要或关系语义正确。完整协议、作者输出、实际拒绝及未知token/总墙时在原证中，未宣称普遍质量或成本收益。

隔离负测使用内存引擎；自定义服务端WebSocket限额、SurrealKV全面负测及长期负载未验。Windows一次owner.json替换WinError5的外部持读句柄机制已复现，原次实际占用者未知；错误保留，不加盲目重试。团队使用量、token及费用不可得；主agent负责整体与root文档，协调者管理代码五分支和实际集成，清理分支独立核引用/执行，后台维护另有持续协调者，主上下文/往返未计量。

开发、安装、事务、反馈、生命周期、比较及413原证统一在[实施原证索引](../../../artifacts/runs/20261111-maintenance-implementation/README.md)。

## 目录清理

22:01:49（北京时间）完成历史备份组：删除`.basepack/backups`、`.basepack/memory/backups`和`.basepack/memory/devdoc-backup-20261109.surql`，共2,535文件、1,005,490,896逻辑字节。清理前核完整当前/历史来源路径无匹配、目标解析与元数据、无reparse/nested Git，以及原生进程视图中无活动引用；仅用同一PowerShell的`Remove-Item -LiteralPath`执行。

独有安装与覆盖原证选留64件、17,307,399字节，逐件hash核对；没有搬走整套备份来抵消清理。删除量与选留新增量分列，不把并行运行中的整个项目空间变化当成精确净值。清理后`/ready`为200，原8次mandatory/旧basis/图片回读和hybrid literal检索通过，配置、入口、launcher等5个不变量未变（凭据仅核元数据）。原库、原件、assets、受管聊天、活动维护、jobs和492份onboarding捕获仍保留。后续限定杂项及两组扩展清理已全部完成，见下文。

清单、选留映射及前后原证在[清理原证](../../../artifacts/runs/20261111-maintenance-cleanup/)。首次执行在删除前因PowerShell时间类型比较中止，核实不变量后改用UTC ticks完成；未以重试掩盖删除结果。

最终按四组清单累计删除2,877文件、1,064,167,175逻辑字节，另非递归移除7个确实为空的容器：备份2,535文件/1,005,490,896字节，限定杂项81文件/1,849,500字节，覆盖工作包220文件/44,359,998字节，散落历史导出及工作包41文件/12,466,781字节。十份尚无精确原件重建依据的包（3,488,837字节）、覆盖真实结果/语义输入/driver、onboarding原件及维护身份全部保留。最终ready200、8次指定回读、literal检索、2,096/2,096兼容向量、64件选留hash及升级后6项文件不变量通过；[精确清理结果](../../../artifacts/runs/20261111-maintenance-cleanup/result.md)列明保留例外。一次入口在授权升级中刷新导致清理前检查中止，重新以已完成升级的基线核对后执行，未吞掉不变量错误。

## 真实使用反馈与修复

0.10真实维护中多次出现`Partial file summary requires explicit coverage_gaps`：作者把framed聊天file摘要范围写为正文第2行起，而原件第1行仍是文件一部分。程序正确拒绝，尚未半发布。已在随包SKILL的members唯一合同补明完整file覆盖1..末行（含头部）、依据chunk可仅覆盖正文；真正部分覆盖仍须真实gaps。协调者确认无在途apply后短暂停新发布，重建普通wheel并核50文件一致后恢复；逻辑/API/schema/owner不变，已获作者草稿复用，SKILL来源重新prepare。

真实维护又确认程序缺口：两份作者batch把dispositions放在顶层，旧apply返回成功却只登记source。已将两来源改回partial，创建持久反馈；在共用_apply以字段存在检查拒绝顶层dispositions/deferred_refinement，报明应在对应sources[]，不自动搬移或引入通用schema平台。隔离红测复现静默接受，修复后数据库/CLI定向60passed、0skipped，覆盖空/null及自动/显式owner、编码前拒绝、六表无半批、已有合法B/F。唯一发布者确认无在途apply后安装并核50文件一致；原作者重新prepare并正确嵌入source，两来源成功发布，feedback:3e330779946046c59a1e0d3f5c5f845e已resolve为fixed。前一条framing处置反馈feedback:ec6f65a4e19f4f949d2bf1827ebe8b7c亦已fixed。原错、批次与实际回归见misplaced-disposition/及本轮台账。

另一次作者仍在补第4行依据时，旧42成员草稿已发布。来源改回partial并按当前prepare补齐，feedback:a832017a712a4e6ca359e0ce70d0b5b0已fixed。协调者模板现要求作者明确完成、给最终路径/hash；修订另存，发布者冻结唯一自有快照并提交该字节版本。15项模板回归通过，实际后续批次采用此交接；本轮发布冻结、stop且全部后代结束后，将最终模板wheel安装并核50文件一致，再释放owner。没有追加语义复审。

本机共享embedding服务实际`max_length=2048`。三次批次遇到HTTP500，服务原错记录超限token，编码在forward前拒绝；原作者按记录边界重分块后成功。后端按长度排序，错误向量序号不能直接映射作者成员；逐项诊断才确定其中一个超限chunk。没有机械截断、提高共享服务限额或原样盲重试。客户端HTTP500尚缺输入身份和token细节，已形成[Issue草稿](../../../artifacts/runs/20261111-maintenance-implementation/embedding-overflow-issue-draft.md)，未提交。

## 本轮记忆维护

任务内后台预检第一次在沙箱内失败：Codex App Server无法打开`C:/Users/ysPan/.codex/state_5.sqlite`（SQLite code 14 / OS error 5）。正常用户上下文重跑成功：3机械批次、31复用块；固定回执`.basepack/memory/maintenance/1030e20e195c4b3e938a785ae99ca9a2.json`，control为`.basepack/memory/20261111-implementation-background.control`。按回执模型实际启动协调者，最终31次成功apply涉及61个唯一来源、200成员、1节点、4边；无在途发布时stop、取消并释放。随后另行成功提交上文原413批次。这些处理量不代替新客户端显式维护。

显式维护刷新Codex项目注册清单后，以回执`61f4ec9733fc4934a37b9812357054f3`固定来源与聊天截点：35个机械批次、298个复用块；语义候选767个唯一来源（727初次、40已有变动）。主协调者为唯一发布者，四名直属作者及两个下级分支按不重叠路径接续；全局不超过13个并发席位。每源由实际作者阅读、表示或给出有理由的已阅处置；按最终稿/hash交接，成功程序提交计入完成。

最终767/767均为handled，无assigned/partial，258条成功发布记录。626个来源的结案包含知识表示，136个为无新增知识，5个为重复/无新增知识组合处置；本轮已接受批次的sources条目未记录非空deferred_refinement。十组已跟踪依赖及本轮三条反馈全部解决。逐路径/版本/处置/提交快照台账、固定回执、原错及选留修正稿见[显式维护原证](../../../artifacts/runs/20261111-maintenance-implementation/explicit-memory/)。这是作者生成与程序提交的完成口径，没有例行回读、检索抽查或全库语义审计。

本轮control创建于11日22:40:53，12日01:24:34已确认释放，约2小时44分钟，包含实际阅读、派工、编码、修复和收尾；无同规模对照，不能据此宣称整体提速。stop时publications为空，协调者及所有后代已观察为completed；最终wheel同步后release成功，`memory owner`返回null。控制与回执按恢复合同保留，数据库和共享模型继续运行。

范围限制：原始捕获内已有的截断及上下文缺口按源保留，没有补造不可见文本。预检Codex统计为发现152、保留703、全局归属未决336、采集gap76；这些单位不同，不等于767来源中的失败数，也不能解释为本项目缺失聊天数量。固定回执之外及截点之后的新聊天、本文和最终提交变化留待后续维护；不为追逐本轮新材料重开采集。除上述捕获限制及embedding错误信息后续外，本轮固定范围无剩余阻塞。

## 候选路线历史与目录退役

2026-11-14 按用户要求核查并清理 `experiments/20261111-basepack-maintenance`。保留记录支持以下过程：

已直接回读[原始请求](codex://threads/01a1c97f-f5db-76c0-852f-b1db986b02f7)、[实施聊天](codex://threads/01a1cad7-01e6-7c32-bec9-b5442d561b95)及[候选测试分支](codex://threads/01a1cad9-1c6e-7b01-8e46-37b65b8c84ba)：用户要求新建experiment进行试验，后续确实建立独立源码与测试数据库，再按计划收敛。0.9.1于11月11日19:01发布时仍只有候选入口，源码实施发生在之后；这解释了早期发布记录与最终实施记录的阶段差异。

- 11月11日18:52，提交 `15d17b8` 先建立候选 README，约定从固定0.9.1基线导入源码、独立运行与验证；当时尚未实施，见[创建记录](../../change_log/minor/20261111_185037_plan-maintenance-experiment.md)。
- 后续实际建立候选源码。[完整套件记录](../../../artifacts/runs/20261111-maintenance-implementation/suite/README.md)明确记载实际导入候选目录的 `src/basepack/__init__.py`、使用独立端口19083的内存数据库，并记录482通过、5跳过。原完整stdout未另存；受测[源码ZIP](../../../artifacts/runs/20261111-maintenance-implementation/candidate-source-tested.zip)及[收敛哈希清单](../../../artifacts/runs/20261111-maintenance-implementation/consolidation.json)仍保留。
- 11月11日22:39，提交 `5abb8f9` 将候选改动合回 `20261106-basepack`，候选目录改为仅留结案README。Git在该候选路径只提交过README；未提交中间候选源码不代表没有隔离试验。实现与安装沿上文接续。

本次核对源码ZIP整体及38项候选文件哈希均与清单一致；按Git换行规范比较合回提交，35项与清单对应，其余3项仅调整候选/现行说明与路线引用。清理前目录仅有1199字节README，无隐藏附属材料、嵌套Git或联接，工作树干净，配置及进程无活动引用。已删除该README及空目录，将公开入口和相关文档链接改指本结果；原创建记录、Git历史、候选源码快照和运行原证保留。未修改现行实现、安装、数据库或服务。

检索限制：0.14.0的 `memory freshness` 在受限shell中报Codex App Server无法打开 `C:/Users/ysPan/.codex/state_5.sqlite`（SQLite code 14），未取得全项目清单或逐聊天新鲜度截点；以上相关聊天由宿主直接回读。现象已报 `feedback:0fbd4bfef4254cb2969a91f69d22c7b4`，待维护核实入口/权限责任；不据此认定产品逻辑缺陷。
