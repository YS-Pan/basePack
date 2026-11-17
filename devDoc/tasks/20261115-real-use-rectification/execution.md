# N0—N5 实施与本项目迁移执行

2026-11-17用户已授权执行当前计划，完成后迁移本项目数据库并维护；随后要求并行调查Terra用量并尝试修复确有证据的问题。本页记录接续信息；技术决定沿[目标架构](target-architecture.md)，实际接受结果沿[进度](progress.md)。记忆迁移限本项目，相关统计器修复按后续授权执行；不修改纲领，不自动推送/发行。

## 当前组织与状态

- 知识分支：独立采集、严格工作集、长单行locator、固定prepare与语义提案编译；唯一负责store集成。
- 行为分支：严格事实J与非空C、KL-NMF、Gaussian H/R增量编译及快照重放；负责access/schema及数值模块。
- 检索分支：请求级身份、行为筛选前固定原始锚点、行为候选、一次评分与跨领域概况。
- 迁移分支：只读导出、独立物理库演练、逐字段保留与恢复，等待主集成通过后才正式切换。
- 主任务负责CLI/维护派工、依赖锁、安装及切换门、文档与最终收尾；测试分支核CLI和新派工合同。

N0—N4初始实现已提交`9d3e479`。普通wheel首次49项/40步验证使用真实0.15共享图文embedding，加权brief/schema门定点23项/10步亦通过；初始0.17.0 wheel SHA256为`902aaec7f5e426f35636b063fac2939d23fc714a67eadee360cdfd744aea216f`。真实维护暴露历史pin缺陷后，已修复并安装0.17.1，wheel SHA256为`cd9c12b9b590c8b95f95eada65319b56e4344e9a84db0b96fbdc9142bb80d4bb`，65个安装文件逐字节一致且pip check通过。原18080保持关闭，新正式物理库暂在18176，尚未推广。这些结果不表示N5已完成。

长回归修正过时合同后，受限上下文801 passed/2 failed/6 skipped；普通上下文809 passed/3 failed/6 skipped。最后三项为两处Windows owner原子替换WinError5及一次本地测试库连接超时，原失败维护路径定向4项通过；owner独立200周期、600次替换通过，事后属性/可获得DELETE访问句柄/占用检查未找到根因。未修改owner协议或加入自动重试，不能把这些间歇错误宣称已修复。下一步在保留原库的迁移新库上进行首批真实维护观察，若复现则停止并按实际状态处置，不掩盖发布不明。

最终打包前仅删除retrieval模块尾部空行，与普通wheel定点验收件仅此字节差异，Python AST相同；最终65文件与工作区源码逐字节匹配。正式安装时再核实际site-packages，原验收件/最终身份报告分别留存，不混淆SHA。

## 已确定的上线合同

1. 初始实现0.17.0、首试修复0.17.1；新增memory schema版本3，保留member identity版本2。数值依赖为可选behavior extra，锁定本次NMF实现版本；共享embedding服务不随客户端更新。
2. `memory collect`独立采集；`memory maintain`明确选择采集回执或retained快照，不在owner内隐式采集。采集结果与语义接受分开，采集失败保留原错和回执，不静默回退。明确scope限制实际工作集，默认全项目仍纳入已登记来源。
3. 原始事实的J包括首次接受的空/非空交付；C仅非空推进，技术重试两者均不推进。精确版本命中先累计本事件再重置基准，读API不隐式写投影。
4. 旧delivery保留原清单、非空事件顺序和原context，不伪造完整新J或锚点；新J从切换基点开始。缺原始锚点为unknown，仍可训练真实共交付。
5. 旧接受时间无法证明时，j_enter保留未知，另固定迁移后观察起点，仅表示新规则从切换处开始观察，h=0不冒充命中。重训不移动该起点；有真实旧命中的版本保留可证奖励/基准。历史年龄无法完全恢复是明确限制。
6. 保留原件、知识版本、关系、依据、mandatory/private和未变embedding，重建行为派生层；不因低权重删除或退出。先隔离验证，再同步切换客户端/库，旧库和旧wheel仅作回退。

## 执行证据与余项

