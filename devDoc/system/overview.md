# 系统实现概览

当前唯一 active 路线是 [20261106-basepack](../../experiments/20261106-basepack/README.md)，源码面向 0.6.2。代码、依赖锁、测试、产品文档、示例及随包 skill 位于实验工程；根 devDoc 维护现行实现与活动工作。资源部署基线见 [R9 结果](../archive/20261107-resource-coordination/r9-result.md)，记忆功能与正式安装的实际完成边界见 [专项进度](../tasks/20261106-memory-system/progress.md)。

本仓库提供两项可独立使用的 skill：[file-structure](../../skills/file-structure/SKILL.md) 推荐或整理开发文档和实验工程布局；[agent-team](../../skills/agent-team/SKILL.md) 为每项任务选择组织，按完整交付过程判断独立完成、简单协作或清晰分层，并使用宿主已有的订阅 subagent 能力。组织选择与协作已有指令层实现，复杂广读的质量与总成本对照仍见 [专项记录](../tasks/20261106-rebuild/research/agent-team.md)。

`basepack` 的公共入口包括项目 `init`、`config show`、`config ai`、`doctor`，项目 `memory`，共享图文 `embed` 及普通重任务 `jobs`。项目接入源码和模板统一在 [project/](../../experiments/20261106-basepack/src/basepack/project)，[config.py](../../experiments/20261106-basepack/src/basepack/project/config.py) 唯一解析配置。`config ai` 按项目配置解析 tier 对应的模型与推理强度；宿主读取结果并在派工时实际传递，程序不自行调用模型。日常默认 tier3，检索、筛选和重排序默认 tier1；配置和命令见 [项目接入](../../experiments/20261106-basepack/docs/setup-project.md#agent-模型等级)。项目使用 schema 2 的 `.basepack/config.toml` 和 `.basepack/instructions.md`，根 AGENTS 只保留短指针；机器格式保持 schema 1，旧项目需补入 AI 配置。客户端兼容 0.5.0 embedding 服务，部署与旧格式迁移见 [部署合同](deployment.md)。

[项目记忆](modules/memory.md) 使用唯一 SurrealDB 基座。一个 member 同时表示文件、实际章节、智能原文块或图片，也是默认检索表示及图节点；另有实体/决定/条件节点和带依据的原生语义边。宿主订阅 agent 同读完成分块、摘要、识图与关系，程序核源与逐记录知识版本后原子接受。多层全文、图文向量、严格回源、语义展开、人工更正及原生恢复共用这份持久知识。

memory init 绑定项目 UUID 并写入随包 skill 和 brief 的宿主入口。brief 快检已登记原件及 source_scope，交付必保留内容、项目地图、相关线索与缺口；宿主据此维护任务内小批，不依赖后台语义进程或另购 LLM API。变化按范围、包含和依据失效，未变表示可复用；默认 hybrid 直接检索所有粒度，缺兼容向量明确报错，text 模式可独立运行。

机器级 embedding 由 Sentence Transformers 编码、LitServe 管理请求与单推理 worker、Shawl 托管 Windows 服务进程树。模型在服务 setup 时加载并常驻；EmbeddingClient 只通过配置中的 HTTP endpoint 调用，客户端等待结束不会中断共享推理。模型、预处理和归一化决定 embedding_identity，记忆按该身份与实际编码输入版本过滤和重建向量；客户端安装路径变化不改变语义空间。接口与生命周期边界见 [资源模块](modules/resources.md)。

普通 CPU/GPU 作业由 CondorClient 提交至 HTCondor；容量、队列、终态及 GPU 站点策略由 Condor 维护。共享模型服务位于 Condor 作业树之外，通过管理员固定背景预留与普通作业并存。项目知识、来源和工具产物属于各自项目，通用模型和机器环境可显式共用。配置、安装和运行目录见 [部署合同](deployment.md)。

每项目数据库使用该项目内独立物理目录及进程，多聊天共享；通用 exe 和 embedding 服务可跨项目共用。项目 UUID 核查防止误连，原生导出连同原件、必要 assets 与配置构成恢复集合。旧项目仅作参考，不承接其数据库或验收，依据见 [调研索引](../tasks/20261106-rebuild/research/sources.md)。

按文件位置理解源码、安装、业务实例与共享设施时读 [逻辑框图](diagrams.md)。跨模块修改读 [架构说明](architecture.md)，准备运行或诊断读 [环境说明](environment.md)，概念歧义查 [项目术语](../terminology.md)。跨工具状态见 [重建总进度](../tasks/20261106-rebuild/progress.md)。
