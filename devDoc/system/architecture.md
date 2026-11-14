# 系统结构与边界

当前唯一 active 路线为 [20261106-basepack](../../experiments/20261106-basepack/README.md)，源码面向 0.13.0.dev1 的公共入口、项目记忆与资源工具；当前验证与安装见[交付进度](../tasks/20261114-delivery-closeout/progress.md)。配置和安装合同见 [部署说明](deployment.md)，记忆实际完成边界见 [专项进度](../tasks/20261106-memory-system/progress.md)，资源基线见 [R9 结果](../archive/20261107-resource-coordination/r9-result.md)。文件位置图见 [逻辑框图](diagrams.md)。

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
- `init` 从安装包模板生成配置和详细 instructions，根AGENTS合并关键动作及详情链接；memory init绑定原UUID并刷新AGENTS和本机入口，保留托管块外字节。旧格式先经保留的 0.4.0 迁移，当前版本直接读取 schema 2。
- memory endpoint 在唯一配置边界只接受 HTTP(S) 显式回环 IP；数据库保留认证。客户端与 launcher 按配置读取唯一 password_file（默认 memory_dir/password.txt）及 username，config show 只显示路径。缺失/权限/认证错误直接失败；项目UUID防误连。升级保留项目身份与凭据，0.13的成员身份变化先离线迁库再同步切换客户端。
- 项目记忆只用 SurrealDB。member 同时是层级、检索表示与图节点；source_version、change 和必要图像 assets 保存原文依据及更正。source revision、input_revision、knowledge_revision 与 embedding_identity 各管来源、编码输入、并发更正和语义空间。原生WebSocket事务按完整语句透明分消息、原子接受，原生 CLI 负责服务、导出与恢复；没有多后端层或自建 MCP。
- member身份统一为程序分配的UUID。作者草稿按数组位置引用本草稿或指定草稿内的新对象，freeze统一解析父项、依据与边端点并冻结批次；更新沿用prepare提供的UUID和expected。apply只接受新协议，重复写入与冲突更新明确失败，同一冻结批次重放幂等。存量转换工具及映射属于离线恢复材料，正常读写不查旧ID别名。
- 结构解析只供定位。独立`memory maintain --holder <thread> --control <fresh>`先原子取得项目owner，再采集已绑定宿主聊天、比较原件与各成员实际接受版本，程序完成机械等价小批并输出必要变化与未决范围。智能块、摘要、识图、关系和评分的语义余项由宿主订阅 agent 同读完成，按来源核版本后原子发布内容与所需向量；机械匹配不替代语义判断。查询使用已发布知识与对应依据快照，brief 交付启动信息且不扫描或写入。宿主stop自有control、取消自有后代、确认发布结束后release；未决发布保留owner。普通批次作者生成并成功提交后结束，使用反馈持久待办，已阅/延期处置避免重复首建；仅用户明确审计意图启动审计。详细合同见 [记忆模块](modules/memory.md)。
- Codex 来源适配仅通过受支持的 App Server 读取持久化消息；宿主提供当前项目绑定及完整注册根，以 projectId 优先、root/worktree 与其它注册项目根排冲突。每聊天的受管导出进入既有 source_version/prepare/apply，消息定位从已核快照解析；来源发现、正文采集、语义接受与向量覆盖各自可见。能力缺失或归属不明保留缺口，非 Codex 继续文件功能。
- 项目现状及历史决定由同一检索worker核已有知识和必要新聊天。只读freshness脚本返回新增、可能变化、实际正文已覆盖和未知清单；端点或更新时间不证明正文一致。worker选择相关原证补读，明确采集与语义边界，不取得维护owner或发布知识。触发仍由宿主agent遵循指令。
- 默认查询直接从全部粒度取得全文及兼容向量候选，按配置的 vector/hybrid 查询交给 worker；worker 核原文、展开图和评分，selection 按预算交付完整内容与省略入口。必保留内容经 brief 独立交付，模型或兼容向量缺失明确失败，hybrid 保留文字匹配和精确查找。
- embedding 的编码由 Sentence Transformers 负责；薄 LitAPI 在 setup 加载模型、predict 编码，LitServe 管理 HTTP、队列和单推理 worker，Shawl 的 Job Object 拥有 Windows 服务进程树。服务位于 Condor 作业树之外，多项目通过同一 endpoint 共用模型。CPU/CUDA 按相同语义合同编码，设备自动选择不改变身份。向量语义身份独立于 HTTP 等待和服务部署，见 [资源模块](modules/resources.md)。
- 普通任务的进程树、限时策略、容量、队列和站点GPU策略归Condor；basePack保留参数封装和不确定提交查询恢复，按原生queue/history/事件观察结果。调用者等待到期不取消作业，取消请求与终态分别报告；不另核OS进程族。背景服务与普通作业的额度由管理员预留协调。
- 后续路线复用明确版本的发行包或公开 HTTP/API；模型、环境和缓存可以显式共享，项目知识和试验状态分别保存。运行环境不依赖另一条路线的可变源码或临时工作区。

数据库物理文件与图像快照属于业务项目；每项目独立进程/端口，多聊天共享。源码外普通安装和机器观测见 [环境说明](environment.md)；文件结构建议、宿主协作与项目知识分别由对应模块维护。

知识版本归档与交付状态仍在同一项目数据库。原生同步事件为今后的 member/node/semantic 知识版本保留前后像，关系端点另外绑定知识版本；旧原证版本不冒充旧知识表示。交付短事务持久化稳定 delivery_id、实际观察版本和全局事件，独立于语义维护 owner 与向量输入。宿主负责实际派工/接收/确认，CLI 与 Python 共用内核；渲染、search、read 和 rank 不构成交付。权重只按交付事件惰性计算，不读取时钟、不传播强化。brief 不做任务相关检索，worker 同次阅读和综合评分；不新增跨来源的当前理解同步层。