用户追加：迁移后的维护同时作为本轮真实使用测试，先约100个维护候选组成一批；数量是本次样本建议，不是产品硬预算。每批核实际范围、作者编译/共读协作、原子接受和必要检索结果，记录实际接受与剩余；出现明显不符时先修实现和对应回归，再做下一小批。原授权范围按批接续，不以100条替代全部处置。沿正常维护链观察，不另建形式化对照、监控或例行语义复审平台。正式迁移留一次完整恢复集合，各批只保范围/接受回执/事实与模型游标的小型观测；整体结束保留最终恢复点。

工作包、测试日志及隔离库位于`tmp/20261117-implementation/`，交付前选留必要原证到`artifacts/runs/20261117-implementation/`；生产恢复集合沿`.basepack/memory/backups/`。正式停写后的新鲜导出含24条旧交付、9条反馈；旧物理库保留并暂在18174只读使用，新`.basepack/memory/store-0.17`在18176恢复。新目标原生重导出与新鲜源导出SHA256相同，数据桥finalize已逐字段核对schema/索引/事件及记录后写marker3。恢复集合`architecture-0.17.0-20261117`含2702文件、951,738,769字节及逐文件哈希，包含旧客户端/配置/凭据/入口、原件、assets和必要回执。

新库保留8192成员、9264知识版本；旧8005个向量全部兼容。真实旧事实训练并重放后J=compiled_j=0、C=24，23个共用篮子、rank8；139个有旧访问记录的精确版本命中数与重放一致。只读brief保留3条mandatory，真实共享设施vector search、文本/图片原文、history和neighbors均通过，未写合成交付。staging配置为`.basepack/staging-0.17.toml`，其data_dir仍为本项目`.basepack/memory`，首批维护将直接使用该新正式库；新客户端依赖实际为numpy2.5.5、scipy1.18.1、sklearn1.9.1。共享embedding服务保持0.15。

初次brief成功并保留三条mandatory，跨历史检索实收5376字符/5个精确版本并确认旧event24。旧客户端例行automatic在语义派工前复现Codex SQLite14，已自清理。新独立collect在普通用户上下文成功，采集1164个路径，包含本聊天；仍有100处捕获/发现缺口及336项归属未明，不宣称全部历史完整。首100来源的只读选择、实际维护及修复循环见下节；按实际授权范围报告接受版本、缺口与未完项，不能以预检成功替代维护完成。

## 首批真实维护与修复循环

首批固定100来源，54修改、41新增、5既有成员待同步；包含主计划聊天与本执行聊天。第一次预检与主任务安排的部署文档编辑重叠，source revision guard正确拒绝旧内容；出错前5来源已有21条机械接受。主任务停止并发改原件，核owner=null后使用全新control重跑，不复用失败control。第二次预检完成41个机械批次、复用349块；实际included集合恰等于100选定来源，无范围外来源，J=compiled_j=0、C=24保持不变。95来源进入语义处理，另5来源已由机械链完整处理。

实际按返回身份和档位派出三队，最多11个维护agent，仅第0队发布；第2队零reader由协调者亲读。收尾时16个成功语义批次已处置46个唯一候选，49个仍未完，不把已读未交稿或被stop拦截的冻结稿算作接受。两名作者曾遗漏显式source-version回读所需范围，补齐参数后读取成功；团队usage不可用，未估算token节省。

样本暴露N1实际缺陷：compiler按逻辑ID遍历已接受记录的basis/parent_version，却要求其历史pin等于prepare中的当前版本。两次freeze错误在固定prepare生成时已存在，涉及stale=false且原文未变的记录，不能归为prepare后的并发修改。第一次作者为通过编译额外重写10个section；第二次进一步定位到合法历史父版本，主任务随即停止新发布，保留工件并修复产品。正确合同应沿精确(ID,knowledge_revision)解析保留版本，并独立保留真实current乐观冲突检查及按所选版本的private传播，不为过编译重绑历史。

已stop自有control、确认全部团队结束/中断及publications=[]后release，独立owner=null；一次已冻结source-only批次在提交前被stop明确拒绝，无未知提交。原始停工分区和未发布清单在`tmp/basepack-maintenance/456d252ffd1a41c996756490caf54bf1/a18ef1ecfea344039a86342bb6fc4bc7/`；阶段小型观测在`tmp/20261117-implementation/pilot-1/`。

