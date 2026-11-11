# 维护改造实施结果

2026-11-11（北京时间）。状态：改造、候选收敛、本项目安装及清理已交付；显式记忆维护的实际结果在末节接续。

## 授权与范围

用户要求完整阅读[调查知识维护未自动并行](codex://threads/01a1c97f-f5db-76c0-852f-b1db986b02f7)，执行其修改，再进行记忆维护。本轮以该聊天最后确定的[维护计划](automatic-maintenance-plan.md)为准：在独立候选试验默认无审计、使用反馈、父引用检查、入口刷新、透明事务分包、已阅处置、粗层策略、单维护所有权及目录治理。D、通用性能优化E排除，已有C沿用。项目纲领保持原文。

## 实施与验收

- 候选从固定0.9.1基线`490b1c219ef92b625dd3075a0516ce6c761c5f80`独立建立并验证，38项实现/回归/依赖变更合回唯一active路线`experiments/20261106-basepack`，版本0.10.0.dev1。候选目录只留结案README，受测源码ZIP及收敛哈希保存在原证中，不长期双写源码。
- 已交付父项解析/依赖并发guard、AGENTS托管入口与升级刷新、原生事务透明分消息、默认无审计、持久使用反馈、来源已阅/重复与待细化处置、单owner维护及工作包进入根tmp。CLI apply显式传control，Python省略时仅在空闲项目取短期owner；反馈报告可并发，发布由单owner负责。
- 完整候选源码套件482 passed、5 skipped，280.57秒；实际导入候选src，隔离SurrealDB4.0.0内存实例。完整stdout未另存，工具结果及条件已整理；五个跳过项后续在active源码、独立数据库及共享模型配置下全部通过（13.44秒），涵盖图像/向量、原生恢复、特殊ID与overflow。事务后续专项14通过、反馈含新旧表原生恢复8通过，保留原日志。代码测试属于开发验收，普通知识批次不追加审计。
- 普通任务子agent只收到业务问题及生成AGENTS，实际brief、取得owner、预检、派协调者、stop/取消/release；释放前未另观测协调者终止，后续宿主状态为interrupted。停止control和空发布列表保证旧任务不能继续发布，不把事后状态冒充当时观察。
- 本项目普通安装在`D:/AgentTools/envs/basepack-client-0.10/`，只修改本项目runtime.python与入口；原共用客户端仍为0.9.1。最终wheel SHA256为`db6d990cf0476359948663e5cdfd7053ffe63f48e14624f5145297166ba5af5a`，50个包文件与安装和active源码逐字节相同。刷新前后原UUID`464948e9-d41e-420f-966b-ebaa602fd9bc`、七表计数、三条fresh mandatory及托管块外字节已核；共享模型、数据库进程/目录/原凭据及其它项目入口未改。
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

0.10真实维护中多次出现`Partial file summary requires explicit coverage_gaps`：作者把framed聊天file摘要范围写为正文第2行起，而原件第1行仍是文件一部分。程序正确拒绝，尚未半发布。已在随包SKILL的members唯一合同补明完整file覆盖1..末行（含头部）、依据chunk可仅覆盖正文；真正部分覆盖仍须真实gaps。协调者确认无在途apply后短暂停新发布，重建普通wheel并核50文件一致后恢复；逻辑/API/schema/owner不变，已获作者草稿复用，SKILL来源重新prepare。

真实维护又确认程序缺口：两份作者batch把dispositions放在顶层，旧apply返回成功却只登记source。已将两来源改回partial，创建持久反馈；在共用_apply以字段存在检查拒绝顶层dispositions/deferred_refinement，报明应在对应sources[]，不自动搬移或引入通用schema平台。隔离红测复现静默接受，修复后数据库/CLI定向60passed、0skipped，覆盖空/null及自动/显式owner、编码前拒绝、六表无半批、已有合法B/F。唯一发布者确认无在途apply后安装并核50文件一致；原作者重新prepare并正确嵌入source，两来源成功发布，feedback:3e330779946046c59a1e0d3f5c5f845e已resolve为fixed。前一条framing处置反馈feedback:ec6f65a4e19f4f949d2bf1827ebe8b7c亦已fixed。原错、批次与实际回归见misplaced-disposition/及本轮台账。

## 本轮记忆维护

任务内后台预检第一次在沙箱内失败：Codex App Server无法打开`C:/Users/ysPan/.codex/state_5.sqlite`（SQLite code 14 / OS error 5）。正常用户上下文重跑成功：3机械批次、31复用块；固定回执`.basepack/memory/maintenance/1030e20e195c4b3e938a785ae99ca9a2.json`，control为`.basepack/memory/20261111-implementation-background.control`。已按回执模型实际启动维护协调者，按用户的新策略不追加事后审计。新一轮显式维护在实现与整理之后进行；后台处理量不代替该项交付。

后台回执另有全局聊天归属未决336项、采集gap 73项；它们不等于本项目缺失聊天数，也不表示已接受750个语义来源候选。最终已处理范围、未决和余项据实际运行补充，代码测试数、派工成功与知识数量均不替代功能验收。
