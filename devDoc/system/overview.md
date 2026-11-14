# 系统实现概览

唯一active路线是[20261106-basepack](../../experiments/20261106-basepack/README.md)，源码面向0.14.0；本轮私有开发上下文、同库标记与实际安装/验证状态见[本轮进度](../tasks/20261114-next-maintenance/progress.md)，此前统一身份与资源收敛见[交付进度](../tasks/20261114-delivery-closeout/progress.md)，知识历史与访问状态见[使用整改进度](../tasks/20261112-usage-rectification/progress.md)。代码、依赖锁、测试、产品文档、示例和随包skill位于实验工程；根devDoc维护现行实现和活动工作。实测和历史边界见[环境记录](environment.md)，共享资源基线见[R9结果](../archive/20261107-resource-coordination/r9-result.md)。

本仓库提供三项可独立使用的 skill：[engineering-judgment](../../skills/engineering-judgment/SKILL.md) 用于设计、错误处理、兼容和使用流程的工程取舍，保留独立形态，通过长期使用反馈维护；[file-structure](../../skills/file-structure/SKILL.md) 推荐或整理开发文档、实验工程及私有开发上下文布局；[agent-team](../../skills/agent-team/SKILL.md) 为每项任务选择组织，按完整交付过程判断独立完成、简单协作或清晰分层，并使用宿主已有的订阅 subagent 能力。安装时选择完整目录放入目标 `.agents/skills/`，或把已有项目原件联接到该发现目录，核对相对引用与宿主实际列表；`init` 与 core doctor 不覆盖这项验收。完整步骤见 [项目接入](../../experiments/20261106-basepack/docs/setup-project.md#独立-skills-安装与发现)。组织选择与协作已有指令层实现，复杂广读的质量与总成本对照仍见 [专项记录](../tasks/20261106-rebuild/research/agent-team.md)。

`basepack` 的公共入口包括项目 `init`、`config show`、`config ai`、`doctor`，项目 `memory`，共享图文 `embed` 及普通重任务 `jobs`。项目接入源码和模板统一在 [project/](../../experiments/20261106-basepack/src/basepack/project)，[config.py](../../experiments/20261106-basepack/src/basepack/project/config.py) 唯一解析配置。`config ai` 按项目配置解析 tier 对应的模型与推理强度；宿主读取结果并在派工时实际传递，程序不自行调用模型。日常默认 tier3，检索、筛选和重排序默认 tier1；配置和命令见 [项目接入](../../experiments/20261106-basepack/docs/setup-project.md#agent-模型等级)。项目使用 schema 2 的 `.basepack/config.toml` 和 `.basepack/instructions.md`，根 AGENTS 直接呈现关键动作及详情链接；机器格式保持 schema 1，旧项目需补入 AI 配置。客户端兼容 0.5.0 embedding 服务，部署与旧格式迁移见 [部署合同](deployment.md)。

[项目记忆](modules/memory.md) 使用唯一 SurrealDB 基座。一个 member 同时表示文件、实际章节、智能原文块或图片，也是默认检索表示及图节点；另有实体/决定/条件节点和带依据的原生语义边。宿主订阅 agent 同读完成分块、摘要、识图与关系，程序核源与逐记录知识版本后原子接受。多层全文、图文向量、严格回源、语义展开、人工更正及原生恢复共用这份持久知识。

根`private/`是公共Git忽略的独立本机仓库，机密原件和人工分析按内容归入；公共开发说明继续自足。默认来源发现自动加入其内层Git清单，私有资料进入原项目记忆，`private`标记沿固定版本依据和关系端点传播并随检索/回读交付。存量补标保留知识身份与未变向量，无法确认的旧记录留未知。受管记忆与工作包沿现有忽略目录保留，完整恢复仍需数据库导出和相应文件；标记及原生导出不构成公开分享副本。详见[记忆模块](modules/memory.md)与[本机目录](project-data-layout.md)。

member新建由freeze分配UUID并解析草稿局部位置引用，更新沿用prepare中的UUID与expected；冻结批次重试复用相同身份，apply只接受新协议。未迁移库明确拒绝，不自动转换或解析旧别名。存量按项目停写、备份、离线转换与验证后同步切换，原文/向量/知识版本及交付访问状态保留。

memory init绑定原UUID并刷新AGENTS关键动作与本机详细入口，固定Python、显式配置和原凭据文件。主任务直觉预计约十分钟以内跳过整个自动维护，保留brief；长任务以全项目maintain取得单owner并行业务。容量快照由安装agent采集，脚本按模式及可得空闲额度固定本轮布局与名称：自动仅0队，手动满队，低并发coord亲读，仅coord_0发布。其它聊天继续业务，反馈加入下轮派工。普通批次作者生成并由程序提交即完成，默认不追加审计；显式审计另按授权。发布采用原生WebSocket事务透明分消息，保留依赖版本、原文和向量保护。结束stop、取消后代，确认发布结束才release；未知结果保留owner。详见[记忆模块](modules/memory.md)。

CLI检索默认读memory.search_mode，新项目为vector；hybrid/vector按相同语义身份查询，缺模型或兼容向量明确失败。CLI和Python返回`{matches, vector_coverage}`；采集、语义接受与向量覆盖分别报告，结果保留观察knowledge_revision供反馈。检索派工独立使用retrieval-dispatch/retrieval-prompt，名称bp_mem_search_s，零席位由主agent直接执行；不要求维护回执或owner。guide/rank不需配置；owner/stop/release/recover-owner不连库；prompt、pending-dispatch及检索渲染只读配置和各自输入。doctor默认core，模型及Condor显式选查。

brief 每任务直接读取已发布必保留、已有摘要索引和缺口，不执行检索/embedding，也不按新 shell 重复。`memory retrieve --question` 准备默认全项目/6000字请求，宿主真正执行并在收妥结果后确认交付。精确知识历史与图端点共用 `id + knowledge_revision`，原证另有版本；程序按稳定 delivery_id 幂等记录并按全项目交付事件计算访问权重，不按时间、不传播强化、不影响 embedding。已有 tier1 一次综合评分参考访问线索，rank 无二次加权。关系和条件由维护作者接受；没有独立当前理解同步层。

项目现状、余项与历史要求触发同一worker完整检索；`memory freshness`脚本只读比较当前Codex清单、采集回执和端点，必要时分页读取指定聊天逐正文核对，返回新增/可能变化/已覆盖/未知。worker补读相关新原证并说明采集截止、待语义范围及未核状态；探查不写记忆、不生成向量，触发仍依赖agent指令。安装升级由独立[basepack-setup](../../experiments/20261106-basepack/skills/basepack-setup/SKILL.md)指向既有操作文档，日常使用和维护仍用随包memory skill。

Codex 宿主自动提供项目绑定和完整注册根，线程明确 projectId 优先，字段缺失时按 root/worktree/common-dir 与其它注册项目根排除冲突；无法取证留覆盖缺口，非 Codex 保持文件功能。每聊天导出留在项目 memory 目录并沿原生 source_version 保存，精确回读提供消息身份与正文字节范围。宿主字段、附件及完整分叉/继承范围的实际验收边界见 [本轮进度](../archive/20261110-onboarding-simplification/progress.md)。

机器级 embedding 由 Sentence Transformers 编码、LitServe 管理请求与单推理 worker、Shawl 托管 Windows 服务进程树。设备默认 auto，优先可用 CUDA，否则 CPU；同模型、前处理和精度的 CPU/CUDA 向量共用语义身份。模型在服务 setup 时加载并常驻；EmbeddingClient 只通过配置中的 HTTP endpoint 调用，客户端等待结束不会中断共享推理。模型、预处理和归一化决定 embedding_identity，记忆按该身份与实际编码输入版本过滤和重建向量；客户端安装路径变化不改变语义空间。接口与生命周期边界见 [资源模块](modules/resources.md)。

普通CPU/GPU作业由CondorClient提交至HTCondor；容量、队列、限时策略、终态和GPU站点策略由Condor维护。basePack保留JSON参数传递、退出码与不确定提交查询恢复，删除额外PID确认和客户端重复作业计时；等待到期只返回observation_expired，不自动取消。共享模型服务位于Condor作业树之外，通过管理员固定背景预留与普通作业并存。项目知识、来源和工具产物属于各自项目，通用模型和机器环境可显式共用。配置、安装和运行目录见[部署合同](deployment.md)。

0.8.1 保留数据库认证与显式回环 IP。配置维护 username 与可选 password_file，默认文件为实际 memory_dir/password.txt；客户端和 launcher 读取同一文件，config show 只显示解析路径。文件缺失、权限或认证错误直接失败；已有库恢复原凭据，不随机换密码。UUID 只防误连，账户密码负责认证。

每项目数据库使用该项目内独立物理目录及进程，多聊天共享；通用 exe 和 embedding 服务可跨项目共用。项目 UUID 核查防止误连，原生导出连同原件、必要 assets 与配置构成恢复集合。旧项目仅作参考，不承接其数据库或验收，依据见 [调研索引](../tasks/20261106-rebuild/research/sources.md)。

按文件位置理解源码、安装、业务实例与共享设施时读 [逻辑框图](diagrams.md)。跨模块修改读 [架构说明](architecture.md)，准备运行或诊断读 [环境说明](environment.md)，概念歧义查 [项目术语](../terminology.md)。跨工具状态见 [重建总进度](../tasks/20261106-rebuild/progress.md)。