修复版0.17.1按精确知识版本物化/遍历已接受历史依赖，current expected另保留，缺失版本仍报错，private沿实际版本传播。独立内存库最终publish/proposals 22 passed，此前维护组合70 passed。独立实际样本中4个原件字节未变，旧installed0.17.0精确复现原错；仅替换prepare路径/hash，新源码freeze保留原46成员/10section/1节点/3边语义。prepare约15.498秒、330历史版本、2,303,978字节，freeze约0.015秒；J0/C24/model/owner不变。稳定0.17.1 wheel安装后同一语义稿freeze也通过，无数据库写入。接下来以新control继续原100来源的未完项及修复相关变化，再做实际检索；新库仍18176、正式18080未推广，整体维护未完成。

用户追加要求：结合最近小时Terra/Luna用量图，在之后的实际维护中调查其与此前协调成本问题是否同源；存在需要修复的浪费时继续修复。调查分支以Sol协调、一次跨历史Luna检索及本机统计证据并行进行，按实现/迁移/维护阶段、主任务/协调者/reader和实际input/cached/output拆分，核图表全机范围与聚合口径，再比较既有修复。真实检索的实际交付单独登记，不能将其引起的J/C变化归为维护生成事实；不新增正式监控或benchmark平台。下一轮按两个实际调查agent占用后的raw free=10安排维护，重用原100范围，不重复计已接受的46项。

## 0.17.1实用闭环与0.17.2提示词交付

第二轮固定原100工作集，14机械批次/147复用块后有54语义候选（2新增、52既有变更）。29成功发布完成54/54候选的实际覆盖，0范围外接受；原大聊天1–2272及uv.lock的22个旧范围缺口已闭合，前轮3边/1节点已处理。两次作者合同修稿分别为交hash后原地改稿、file摘要漏末行，程序在提交前拒绝后均以新稿成功接受；一次历史source-version回读漏行界，补界成功。已结束所有团队，stop后publications=[]，release及独立owner=null。

新反馈`feedback:f30ab4e07bff47f99546ee15edc9cedf`记录启动节点两条basis与可回读知识版本的source_version元数据差异；两次原文read均成功，原因未定，不能称原证丢失。另一个duplicate条目消失已核为作者显式列表替换，整个字段省略才沿用旧表；当前fresh member仍覆盖对应范围，不加隐式merge，改为澄清指引。两项沿后续完整维护处理，首100处置不代表全项目完成。

两次真实项目检索分别使J推进至1、2，C由24至26，投影已追到2、模型保持3c69…；第一条为本用量调查实收8项/5624字符，第二条为共享项目另一KL-NMF业务检索7项，全维护树已确认未发起后者。维护接受本身没有制造交付事实，真实业务变化单列，推广前重新取实际事实头。

0.17.2已把现场验证的具体等待/子树调用写入两个协调模板，并明确reader初稿/修稿文件、完整文件行界、历史读取行界及source-decision列表替换语义。普通wheel SHA256为`60af6c2504d85132c4c90b66f651841a532087c015482bdb6a7529362f964c47`；65文件源码/wheel/安装逐字节一致，pip check和installed三角色渲染23项通过。纯prompt/config初轮229 passed/1个既有类型的10秒子进程超时；该项隔离0.23秒通过，project-entry子集9 passed，不把超时根因称已修。新身份不靠现场提醒的行为验证留给后续全项目维护。

用量[调查](research/terra-usage-20261117.md)区分已实现的C1/C2、仍存在的短轮询/全树输出、实现工作和真实语义作者工作；现场修改后的两协调者157次等待均为60秒且可提前唤醒，不外推净收益。另已在统计工具原仓库提交`dcf6669`并普通user-site安装0.2.1，18文件三方一致，124相关回归及两个原入口的去内容真实计数重放通过；原图/全机缓存没有全量重建。

正式推广已完成并经主任务独立核实：18080数据库PID115116、父隐藏launcher48740，store-0.17；旧18174/18176关闭。切换前、后、普通init后与staging配置改指针后事实摘要相同，J=compiled2/C26、模型不变。两个配置均指正式端点；AGENTS托管块外未变。brief、8250/8250向量兼容、图文原文、history/邻接通过，owner=null。根任务另核/ready=200及精确进程/父子/store身份；恢复集合留存，最终恢复点待完整维护后建立。

## 正式端点全项目维护：首个有限阶段

