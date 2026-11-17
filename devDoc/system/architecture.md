# 系统结构与边界

当前唯一active路线为[20261106-basepack](../../experiments/20261106-basepack/README.md)。本页描述0.18.0源码；2026-11-18核对，稳定客户端已普通安装0.18.0[behavior]，新有限wave宿主probe进行中、闭环待验；新库store-0.17已推广至正式18080，实际部署与维护边界见[部署说明](deployment.md)和[实施记录](../tasks/20261115-real-use-rectification/execution.md)。0.16既有验收见[整改结果](../tasks/20261115-real-use-rectification/result.md)和[维护实测](../tasks/20261115-real-use-rectification/maintenance-20261116-result.md)。[逻辑图](diagrams.md)标明各图版本；设计依据与尚待真实使用验证的目标见[目标架构](../tasks/20261115-real-use-rectification/target-architecture.md)。

## 当前组成

```text
AGENTS.md                         项目规则和阅读导航
README.md                         项目目标、active 路线和路线索引
skills/file-structure/            文件结构 skill 与按需参考
skills/agent-team/                使用宿主 subagent 的分层协作 skill
skills/engineering-judgment/      工程取舍 skill 与按需案例
experiments/20261106-basepack/
  README.md                       路线和产品入口
  pyproject.toml、uv.lock          原生依赖声明、CUDA 来源和锁
  src/basepack/
    project/                      唯一配置解析、init/doctor 及模板
    memory/                       来源、原生领域事务、图文向量、检索交付与随包 skill
    embedding/                    ST 模型适配、LitServe 服务、HTTP 客户端与管理
    jobs/                         CondorClient、提交材料与 UTF-8 worker
  tests/                          回归与夹具
  docs/                           用户与管理员说明
  examples/                       小样例和 Condor 配置维护源
  skills/resources/               共享 embedding 和重任务入口
  skills/basepack-setup/          安装、升级与接入的薄路由 skill
  dist/                           交付和回滚 wheel，Git 忽略
devDoc/                           根目录唯一开发文档树
  system/                         当前实现、部署和环境说明
  tasks/                          活动计划、调查、进度与结果
  archive/                        已结束任务材料，始终存在、允许为空
  change_log/                     已发生变化的按次记录
tmp/                              可清除的一次性工作区，Git 忽略
artifacts/runs/                    选留运行和迁移原证，Git 忽略
```

根 AGENTS 按问题引导至系统说明或任务入口；详细依赖和产品操作随路线维护，计划、进度和结论集中在根 devDoc。实验路线短期比较后收敛 active，需要长期独立演进时分为多个 project。

## 所有权与边界

