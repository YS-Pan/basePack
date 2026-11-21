# 系统实现概览

唯一active路线是[20261106-basepack](../../experiments/20261106-basepack/README.md)。本页描述0.18系列实现；实际安装版本、wheel和验收状态以[部署合同](deployment.md)为唯一维护源，当前维护范围与余项沿[进度](../tasks/20261115-real-use-rectification/progress.md)。0.16既有验收见[整改结果](../tasks/20261115-real-use-rectification/result.md)。代码、依赖锁、测试、产品文档、示例和随包skill位于实验工程；根devDoc维护现行实现和活动工作。实测边界见[环境记录](environment.md)，共享资源基线见[R9结果](../archive/20261107-resource-coordination/r9-result.md)。

本仓库提供三项可独立使用的 skill：[engineering-judgment](../../skills/engineering-judgment/SKILL.md) 用于设计、错误处理、兼容和使用流程的工程取舍，保留独立形态，通过长期使用反馈维护；[file-structure](../../skills/file-structure/SKILL.md) 推荐或整理开发文档、实验工程及私有开发上下文布局；[agent-team](../../skills/agent-team/SKILL.md) 为每项任务选择组织，按完整交付过程判断独立完成、简单协作或清晰分层，并使用宿主已有的订阅 subagent 能力。安装时选择完整目录放入目标 `.agents/skills/`，或把已有项目原件联接到该发现目录，核对相对引用与宿主实际列表；`init` 与 core doctor 不覆盖这项验收。完整步骤见 [项目接入](../../experiments/20261106-basepack/docs/setup-project.md#独立-skills-安装与发现)。组织选择与协作已有指令层实现，复杂广读的质量与总成本对照仍见 [专项记录](../tasks/20261106-rebuild/research/agent-team.md)。

`basepack` 的公共入口包括项目 `init`、`config show`、`config ai`、`doctor`，项目 `memory`，共享图文 `embed` 及普通重任务 `jobs`。项目接入源码和模板统一在 [project/](../../experiments/20261106-basepack/src/basepack/project)，[config.py](../../experiments/20261106-basepack/src/basepack/project/config.py) 唯一解析配置。`config ai` 按项目配置解析 AI 档位、模型及推理强度，供宿主实际派工。日常默认 3 档，检索、筛选和重排序默认 1 档。配置和命令见 [项目接入](../../experiments/20261106-basepack/docs/setup-project.md#ai-档位)。项目使用 schema 2 的 `.basepack/config.toml` 和 `.basepack/instructions.md`，根 AGENTS 直接呈现关键动作及详情链接。机器格式为 schema 1，旧格式迁移及 embedding 服务见 [部署合同](deployment.md)。

[项目记忆](modules/memory.md) 使用唯一 SurrealDB 基座。一个 member 同时表示文件、实际章节、智能原文块或图片，也是默认检索表示及图节点；另有实体/决定/条件节点和带依据的原生语义边。宿主订阅 agent 同读完成分块、摘要、识图与关系，程序核源与逐记录知识版本后原子接受。多层全文、图文向量、严格回源、语义展开、人工更正及原生恢复共用这份持久知识。

根`private/`是公共Git忽略的独立本机仓库，容纳隐私、机密及因版权/许可需限制分发的资料；公共开发说明继续自足。默认来源发现自动加入其内层Git清单；`memory.private_scope`可额外声明原位私有文件／目录，分类不扩大来源发现或控制Git发行。freeze固定归一规则及分类，新source_version纳入分类与规则版本，apply在编码前及提交前核规则，历史依据保持原分类。私有资料进入原项目记忆，`private`标记沿固定版本依据和关系端点传播并随检索/回读交付。存量补标保留知识身份与未变向量，无法确认的旧记录留未知。受管记忆与工作包沿现有忽略目录保留，完整恢复仍需数据库导出和相应文件；标记及原生导出不构成公开分享副本。详见[记忆模块](modules/memory.md)与[本机目录](project-data-layout.md)。

作者提案引用固定prepare文件的path/file_sha256。程序从prepare编译来源版本、UUID、expected、依据闭包与private，解析草稿局部位置引用；可选historical-versions明确固定历史端点。冻结批次重试复用相同身份，apply沿用原原子接受链。0.17严格核memory schema 3、member identity 2；新库init写入标记，已绑定旧库须经离线桥verify/finalize后才能用新版init，普通init不替代迁移或重置J。存量按项目停写、备份、隔离转换和验证后同步切换，保留原文、向量、知识历史及真实交付事实，行为投影可重建。

`memory publish` CLI与Python helper共用完成稿hash核对、freeze/validate、固定稿保存和原apply这一条组合链；数据库batch receipt仍是权威，本地result为详细投影。固定稿接续保持原batch_id与UUID，真实修稿才生成新path/hash后重新freeze。其余准备和条件组合沿既有原子工具／普通Python，合组、拆组、共读与返工仍由agent判断，宿主负责实际派工及生命周期；见[发布合同](../../experiments/20261106-basepack/docs/memory.md#最小闭环示例)。

memory init绑定原UUID并刷新AGENTS和本机入口。主任务预计约十分钟以内保留brief并跳过自动维护；长任务经`maintain-start`实际派出唯一协调者并继续业务。协调者首turn独立采集或选择现有来源，再用原父holder/control申领owner并预检。有语义任务时，同一协调者初始化有限reader池，原父核协调者空闲后封口并发送go。最后正常退队者恢复同一协调者，第二turn编译并唯一发布。容量保留协调者恢复席。父任务可在采集和审批期间取消尝试，结束时核宿主及发布终态后释放自有owner。默认全项目接续，显式scope限制维护工作集。详见[记忆模块](modules/memory.md)。

CLI检索默认读memory.search_mode，新项目为vector；hybrid/vector按相同语义身份查询，缺模型或兼容向量明确失败。CLI和Python返回`{matches, vector_coverage}`；采集、语义接受与向量覆盖分别报告，结果保留观察knowledge_revision供反馈。独立检索由[retrieval.py](../../experiments/20261106-basepack/src/basepack/memory/retrieval.py)统一请求、工作目录与派工身份，每个请求加slot区分worker；零席位由主agent执行完整流程，不要求维护owner。guide/rank不需配置；owner/stop/release/recover-owner不连库；memory prompt渲染唯一协调者；memory wave worker-prompt/task-prompt只读本地wave与固定任务，检索渲染只读配置和请求，均不连库或模型。doctor默认core，模型及Condor显式选查。

brief每任务读取mandatory、跨来源摘要/图节点地图、未映射或未读入口及缺口，不执行检索/embedding，也不按新shell重复。非mandatory地图从有界结构样本计算Gaussian访问区间，组内按区间优先、跨组交错；UTC日仅轮换展示样本，不改变访问事实或年龄，低权重仍可被基础检索找到。`memory retrieve --question`准备默认全项目/6000字请求；worker运行retrieval-start固定独立基础锚点和行为候选，再回源并一次综合评分，rank仅排序/去重/预算。retrieval-receipt从实际候选数组和rank结果形成待确认清单，主agent收到内容后执行delivery。精确知识历史与图端点共用`id + knowledge_revision`，原证另有版本。首次确认（包括空清单）推进严格事实J，只有非空交付推进机会C，重试均不推进。

行为表示只从共同交付逻辑ID学习无正则KL-NMF；默认rank=8、epsilon=0.001、beta=0.2、strength=8是工程初值。固定模型文件位于memory_dir/behavior/<sha256>.json。访问年龄逐原始锚点求Gaussian后加权，以H/R和精确版本标量基准增量编译；未知锚点份额保留为区间，重训重放原始事实后原子切换。读API不补写投影，返回事实/编译截点及未知状态。低权重不删除或排除原文、图、向量和训练ID，mandatory独立保留；数值工件仍属项目受限材料。数值训练使用可选behavior extra，基础采集、发布和检索不依赖训练成功。关系和条件仍由维护作者接受，没有独立当前理解同步层。

项目现状、余项与历史要求触发同一 worker 完整检索。`memory check-codex-capture` 核对聊天采集覆盖，`memory check-file-changes` 核对已登记来源的文件差异。检索 worker 补读相关新原证并说明采集截止、待语义范围及未核状态。安装升级由独立 [basepack-setup](../../experiments/20261106-basepack/skills/basepack-setup/SKILL.md) 指向操作文档，日常使用和维护沿随包 memory skill。

Codex 宿主自动提供项目绑定和完整注册根，线程明确 projectId 优先，字段缺失时按 root/worktree/common-dir 与其它注册项目根排除冲突；无法取证留覆盖缺口，非 Codex 保持文件功能。每聊天导出留在项目 memory 目录并沿原生 source_version 保存，精确回读提供消息身份与正文字节范围。宿主字段、附件及完整分叉/继承范围的实际验收边界见 [本轮进度](../archive/20261110-onboarding-simplification/progress.md)。

机器级 embedding 由 Sentence Transformers 编码，LitServe 管理请求与单个推理 worker。设备默认优先 CUDA，否则 CPU。每项输入按含模板、指令及图片的实际 token 核对 32768 上限。CUDA 服务空闲 60 秒时释放可回收的缓存，Windows 用户任务空闲 30 分钟时正常退出。后续请求按需启动同一模型，继续使用兼容索引。客户端等待结束后，服务端继续处理已接收的预测。配置与生命周期见 [资源模块](modules/resources.md)，实际服务部署状态见 [部署合同](deployment.md)。

普通CPU/GPU作业由CondorClient提交至HTCondor；容量、队列、限时策略、终态和GPU站点策略由Condor维护。basePack保留JSON参数传递、退出码与不确定提交查询恢复，删除额外PID确认和客户端重复作业计时；等待到期只返回observation_expired，不自动取消。共享模型服务位于Condor作业树之外，通过管理员固定背景预留与普通作业并存。项目知识、来源和工具产物属于各自项目，通用模型和机器环境可显式共用。配置、安装和运行目录见[部署合同](deployment.md)。

0.8.1 保留数据库认证与显式回环 IP。配置维护 username 与可选 password_file，默认文件为实际 memory_dir/password.txt；客户端和 launcher 读取同一文件，config show 只显示解析路径。文件缺失、权限或认证错误直接失败；已有库恢复原凭据，不随机换密码。UUID 只防误连，账户密码负责认证。

每项目数据库使用该项目内独立物理目录及进程，多聊天共享；通用 exe 和 embedding 服务可跨项目共用。项目 UUID 核查防止误连，原生导出连同原件、必要 assets 与配置构成恢复集合。旧项目仅作参考，不承接其数据库或验收，依据见 [调研索引](../tasks/20261106-rebuild/research/sources.md)。

按文件位置理解源码、安装、业务实例与共享设施时读 [逻辑框图](diagrams.md)。跨模块修改读 [架构说明](architecture.md)，准备运行或诊断读 [环境说明](environment.md)，概念歧义查 [项目术语](../terminology.md)。跨工具状态见 [重建总进度](../tasks/20261106-rebuild/progress.md)。

本项目的[持续整改索引](../tasks/ongoing/README.md)仅服务本仓库正常任务，按有限期限选择主题并在发现到期时整目录归档；期限及记录规则由[文档约定](../documentation.md#持续整改)维护。它属于项目开发文档，不进入通用skill或业务项目接入合同。