刷新宿主完整项目注册表后，独立collect得到1198路径、105采集缺口、336归属未决聊天；发现仍有41个non_utf8文件缺口。正常用户上下文collect成功不代表受限shell的freshness已修。全项目预检23机械批次复用317块，固定回执有178语义来源、2关系、3反馈。原100样本之外的全授权范围保持，未按当前业务缩窄。

干净0.17.2团队386b582c实际3Terra/8Luna，未接受宿主等待/子树现场提醒。首有限组13份发布结果完成65来源及2关系，113来源留续；两反馈处置、受限入口主报告仍pending。全部启动句柄已结束，owner仍为原run且publications=[]，未stop/release全轮。host固定交接为tmp/20261117-implementation/full-maintenance/stage0-handoff.json，SHA256 ae1052ca59e32d8143426014e36a64ed75cd4e85bb26c4040700f2392dfff2a9；保存逐项部分范围、原错误及未发布稿。

作者误用退休chunk被freeze拒绝，修稿后9源/28成员接受；另一文档组先因局部引用语法拒绝，修复freeze后apply因9项版本变化拒绝，未发布。实际追踪九项均由直接证据的历史parent/basis闭包进入，直接证据、中间section和目标边仍为旧版本且fresh，九个祖先头则已变且fresh。拒绝符合当前对闭包逻辑ID的保守current-head guard；该案例证明跨组重prepare成本，不能证明直接语义冲突或必须重绑历史，也不足以安全移除更正/退役保护。五源及pyproject/uv.lock等未完留干净下一组，当前不改guard。定点路径和观察留closure-conflict-analysis.md/json；不将正常拒绝称修复后的旧compiler缺陷复发。

用量分支另证同版60行原文先在metadata投影的previous嵌套正文出现，随后作为当前正文再次出现，至少6067原文字符重复；未证167节点目录被整批反复输入。0.17.3源通过单一共享prepare-inspection片段收窄输出：元数据字段白名单、正文与metadata分离、核版本及text hash后同文展示一次，必要关系共读/修复回读保留；canonical prepare及其hash完整不改。构建/普通安装验收进行中，下一干净身份检验实际执行，未据字符量推算token、费用或净收益。

0.17.3普通安装完成：wheel SHA216a75ae2275551f1c40a7018662d87c287a6d9a9c5a40d112abdba162eb3394；66包文件源码/wheel/实际site-packages逐字节一致，pip check通过。既有纯prompt130项及project-entry9项通过；closed pilot2渲染49检查通过，三角色共享段完整原文各一次且一致，旧等待/子树/固定稿合同保持。未写DB/owner/control，无需改变共享模型或端点。实际新身份读取行为待后续stage；相同原文展示一次不禁止必要关系共读/修复回读。

## 阶段1实际模型误派与0.17.4修正

新干净stage1的layout与真实render均要求reader为Luna/max，publisher却把四个read_0_*显式spawn为Terra/ultra/forknone，实际turn_context一致，非统计按父模型误记。独立用量分支发现后，root停止新派工/新发布并实际中断剩余作者和非发布协调者；后者已启动两位reader实际Luna/max正确。阶段三份成功发布含27个全文聊天及5文档，其中仅private README本阶段全文阅读，另4文档仅部分新读而保守留remaining；本阶段完成28/留85，原178累计完整93/余85。已接受内容保留，三个未发布稿、逐项范围和错误也固定；全部8启动句柄ended/interrupted、pub=[]。host补actual metadata后固定stage1-handoff.json，SHA c4a453d3f66886cbe61aac4839e04d81c423ab0257e82b1a7a8de4d15def4631。

publisher承认未核reader dispatch参数而误用自身模型；现有代码/渲染字段正确，改为减少手工拆字段：0.17.4的prompt_dispatch新增完整spawn_arguments，含task_name/forknone/本worker自身model和reasoning_effort/message，MAINTENANCE_BOOTSTRAP单一实现源拼同一render_command。两个协调模板和SKILL明确直接采用对象、仅按shell约定替换message来源占位符，不继承自身档位或擅自升级；原descriptor/render_command保留。此对象并非宿主强制模型机制，真实执行仍需核验，不增加常驻监控或DB状态。