- 本仓库维护目标和开发文档；纲领正文按用户同意修改，原始快照保留原文。调查和历史验收各有条件，旧项目不提供本项目的运行状态或验收结论。
- `file-structure`、`agent-team`、`engineering-judgment` 是可独立交付的通用技能。实际 agent 派发、权限和模型能力由宿主提供。安装保留完整目录或项目内原件的发现联接，验收宿主实际项目列表；init/doctor 的成功不代替技能发现。
- 产品代码、模板和资源 skill 各有一个维护源。运行代码通过普通 wheel 安装；业务项目只保存自己的接入配置、数据和产物。
- 项目显式指定 schema 2 接入配置，绑定运行 Python 和 schema 1 机器配置。project.root 相对项目配置，受管理数据进入该业务项目 `.basepack/`；机器相对路径以机器配置为基准。ProjectConfig 只解析公共绑定，各功能按需读取自身节；memory guide/rank在项目解析前处理自身输入；owner/stop/release/recover-owner需配置定位状态但不读凭据或连库。
- 项目 `[ai]` 配置维护 tier1 至 tier4 的模型和推理强度及用途默认值；`config ai` 输出所选配置，宿主负责把 model 和 reasoning_effort 传入派工接口，程序不调用模型。
- `init`从安装包模板生成配置和详细instructions，根AGENTS合并关键动作及详情链接；memory init绑定原UUID并刷新AGENTS和本机入口，保留托管块外字节。新库设置memory_schema_version=3，已绑定且缺失或不符的库须离线迁移，普通init明确拒绝；迁移finalize核等价后显式交接标记，新版init保留既有J。项目配置仍读schema 2；更旧配置先按历史迁移入口处理。
- memory endpoint 在唯一配置边界只接受 HTTP(S) 显式回环 IP；数据库保留认证。客户端与 launcher 按配置读取唯一 password_file（默认 memory_dir/password.txt）及 username，config show 只显示路径。缺失/权限/认证错误直接失败；项目UUID防误连。升级保留项目身份与凭据，0.13的成员身份变化先离线迁库再同步切换客户端。
- 项目记忆只用 SurrealDB。member 同时是层级、检索表示与图节点；source_version、change 和必要图像 assets 保存原文依据及更正。source revision、input_revision、knowledge_revision 与 embedding_identity 各管来源、编码输入、并发更正和语义空间。原生WebSocket事务按完整语句透明分消息、原子接受，原生 CLI 负责服务、导出与恢复；没有多后端层或自建 MCP。
- member身份统一为程序分配的UUID。作者提案引用固定prepare的path/file_sha256，写语义内容及草稿局部引用；编译器从prepare取得来源版本、已有身份、expected、依据闭包与private，再freeze唯一批次。历史端点可经prepare的historical-versions显式pin。apply仍负责原子接受、冲突和同稿幂等，不另建发布事务或作者状态库；存量转换工具属于离线恢复材料。
- 结构解析只供定位。独立`memory collect`保全原件并记录采集观察；绑定Codex的`memory maintain`明确消费`--collection`或`--retained`，随后以自有holder/control原子取得单owner。显式scope限制实际来源工作集，默认全项目接续。采集回执加载核hash，prepare另固定本批实际版本；跨阶段不是全库不可变快照。机械等价小批与待语义范围分别报告。智能块、摘要、识图和关系由宿主订阅agent同读生成，程序核版本并原子发布内容及所需向量；普通批次成功接受即结束。0.18以有限本地任务池保存独立语义任务及固定worker，按工作量选较小Luna池并保留Terra恢复名额。Terra首turn规划后结束，父任务核空闲再seal/go；Luna循环原子领取与提交，最后正常退队者实际恢复同Terra，第二turn编译并唯一发布。父任务核通知ack/宿主终态后关闭wave，正常不逐稿全文复读或额外审计；旧逐组续派不再是默认组织。宿主stop自有control、取消自有后代、确认发布结束后release，未知发布保留owner。反馈和已读处置沿原职责保留，仅显式审计意图启动审计。详细合同见[记忆模块](modules/memory.md)。
- Codex来源适配仅通过受支持的App Server读取持久化消息；宿主提供当前项目绑定及完整注册根，以projectId优先、root/worktree与其它注册项目根排冲突。collect不持维护owner，失败保留原错与独立回执；retained明确表示已有原件，freshness未知。受管导出进入source_version/prepare/apply，来源发现、采集、语义接受与向量覆盖各自可见；能力缺失或归属不明保留缺口，非Codex继续文件功能。
- 项目现状及历史决定由同一检索worker核已有知识和必要新聊天。只读freshness脚本返回新增、可能变化、实际正文已覆盖和未知清单；端点或更新时间不证明正文一致。worker选择相关原证补读，明确采集与语义边界，不取得维护owner或发布知识。触发仍由宿主agent遵循指令。
- 默认查询从全部粒度取得全文及兼容向量候选，按配置的vector/hybrid查询；retrieval.py唯一维护请求与派工身份。retrieval-start固定基础锚点、知识观察和行为候选，同请求各轮共用，worker核原文及图后一次综合评分；selection仅排序、去重、预算。retrieval-receipt保存实际候选与交付版本，主agent实收后确认delivery。零席位由主agent执行同一完整流程，查询不需维护owner。brief独立交付mandatory，非mandatory地图在有界结构样本中精算Gaussian访问区间后组内排序、跨组交错，交付模型/游标/区间及遗漏边界。UTC日仅轮换展示采样，不改J/C/hits或年龄；低权重无硬过滤。概要与投影读取仍有实际成本，这不是常数成本或完整语义覆盖承诺。
- 交付事实与行为投影分开：稳定delivery_id首次确认（含空清单）推进J，非空才推进C，技术重试两者均不推进。严格context保留独立原始锚点/份额/基础质量、知识截点、query/episode、实际候选/预算、策略与模型；精确版本命中不奖励新版或传播到邻居。纯共交付ID经KL-NMF形成固定非负行为向量，逐anchor Gaussian机会年龄以H/R及每版本标量基准编译，重训全史重放后原子切换。读API仅报告模型、事实头和编译截点，不隐式训练/补写。缺失证据保留区间，低权重保持原文、图、向量、训练ID及基础检索资格。
- embedding 的编码由 Sentence Transformers 负责；薄 LitAPI 在 setup 加载模型、predict 编码，LitServe 管理 HTTP、队列和单推理 worker，Shawl 的 Job Object 拥有 Windows 服务进程树。服务位于 Condor 作业树之外，多项目通过同一 endpoint 共用模型。CPU/CUDA 按相同语义合同编码，设备自动选择不改变身份。向量语义身份独立于 HTTP 等待和服务部署，见 [资源模块](modules/resources.md)。
- 普通任务的进程树、限时策略、容量、队列和站点GPU策略归Condor；basePack保留参数封装和不确定提交查询恢复，按原生queue/history/事件观察结果。调用者等待到期不取消作业，取消请求与终态分别报告；不另核OS进程族。背景服务与普通作业的额度由管理员预留协调。
- 后续路线复用明确版本的发行包或公开 HTTP/API；模型、环境和缓存可以显式共享，项目知识和试验状态分别保存。运行环境不依赖另一条路线的可变源码或临时工作区。

数据库物理文件与图像快照属于业务项目；每项目独立进程/端口，多聊天共享。源码外普通安装和机器观测见 [环境说明](environment.md)；文件结构建议、宿主协作与项目知识分别由对应模块维护。

知识版本、交付事实和行为投影的权威元数据仍在同一项目SurrealDB。知识首次接受保存真实事实头，h=0先验不冒充命中；旧版无法证明的接受截点保持未知，只记录迁移观察起点。模型数值工件按hash保存在项目memory_dir/behavior，连同原始事实参与恢复，仍受项目限制分发边界约束。宿主负责实际派工、接收和确认；渲染、search、read、neighbors及rank只读已发布内容，不构成交付或推进投影。默认rank/epsilon/beta/strength是实现初值，长期检索收益和规模性能以真实使用反馈判断。
