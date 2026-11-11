# 系统实现概览

唯一active路线是[20261106-basepack](../../experiments/20261106-basepack/README.md)，源码面向0.10.0.dev1；独立维护候选验证后已合回，当前实现、安装与限制见[维护改造结果](../tasks/20261106-memory-system/maintenance-implementation-result.md)。代码、依赖锁、测试、产品文档、示例和随包skill位于实验工程；根devDoc维护现行实现和活动工作。实测和历史边界见[环境记录](environment.md)，共享资源基线见[R9结果](../archive/20261107-resource-coordination/r9-result.md)。

本仓库提供三项可独立使用的 skill：[engineering-judgment](../../skills/engineering-judgment/SKILL.md) 用于设计、错误处理、兼容和使用流程的工程取舍，保留独立形态，通过长期使用反馈维护；[file-structure](../../skills/file-structure/SKILL.md) 推荐或整理开发文档和实验工程布局；[agent-team](../../skills/agent-team/SKILL.md) 为每项任务选择组织，按完整交付过程判断独立完成、简单协作或清晰分层，并使用宿主已有的订阅 subagent 能力。安装时选择完整目录放入目标 `.agents/skills/`，或把已有项目原件联接到该发现目录，核对相对引用与宿主实际列表；`init` 与 core doctor 不覆盖这项验收。完整步骤见 [项目接入](../../experiments/20261106-basepack/docs/setup-project.md#独立-skills-安装与发现)。组织选择与协作已有指令层实现，复杂广读的质量与总成本对照仍见 [专项记录](../tasks/20261106-rebuild/research/agent-team.md)。

`basepack` 的公共入口包括项目 `init`、`config show`、`config ai`、`doctor`，项目 `memory`，共享图文 `embed` 及普通重任务 `jobs`。项目接入源码和模板统一在 [project/](../../experiments/20261106-basepack/src/basepack/project)，[config.py](../../experiments/20261106-basepack/src/basepack/project/config.py) 唯一解析配置。`config ai` 按项目配置解析 tier 对应的模型与推理强度；宿主读取结果并在派工时实际传递，程序不自行调用模型。日常默认 tier3，检索、筛选和重排序默认 tier1；配置和命令见 [项目接入](../../experiments/20261106-basepack/docs/setup-project.md#agent-模型等级)。项目使用 schema 2 的 `.basepack/config.toml` 和 `.basepack/instructions.md`，根 AGENTS 直接呈现关键动作及详情链接；机器格式保持 schema 1，旧项目需补入 AI 配置。客户端兼容 0.5.0 embedding 服务，部署与旧格式迁移见 [部署合同](deployment.md)。

[项目记忆](modules/memory.md) 使用唯一 SurrealDB 基座。一个 member 同时表示文件、实际章节、智能原文块或图片，也是默认检索表示及图节点；另有实体/决定/条件节点和带依据的原生语义边。宿主订阅 agent 同读完成分块、摘要、识图与关系，程序核源与逐记录知识版本后原子接受。多层全文、图文向量、严格回源、语义展开、人工更正及原生恢复共用这份持久知识。

memory init绑定原UUID并刷新AGENTS关键动作与本机详细入口，固定Python、显式配置和原凭据文件。查询纯读已发布知识；默认全项目maintain在预检前取得单owner，完成机械变化后按返回模型实际派持续协调者。其它聊天继续业务，使用反馈可并发入库，未决报告加入下轮派工。普通批次作者生成并由程序提交即完成，默认不追加审计；用户明确要求时手动审计。来源级已阅/重复及待细化处置避免未变首建反复入队。发布采用原生WebSocket事务透明分消息，保留依赖版本、原文和向量保护。结束stop、取消后代，确认发布结束才release；未知结果保留owner。详见[记忆模块](modules/memory.md)。

CLI检索默认读memory.search_mode，新项目为vector；hybrid/vector按相同语义身份查询，缺模型或兼容向量明确失败。CLI和Python返回`{matches, vector_coverage}`；采集、语义接受与向量覆盖分别报告，结果保留观察knowledge_revision供反馈。guide/rank不需配置，owner/stop/release/recover-owner需配置定位状态但不读凭据或连库，prompt只读配置/模板/回执。doctor默认core，模型及Condor显式选查。

Codex 宿主自动提供项目绑定和完整注册根，线程明确 projectId 优先，字段缺失时按 root/worktree/common-dir 与其它注册项目根排除冲突；无法取证留覆盖缺口，非 Codex 保持文件功能。每聊天导出留在项目 memory 目录并沿原生 source_version 保存，精确回读提供消息身份与正文字节范围。宿主字段、附件及完整分叉/继承范围的实际验收边界见 [本轮进度](../archive/20261110-onboarding-simplification/progress.md)。

机器级 embedding 由 Sentence Transformers 编码、LitServe 管理请求与单推理 worker、Shawl 托管 Windows 服务进程树。设备默认 auto，优先可用 CUDA，否则 CPU；同模型、前处理和精度的 CPU/CUDA 向量共用语义身份。模型在服务 setup 时加载并常驻；EmbeddingClient 只通过配置中的 HTTP endpoint 调用，客户端等待结束不会中断共享推理。模型、预处理和归一化决定 embedding_identity，记忆按该身份与实际编码输入版本过滤和重建向量；客户端安装路径变化不改变语义空间。接口与生命周期边界见 [资源模块](modules/resources.md)。

普通 CPU/GPU 作业由 CondorClient 提交至 HTCondor；容量、队列、终态及 GPU 站点策略由 Condor 维护。共享模型服务位于 Condor 作业树之外，通过管理员固定背景预留与普通作业并存。项目知识、来源和工具产物属于各自项目，通用模型和机器环境可显式共用。配置、安装和运行目录见 [部署合同](deployment.md)。

0.8.1 保留数据库认证与显式回环 IP。配置维护 username 与可选 password_file，默认文件为实际 memory_dir/password.txt；客户端和 launcher 读取同一文件，config show 只显示解析路径。文件缺失、权限或认证错误直接失败；已有库恢复原凭据，不随机换密码。UUID 只防误连，账户密码负责认证。

每项目数据库使用该项目内独立物理目录及进程，多聊天共享；通用 exe 和 embedding 服务可跨项目共用。项目 UUID 核查防止误连，原生导出连同原件、必要 assets 与配置构成恢复集合。旧项目仅作参考，不承接其数据库或验收，依据见 [调研索引](../tasks/20261106-rebuild/research/sources.md)。

按文件位置理解源码、安装、业务实例与共享设施时读 [逻辑框图](diagrams.md)。跨模块修改读 [架构说明](architecture.md)，准备运行或诊断读 [环境说明](environment.md)，概念歧义查 [项目术语](../terminology.md)。跨工具状态见 [重建总进度](../tasks/20261106-rebuild/progress.md)。