wheel SHA49e9884a11f7be85c78d3a41f2c9945144497376ce423cf1ecc7d57dcc9c50a9已普通安装，66源码/wheel/sitepkg逐字节一致、pip check通过。首轮129prompt通过/1旧句断言失败；同步既有两处操作句期待后最终130prompt+9project-entry通过，无新增实现镜像测试。closed receipt三角色及其全部12 descriptor/10唯一task的readyargs/既有规则共142静态检查通过。下一新身份只作8–12来源实际model小批，静态通过不算实际派工已修。阶段1错误四作者实际4.609M总token是工作量账，不能全额算作可避免费用；时间在21:42之后，不能倒推19:05原图原因。

主任务实际收到8项3316字符、privatefalse后确认检索retrieval-09a22255967f4eb59b2c0d9a89bbac6f，J=compiled3/C27、模型不变；这条真实业务事实与维护分开。检索同时核出f30已invalid、原受限入口报告pending及3498duplicate。截止后338c报告经有界只读triage及隔离纯函数检查，只证明检索文本回流可形成不同logical ID与共交付频数风险，没有实库重复/实际自强化/质量损失证据；现有duplicate/no_knowledge可处置确证重复，自动lineage/跨ID合并需具体案例和独立设计判断，维持pending，不改实际数据。

## 阶段2真实小批复验

0.17.4干净stage2启用team0、10路径。四个reader的显式requested及实际turn_context全部Luna/max、forknone，publisher实际Terra/ultra；未在派工前添加宿主model/effort现场提醒。四稿均成功发布且invalidated=0，完成9路径、uv.lock部分范围留续，原178累计完整102/余76。四文档剩余范围已实际处理完；聊天01a1e50e捕获16/221/437处原始截断及其他细化缺口仍保留，不称完整原聊天覆盖。四reader和publisher实际结束、pub[]，全轮owner继续持有。

一处单元素refs经PowerShell转换成对象，publish明确报Completed drafts must be a nonempty ordered list，未产生frozen或未知提交；改为数组后成功，属调用方修正，没有放宽程序契约。结果s2-coordinator-result.json SHA1b09567b0e592072a07d35f68ca631a05c97b0c90db199293cc531e81cf96b22；host确认publisher结束并追加其handle后固定stage2-handoff.json SHAc5d1221991b3684b4de4289dd6313ab2d9e71b2986fffa87fe79fe5f7fd4c9a9。该小批提供真实模型与作者→发布证据，不代表未来硬强制或净费用收益。

## 用户追加有限任务池组织

用户经聊天01a1e9a3明确steering：采用Terra一次规划、Luna自主领取有限语义任务、无活自然退出、最后正常者显式followup原Terra的两段生命周期，替代逐组收发续派。完整合同见maintenance-waves.md。真实小批和全部原维护/验证/恢复继续，不将新小批当全范围完成。

旧stage3依新指令自然收口，68/76来源完成、8留续，原178累计170；12次成功发布、14草稿refs、全部9子句柄及publisher均completed，pub=[]，未stop/release全轮。host追加publisher结束后的stage3-handoff.json SHA1f52b86c5084a147d0dfdaeb38fff6b71deb8ebed7bc7720b1369eb409e6d429；8条实际未完source及范围、原错与原始截断保留。旧同轮source版本记录SHAad38d6226bc7e5b0247c820d0b9601806944b69a7356b7720554147a1c9c5429。0.17.4旧团队不再接新合同；等0.18准备后正确关闭旧owner/control，再fresh受管来源接8未完及新增修订材料。

核心本地state、CLI/模板组织、独立回归、文档及图稿分工，主任务统一检查提交安装。启动屏障选原父实际看到Terra init FINAL后seal及一次go；Luna可等宿主事件，Terra正常无wait/poll。最终publication和通知ack非事务，Terra二段固定发布后直接FINAL，原父核两边宿主终态后机械close。固定frozen与原回执保留，确定拒绝与未知提交分开，旧合同执行入口明确拒绝，DBschema/行为算法不变。

0.18源码程序层已复核：独立18193测试服务上的全memory回归649 passed/6 skipped，1483.62秒，原进程运行至终态，没有失败。6跳过为2项未启用native导出CLI与4项未启用共享模型/恢复模型专项；不冒称本轮重跑GPU和导出验收。首次误指向已关闭旧测试端点的启动尝试已保留并中断，不能当产品失败或本次成功；本次全回归使用全新测试store，与18080正式库隔离。最后幂等返回字段、提示词与config/project-entry定向259项通过，8.91秒；自有native3260/launcher61400独立核身份后停止，18193无监听，正式进程未动。跨模块测试保持真实compiler/freeze/publish与owner边界，仅替换native DB apply；其25项通过不代替真实宿主和SQL接受。普通安装与新宿主闭环仍待完成。

