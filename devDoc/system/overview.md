# 系统实现概览

当前唯一 active 路线是 [20261106-basepack](../../experiments/20261106-basepack/README.md)。源码、依赖与锁、测试、产品文档、示例和 resources skill 一起位于实验工程；根 devDoc 维护现行实现与活动工作。本文描述已交付的 0.5.0，普通安装、真实联合及回退验收见 [R9 结果](../archive/20261107-resource-coordination/r9-result.md)。

本仓库提供两项可独立使用的 skill：[file-structure](../../skills/file-structure/SKILL.md) 推荐或整理开发文档和实验工程布局；[agent-team](../../skills/agent-team/SKILL.md) 使用宿主已有的订阅 subagent 能力组织分工。分层协作已有指令层初版，复杂广读的质量与总成本对照仍见 [专项记录](../tasks/20261106-rebuild/research/agent-team.md)。

`basepack` 的公共入口包括项目 `init`、`config show`、`doctor`，共享图文 `embed`，以及普通重任务 `jobs`。项目接入源码和模板统一在 [project/](../../experiments/20261106-basepack/src/basepack/project)，[config.py](../../experiments/20261106-basepack/src/basepack/project/config.py) 唯一解析配置。项目使用 schema 2 的 `.basepack/config.toml` 和 `.basepack/instructions.md`，根 AGENTS 只保留短指针；机器配置保持 schema 1。0.5.0 直接升级支持 0.4.0 的项目格式，旧项目先通过保留的 0.4.0 迁移，详见 [部署合同](deployment.md)。

机器级 embedding 由 Sentence Transformers 编码、LitServe 管理请求与单推理 worker、Shawl 托管 Windows 服务进程树。模型在服务 setup 时加载并常驻；EmbeddingClient 只通过配置中的 HTTP endpoint 调用，客户端等待结束不会中断共享推理。模型、预处理和归一化决定 `embedding_identity`；新旧身份的索引兼容须由记忆任务处理。接口和生命周期边界见 [资源模块](modules/resources.md)。

普通 CPU/GPU 作业由 CondorClient 提交至 HTCondor；容量、队列、终态及 GPU 站点策略由 Condor 维护。共享模型服务位于 Condor 作业树之外，通过管理员固定背景预留与普通作业并存。项目知识、来源和工具产物属于各自项目，通用模型和机器环境可显式共用。配置、安装和运行目录见 [部署合同](deployment.md)。

记忆的 [多层文字与初步图关系源码](modules/memory.md) 已实现，正式安装、完整图文与行为验收由 [记忆任务](../tasks/20261106-memory-system/progress.md) 接续；已安装资源版 0.5.0 不包含本轮新增 CLI。旧项目和已有机器设施仅提供参考，不作为新功能完成证据；依据见 [调研索引](../tasks/20261106-rebuild/research/sources.md)。

按文件位置理解源码、安装、业务实例与共享设施时读 [逻辑框图](diagrams.md)。跨模块修改读 [架构说明](architecture.md)，准备运行或诊断读 [环境说明](environment.md)，概念歧义查 [项目术语](../terminology.md)。跨工具状态见 [重建总进度](../tasks/20261106-rebuild/progress.md)。
