# 系统结构与边界

当前唯一 active 路线为 [20261106-basepack](../../experiments/20261106-basepack/README.md)，源码面向 0.6.1 的公共入口、项目记忆与资源工具。配置和安装合同见 [部署说明](deployment.md)，记忆实际完成边界见 [专项进度](../tasks/20261106-memory-system/progress.md)，资源基线见 [R9 结果](../archive/20261107-resource-coordination/r9-result.md)。文件位置图见 [逻辑框图](diagrams.md)。

## 当前组成

```text
AGENTS.md                         项目规则和阅读导航
README.md                         项目目标、active 路线和路线索引
skills/file-structure/            文件结构 skill 与按需参考
skills/agent-team/                使用宿主 subagent 的分层协作 skill
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
- `file-structure`、`agent-team` 是可独立交付的通用技能。实际 agent 派发、权限和模型能力由宿主提供。
- 产品代码、模板和资源 skill 各有一个维护源。运行代码通过普通 wheel 安装；业务项目只保存自己的接入配置、数据和产物。
- 项目显式指定 schema 2 接入配置，绑定运行 Python 和 schema 1 机器配置。project.root 相对项目配置，受管理数据进入该业务项目 `.basepack/`；机器相对路径以机器配置为基准。ProjectConfig 只解析公共绑定，各功能按需读取自身节。
- `init` 从安装包模板生成配置和详细 instructions，根 AGENTS 合并短指针；memory init 另行绑定项目 UUID 并写入 brief/skill 的宿主入口。旧格式先经保留的 0.4.0 迁移，当前版本直接读取 schema 2。
- 项目记忆只用 SurrealDB。member 同时是层级、检索表示与图节点；source_version、change 和必要图像 assets 保存原文依据及更正。source revision、input_revision、knowledge_revision 与 embedding_identity 各管来源、编码输入、并发更正和语义空间。原生事务原子接受，原生 CLI 负责服务、导出与恢复；没有多后端层或自建 MCP。
- 结构解析只供定位。实际智能块、摘要、识图、关系和评分由宿主订阅 agent 同读完成；脚本验证来源与块范围，变化沿包含及依据使受影响知识待核。brief 做低成本快检并交付启动信息，宿主承担任务内维护与深维护。详细合同见 [记忆模块](modules/memory.md)。
- 默认查询直接从全部粒度取得全文及兼容向量候选，以原生查询和短排名融合交给 worker；worker 核原文、展开图和评分，selection 按预算交付完整内容与省略入口。必保留内容经 brief 独立交付，缺兼容向量明确失败，text 模式可单独运行。
- embedding 的编码由 Sentence Transformers 负责；薄 LitAPI 在 setup 加载模型、predict 编码，LitServe 管理 HTTP、队列和单推理 worker，Shawl 的 Job Object 拥有 Windows 服务进程树。服务位于 Condor 作业树之外，多项目通过同一 endpoint 共用模型。向量语义身份独立于 HTTP 等待和服务部署，见 [资源模块](modules/resources.md)。
- 普通任务的进程树、容量、队列和站点 GPU 策略归 Condor；basePack 编码标准申请并观察结果及回收，psutil 提供本机进程关系观察。背景服务与普通作业的额度由管理员预留协调。
- 后续路线复用明确版本的发行包或公开 HTTP/API；模型、环境和缓存可以显式共享，项目知识和试验状态分别保存。运行环境不依赖另一条路线的可变源码或临时工作区。

数据库物理文件与图像快照属于业务项目；每项目独立进程/端口，多聊天共享。源码外普通安装和机器观测见 [环境说明](environment.md)；文件结构建议、宿主协作与项目知识分别由对应模块维护。