核心实现及现行文档/新图已在main提交a710e335。随后普通打包发现`--wheel`增量构建把build/lib中两份已删除旧reader模板带回候选，候选SHA24516fcda86b88fe413ecec9d5cb6e4c2ad20289005c53947d06fd48bb851944被拦且未安装。保留原候选，改为uv默认先sdist再由它构建wheel，源码/wheel恰为同一69包文件，旧两模板不存在；开发构建入口已同步。最终wheel SHA9ec178d95bfde63550f1696431866efb22cd7c4f9c7d49d2ac7abe70ae19117d已普通安装到稳定客户端，69包文件三方逐字节一致、pip check及wave create help通过，共享服务和正式库未变。新鲜纯文件宿主探针已启动，独立禁用DB端点、无语义稿/交付/发布；其结果待验，不能替代后续真实来源接受。

## 0.18新宿主闭环与真实小批

全新纯文件探针现已结束：同一Terra/ultra真实2个turn，中段329.781秒没有记录到response/tool/usage；两名实际Luna/max处理3个toy任务，早退者领取两个short后结束且0 followup，最后者唯一followup原Terra。最后工具响应为空，Luna保留pending且不重发；原父实际核Terra第二FINAL及全部宿主终态，再notification-recover accepted、close no-publication、stop/release，fixture owner=null。执行结束至Terra第二FINAL尾段51.786秒。Terra自身两次FINAL保留相同context witness；native callback正文加密、支持的read_thread未提供明文，因此不声称已独立排除callback携带该值。早/晚go由原父实际工具参数与唯一native envelope时序联合验证，非解密正文或按等待时长猜测。

探针usage原始last求和与各角色末累计一致，无同累计重复：Terra新增输入24600/缓存416512/输出3602，两Luna合计新增86485/缓存1299456/输出18032。54条usage观测均无原生response/event ID，不能称54次准确AI调用，也不从toy外推净费用收益。Luna侧2次提交错路径及1次未建artifact目录原错保留，正确输入后成功，未修改产品逻辑；首次未派工fixture遗漏固定layout的调用也修正并单独stop/release。完整界限与逐文件保留清单见本机artifacts/runs/20261118-maintenance-waves/hostloop/README.md。

旧386b582c全轮已按stage3固定交接正确stop/release，owner曾确认null；新鲜受管原件小批取得f62385f3自有owner，仅取旧余8来源，不冒充聊天新采集。8来源规划为7任务、固定2Luna池；首turn已FINAL，原父核两个reader requested=actualLuna/max、coordinator actualTerra/ultra后seal并各发一次go，真实作者/发布尚在执行。其余新增修订材料留后续全项目维护。普通memory init已刷新0.18受管入口，AGENTS块外原字节保留，前后真实交付与行为metadata完全一致。

该真实波现已发布batch ab601e52f78a484780dea6d079e37d71，仅接受2来源/7成员；主任务从正式库逐项精确回读显式值、原文行字节、来源版本、历史头及当前embedding metadata，全部匹配，真实交付头未变。两Luna完成7任务/8来源，多轮间submit→下一claim为5.902–6.972秒；Terra真实2turn，中段1759.193秒无记录到response/tool/usage，执行结束至FINAL尾段87.430秒。148条usage观测无原生response ID（含1条零增量compaction），准确模型调用数unknown；本机原证和逐角色新输入/缓存/输出见artifacts/runs/20261118-maintenance-waves/real-small-1。20次非零command均归Luna A：17次Python残留PY终止符NameError，其余为通配路径、未交当前任务就claim、错误task-id各一次；B和Terra未见非零命令。最终errors=[]不能证明运行中无失败，原错误已按native command索引保留。

实用验收同时发现语义处置未闭合：6个无稿来源虽由作者判已有表示足够，却仍有37条fresh member coverage_gaps没有绑定deferred_refinement；两份已发布来源另有7条，合计8来源/9成员/44条。元数据和原件SHA核对全相同，缺口多为截断、缺失上下文及未知外部结果，不能批量宣布解决。wave coverage是运行回执，不能替代知识中的持久化决定。父任务在实际核全部宿主终态后恢复未知通知结果并close（closure SHA5c44a11cce45df9bb48e0ab46c50541963f76e00c3cf7ebdb35d2eaebd540ae2），随后正确stop/release；已发布内容保留，全部8来源留修复复验，不能据submitted或旧170/178作者计数宣布完整语义维护完成。

0.18.1只补4份SKILL/角色指引：确已读、fresh粗层覆盖且符合现合同的gap须以source-only deferred_refinement提案持久化，精确绑定成员/知识版本/gap；保留未知，未读或无合格粗层覆盖的内容继续remaining。同批改成员先经publisher接受，后波才可暂缓其新版本；不增加例行全文审计。补PowerShell多行Python写.py及真实错误/处理状态留痕，提交后新错另留引用，不改固定文件。后端、schema、Gaussian及真实交付规则不变。136项提示词检查通过；普通wheel cf8f36029941925d0fa22328810bf5c8d96196ebf18f08243c189d90cd2a7047与源码/site-packages恰为同69文件且字节一致，pip check通过。

新鲜418a9020复验的实际预检仍为8 semantic且8条raw revision全不变，实证了重复入队；旧074c（0.17.2全项目）与b870（0.18.0小批）候选中这8条也已存在且current raw revision一致，不能把现象归为0.18队列新引入，但其对19:05原用量图的贡献未量化。新波85a00f63d6ec49bc9fd0ddb318364ed1仍为7任务/2Luna，原父确认首turn结束并核模型后seal/go；接下来以持久化结果、未知仍保留以及同材料是否再次入队验收，不只看发布成功。原其余新修订全项目维护、真实行为训练及完整恢复仍继续。

## 不可得证据与细化暂缓的实用修正

0.18.1同批执行揭示合同缺口：一名作者把未知上下文/截断结果归为细化暂缓，另一名实际读完两个资源聊天后指出，缺失原文和未确认结果不能声称已经读过。R9粗层还存在raw相同但source_version历史pin不同的合法情况，不能为方便绑定而重写provenance。原父据此停止85a波，实际coordinator只完成初始化、r0正常结束、r1中断，publications=[]且未发布；未发关系稿与20个固定引用保留，未伪造剩余任务完成。父终态证据在本机`tmp/20261117-implementation/wave-gap-repair-1/parent-terminal.json`，SHA256为`04f8260c50e86336d75a0493335f6593501623f58e748532e2e477f47897c563`；原owner暂以stopped状态保护恢复，准备新版后再正确释放。

0.18.2因此增加独立source版本字段`unavailable_gaps=[{member,knowledge_revision,gap,reason}]`。作者逐条核实当前不可得条件，编译及原生提交均检查当前fresh、未退役、同path/raw的精确成员版本和现存gap，不替换为新版本；只消除同输入下匹配gap造成的重复维护，原缺口、正文、read/covered范围、历史pin、mandatory/private、向量与交付事实不变。同版本省略保留、显式list替换/[]清空，新raw不继承。其他维护理由不被遮蔽；外部证据恢复但版本未变时需feedback或明确重新判断。public来源不能保存private成员派生记录，private转public的非空继承会留语义复核，其余安全来源仍可机械处理。没有批量为44条缺口自动背书，没有新增遗忘/退役或审阅平台。

隔离18193原生DB的23项新增行为回归通过（主22项199.52秒，strict fresh另10.12秒，真实旧fixture替换后的兼容项5.72秒）；既有prompt/proposal143项、reviewed/maintenance7项通过。另由普通site-packages0.18.1实际prepare→compile→freeze→native发布的两份旧稿，在新代码先接受不可得记录后原样重放成功：旧文件SHA、canonical batch hash和DB receipt hash不变，新记录未被抹除，成员及交付头不变。仅embedding模拟，不以新代码造的“旧稿”冒充跨版本。完整memory、新安装及真实同批复验仍待完成。

0.18.2随后已默认sdist→wheel构建并普通安装，wheel SHA256 `a32196c33e320dcae9a5beed9ee1dc932e87f83ce46bcea204f7133cf93b60c5`，69文件集/字节三方一致、pip check通过。ba3e866e新鲜同8来源仍待处理，7任务/2reader初始化后尚未seal/go；独立最终审查发现legacy frozen可伪造item.private使私有gap写入实际公开快照。原父在任何claim/读取/发布前stop，两reader实际interrupted，coordinator仅init FINAL，publications=[]。父终态证据SHA256 `11874351d3140a91d8ec5c111f171ecf74b288d3d219b5185656daac8ca4b0a3`，位于本机wave-gap-repair-2/parent-terminal.json。已启动的完整memory在21%进度按主任务要求中断，保留原log且没有最终summary，不计成功或产品失败。

0.18.3源码修正隐私准入的实际来源：reviewed按source.path和当前配置privacy_rules计算marker，不再信legacy batch自带private。modern既有冻结规则检查、旧batch的hash/receipt及幂等返回顺序保持。143项prompt/proposal通过，新增legacy伪marker原生回归、重打包和完整回归待续；无必要调整行为算法或迁移数据。

新增2项legacy隐私回归首次都在fixture install_schema HTTP30秒timeout，测试体未执行，真实portable旧稿1项通过。独立核自有测试服务发现Surreal后台node registration反复Transaction write conflict及60秒timeout；health仍200，无残留pytest或已建立连接。只证明隔离服务异常，不证明根因或产品失败；保留全部原证后核身份停止旧48040/74424，不复用其store。全新attempt4/18194的86520/96416经下一次工具独立核PID/exe/cwd/参数/store/监听及health，再运行新增2例及旧portable，3 passed/23.86秒。未改产品超时或盲重试，正式库与共享设施未动。

0.18.3已默认sdist→wheel普通构建安装，SHA256 `21ebcb39bb3cf1fd366431075a56951ab080d08997f6d48c173686a0b38a9cbf`；69文件集/字节source=wheel=site-packages、pip check通过。独立全memory在新attempt4串行运行；生产新鲜81cb6715同8来源预检取得自有owner，真实作者小批重新启动，后续全范围/真实行为训练/完整恢复继续。修复前两次停止波的原件及未发稿均保留，未伪造发布或task终态。

最终全memory首轮实际为666 passed、6 skipped、8 setup errors，2646.34秒，0 assertion failures；新unavailable组25/25通过。8个错误均在fixture install_schema的HTTP30秒超时（5个namespace/db/meta初始化、3个BEGIN+schema），业务body未执行。原实例只读INFO当时该NS含194DB，计数不是原因证明；官方4.0源码显示heartbeat失败后继续调度，日志“60s”标签不等于实际阻塞60秒，health200不核DDL，当前没有证据将后台警告与setup超时连成因果。保留首轮全部log/XML及逐case原trace后，核停原实例、以fresh attempt5/18195同源码/默认timeout仅补验8个精确case，8 passed/54.06秒。首轮仍非green，根因未修；666与8分别报告，不合并伪称一次全过。所有自有测试native/launcher已独立核停，18193/94/95无监听，正式库/共享设施未动。本机整合原证在`tmp/wave-tests/integration-0183-result.md`及同名JSON。

真实小批的首个e3bc来源已提交source-only unavailable，保留原gap和成员；针对性核其理由，明确区分原capture截断字节与后来查到的Git/维护结果。该样本只核新合同，不增加整波逐稿语义复审。related_resources则发现TTS成员三条“终态未知”可由六份本项目原生日志补证；原8来源scope不能新增这些来源，作者正确failed留续，R9的13条valid unavailable草稿随回执保留但尚未发布。当前关系已明确共享历史背景和授权边界，作者判断不需应用旧未发关系稿，所有历史endpoint pin保持。

为后续正常修复波新增[六个历史作业终态核验](research/job-terminals-20261118.md)：直接核6份events.log的字节/SHA及终态行，仅确认退出码/aborted，保留cleanup和原capture缺口未知，未操作旧作业。完整9595字节原件副本、原路径映射和manifest放独立private Git，提交`0605a2e0fec2abea0b2cbb827dccb79e2c08abf8`；6份.log按binary存档，Git暂存字节与原件逐一相同。公开分析只含可公开事实，无本机标识或完整日志；原件可选，public保持自足。新证据接受、TTS成员修正、其新KV的缺口重判及其余全项目范围仍待后续波，不将源外原件直接塞进当前任务或把可恢复内容统一标成不可得。
