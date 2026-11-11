# 当前文件与运行逻辑框图

按 2026 年 11 月 11 日的 0.9.1 源码合同更新；本轮修复和安装验证见 [一致性审阅进度](../archive/20261111-consistency-review/progress.md)，本机部署观测见 [环境记录](environment.md)。既有项目沿用认证服务、原密码、物理库和 UUID，客户端升级与入口刷新不要求迁库。0.5.0 core/jobs 和共享 embedding 服务继续保留，后者与当前客户端协议兼容。沿用[参考 chat](codex://threads/01a1bb3f-4db8-7c10-8d71-c951aba18aa2) 按文件位置分层的方法；记忆行为的实际验收边界见[专项进度](../tasks/20261106-memory-system/progress.md)，阶段合同见[记忆方案图](../tasks/20261106-memory-system/diagrams.md)。

## 路径与读图约定

| 代号 | 位置与含义 |
| --- | --- |
| R | 本源码仓库：`D:/project/20261106 memsys` |
| E | 当前 active 工程：`R/experiments/20261106-basepack` |
| Im | 本机稳定客户端安装包：`D:/AgentTools/envs/basepack-client/Lib/site-packages/basepack` |
| Ic | 保留的 0.5.0 core/jobs：`C:/Program Files/Python313/Lib/site-packages/basepack` |
| Is | 保留的 0.5.0 embedding 服务：`C:/ProgramData/basepack/envs/service/Lib/site-packages/basepack` |
| A | 本机共享设施：`D:/AgentTools` |
| C | 本机 HTCondor：`C:/condor` |
| P、P1、P2 | 接入 basePack 的独立业务项目；本仓库 R 也已接入，项目库使用本地 18080 端口 |

箭头按标签表示构建、调用、引用、读写或所有权，不能只按相邻位置推断依赖。以下机器绝对路径是本次部署实例；公共代码通过配置定位。完整合同见[部署说明](deployment.md)。

## 1. 源码怎样成为安装与项目接入

```mermaid
flowchart TB
  subgraph source["R / E：唯一产品维护源"]
    code["E/src/basepack/<br/>代码与 project/templates/"]
    deps["E/pyproject.toml + uv.lock<br/>依赖与发行声明"]
    wheel["E/dist/交付批次/<br/>basepack-0.9.1-*.whl"]
    r9["E/dist/r9/<br/>保留 basepack-0.5.0 wheel"]
    policy["E/examples/condor/<br/>60_resources.conf、70_job_transforms.conf"]
    code -->|构建| wheel
    deps -->|发行版本与依赖声明| wheel
  end
  wheel -->|普通升级客户端| memory["Im：独立客户端环境<br/>memory 与资源调用入口"]
  r9 -->|既有安装保留| core["Ic：系统 core/jobs 0.5.0"]
  r9 -->|既有安装保留| service["Is：共享 embedding 服务 0.5.0"]
  policy -->|管理员单独部署| condor["C/config/ 下的站点策略"]
  memory -->|init 读取安装包内模板| instance["P/.basepack/<br/>config.toml + instructions.md"]
  memory -->|init 合并短指针与忽略规则| entry["P/AGENTS.md<br/>P/.gitignore"]
  memory -->|memory init：schema、项目 UUID、brief 入口| instance
```

wheel 携带 memory skill，devDoc、根 skills、测试、示例和模型沿各自维护位置保留；运行从普通安装加载。当前客户端可沿用既有 0.5.0 资源服务。普通 `init` 生成接入文件，`memory init` 再绑定已启动的项目库、安装 schema 和宿主入口。依据：[路线入口](../../experiments/20261106-basepack/README.md)、[项目接入实现](../../experiments/20261106-basepack/src/basepack/project/init.py)、[记忆实现](modules/memory.md)。

## 2. 两个业务项目如何绑定共享设施

```mermaid
flowchart LR
  subgraph one["业务项目 P1"]
    cfg1["P1/.basepack/config.toml<br/>schema 2"]
    data1["P1/.basepack/jobs/<br/>本项目提交材料与日志"]
    memory1["P1/.basepack/memory/<br/>独立 store、assets 与日志"]
    cfg1 -->|jobs.jobs_dir，相对 P1 根| data1
    cfg1 -->|memory.data_dir，相对 P1 根| memory1
  end
  subgraph two["业务项目 P2"]
    cfg2["P2/.basepack/config.toml<br/>schema 2"]
    data2["P2/.basepack/jobs/<br/>本项目提交材料与日志"]
    memory2["P2/.basepack/memory/<br/>独立 store、assets 与日志"]
    cfg2 -->|jobs.jobs_dir，相对 P2 根| data2
    cfg2 -->|memory.data_dir，相对 P2 根| memory2
  end
  cfg1 -->|显式 --config| resolve["安装包 project/config.py<br/>每次绑定一个项目配置"]
  cfg2 -->|显式 --config| resolve
  resolve -->|runtime.python：worker 解释器| python["项目显式指定的 Python<br/>保留 Ic 或使用当前兼容安装"]
  subgraph shared["机器级共享设施"]
    machine["A/basepack.toml<br/>schema 1：机器配置"]
    machine -->|embedding.model_root| model["A/models/Qwen/Qwen3-VL-Embedding-2B/<br/>revision/model.lock.json + model/"]
    machine -->|embedding.endpoint| http["127.0.0.1:8765<br/>共享 embedding HTTP 入口"]
    machine -->|htcondor.bin_dir、config_file| condor["C/bin/<br/>C/condor_config"]
  end
  resolve -->|runtime.machine_config| machine
  serviceConfig["SCM / Shawl 服务定义"] -->|显式 stdout / stderr 路径| logs["A/state/basepack/embedding/logs/"]
```

`project/config.py` 是唯一路径解析处：`project.root` 相对配置文件目录；项目数据路径相对该根且位于 `.basepack/`；机器相对路径相对 `A/basepack.toml`。`runtime.python` 给普通作业的 worker 使用，不会把当前 CLI 自动换解释器重启。机器 TOML 定位 Condor，普通作业容量和站点策略仍由 Condor 配置维护。依据：[config.py](../../experiments/20261106-basepack/src/basepack/project/config.py)。

## 3. 普通作业经过哪些文件和进程

```mermaid
flowchart TB
  subgraph project["业务项目 P"]
    spec["调用者：JobSpec<br/>executable、cwd、资源、传输清单"]
    client["CondorClient<br/>用 P/.basepack/config.toml 定位"]
    payload["P/.basepack/jobs/提交ID/<br/>basepack-job.json + job.sub"]
    records["同一提交目录<br/>submission.json、worker.json<br/>stdout.txt、stderr.txt、events.log"]
    business["业务脚本、输入与输出<br/>按 JobSpec.cwd / 显式业务路径"]
    spec -->|submit / run| client
    client -->|写规范化申请| payload
    client -->|写提交回执，读取状态与日志| records
  end
  payload -->|condor_submit| scheduler["C：HTCondor<br/>队列、资源、终态和进程树所有权"]
  scheduler -->|启动配置指定的 Python| worker["配置的安装包 jobs/worker.py<br/>UTF-8 参数桥接"]
  worker -->|启动指定 executable| app["业务程序进程树<br/>cwd 沿 Condor 选定的执行目录"]
  app -->|无传输：直接按 JobSpec.cwd 读写| business
  worker -->|写执行回执| records
  scheduler -->|写事件与标准输出| records
  scheduler -->|有传输：准备执行目录| scratch["C/execute/ 下的 scratch<br/>有传输时 worker / 业务程序的 cwd"]
  business -->|transfer_inputs 按 basename 暂存| scratch
  app -->|有传输：在 scratch 读写| scratch
  scratch -->|按 transfer_outputs 回传| business
```

业务输出不必全部进入 `.basepack/`。有传输时，输入按 basename 进入 execute scratch，worker 和业务程序在其中执行，清单中的输出再回传至 `JobSpec.cwd`；Condor 自身队列和日志另存 C/spool、C/log。`wait` 等待超时后作业仍可继续；`run` 的排队/运行期限及取消由原生 Condor 流程执行。embedding 服务在这棵作业树之外，额度以管理员固定背景预留协调。依据：[提交编码](../../experiments/20261106-basepack/src/basepack/jobs/submit.py)、[客户端](../../experiments/20261106-basepack/src/basepack/jobs/client.py)、[资源合同](modules/resources.md)。

## 4. embedding 的代码、模型和进程归谁管理

```mermaid
flowchart TB
  caller["P 中的 CLI / EmbeddingClient<br/>Im 或 Ic 的 embedding/client.py"]
  scm["Windows SCM<br/>BasepackEmbedding：Manual、LocalSystem"]
  shawl["A/bin/shawl-1.9.0/shawl.exe<br/>Job Object 拥有整个服务进程树"]
  subgraph service["纯净共享环境：C:/ProgramData/basepack/envs/service/"]
    server["Scripts/python.exe → Is/embedding/service.py<br/>LitServe：HTTP、队列与 worker 管理"]
    worker["单推理 worker：LitAPI<br/>setup 加载 / predict 编码"]
    encoder["Is/embedding/qwen3_vl.py<br/>Sentence Transformers → Torch / GPU"]
    server -->|派发请求；原生 worker 故障重建| worker
    worker -->|调用| encoder
  end
  scm -->|启动与停止| shawl
  shawl -->|托管与整树回收| server
  caller -->|POST /predict：文字 / 本地图片路径| server
  server -->|vectors + embedding_identity + pid| caller
  config["A/basepack.toml"] -->|endpoint / 模型 / 设备 / 限额| server
  model["A/models/.../revision/<br/>model.lock.json + model/"] -->|setup 读取同份本地权重| encoder
  image["P 中的图片原件<br/>服务账户须可读取"] -->|按请求绝对路径读取| encoder
  server -->|服务日志| logs["A/state/basepack/embedding/logs/"]
```

共享服务仍为 Is 中的 0.5.0，当前客户端沿用其协议与 embedding_identity 合同。单推理 worker 不等于单个系统进程，LitServe 还使用 Manager 等辅助进程。模型常驻，不随客户端超时退出；排队期限不打断已开始推理。worker 故障由 LitServe 重建，主进程或 Shawl 故障后由管理员手动启动；停止按 SCM → Shawl 整树回收。语义身份由模型和编码合同决定，部署路径不属于该身份。依据：[service.py](../../experiments/20261106-basepack/src/basepack/embedding/service.py)、[生命周期与接口](modules/resources.md)、[R9 交付](../archive/20261107-resource-coordination/r9-result.md)。

## 5. 项目记忆的数据库与维护归谁管理

```mermaid
flowchart TB
  exe["A/bin/surrealdb-4.0.0/surreal.exe<br/>官方程序可跨项目共用"]
  subgraph project["业务项目 P：知识、原件与数据库归本项目"]
    launch["P/.basepack/memory/serve.ps1<br/>认证 + 显式回环bind<br/>同config读取username / password_file"]
    server["本项目 SurrealDB 进程<br/>独立端口；本仓库 R 为 18080"]
    store["P/.basepack/memory/store/<br/>member：文件 → 实际章节 → 智能原文块 / 图片<br/>原文快照、摘要、依据、语义关系、更正与派生向量"]
    assets["P/.basepack/memory/assets/<br/>必要原图版本"]
    original["P 中的业务原件<br/>相对路径与原字节版本"]
    chats["P/.basepack/memory/codex/<br/>受管 UTF-8 聊天导出"]
    client["memory/ + P/.basepack/config.toml<br/>回环endpoint、UUID、username<br/>自动读同一password_file"]
    launch -->|普通用户隐藏手动启动| server
    client -->|原生 HTTP / SurrealQL；核项目身份| server
    server -->|独占物理目录，多聊天共用| store
    original -->|prepare 读原件并核版本与范围| client
    chats -->|同一 source_version / prepare / apply| client
    client -->|保留必要原图版本| assets
  end
  exe -->|运行程序| server
  client -->|EmbeddingClient：实际表示或原图| embedding["共享 embedding 0.5.0<br/>机器模型与推理进程"]
  embedding -->|向量及 embedding_identity| client
```

客户端和 launcher 读取同一个密码文件，前者自动认证，后者交给原生 SurrealDB。新 shell 直接 brief；guide/rank/stop 无需凭据。已有认证进程通常无需因客户端升级重启，原目录、凭据与 UUID 保持；缺文件恢复原凭据，改写文件不等于轮换库内账户。共享 embedding 继续由 SCM/Shawl 托管。每项目的端口、UUID 与物理 store 独立，namespace/database 不代替物理隔离。文件、实际章节与智能原文块各为可寻址 member，默认可直接全文/向量检索；包含、摘要依据和语义边共同保存在项目库。恢复使用原生导出并保留原件、必要 assets 与配置。依据：[记忆实现](modules/memory.md)、[用户流程](../../experiments/20261106-basepack/docs/memory.md)。

```mermaid
flowchart TB
  entry["P/AGENTS.md<br/>→ .basepack/instructions.md"]
  brief["memory brief<br/>纯读已发布知识及依据快照"]
  host["工作 agent 实收<br/>mandatory、地图、线索与覆盖缺口"]
  preflight["独立 memory maintain + task control<br/>采集持久化聊天截点<br/>比较来源与成员接受版本"]
  mechanical["程序完成机械等价小批<br/>保留原字节快照和必要编码"]
  prepare["余下语义范围 → prepare<br/>变化片段、定位、依据与 expected"]
  reader["宿主订阅 reader<br/>必要新旧上下文、摘要、识图与关系"]
  apply["memory apply --control<br/>核版本、编码、原子发布"]
  retrieval["search / read / neighbors<br/>各层候选、已发布快照、语义展开"]
  delivery["reader 实读评分 → rank<br/>按预算交付内容、来源与缺口"]
  entry -->|开始 / 接续任务| brief
  brief -->|直接交付| host
  entry -->|并行独立工具任务；业务不等待| preflight
  preflight --> mechanical
  preflight -->|needs_semantic=true| prepare
  prepare --> reader
  reader -->|同批成果| apply
  host -->|一次检索委托| retrieval
  retrieval -->|同一 reader 阅读与评分| delivery
  host -->|业务结束：stop control，再取消worker| preflight
```

brief/search/read 保持纯读。确定性维护把元数据、全文换行等价与有足够上下文证据的唯一定位交给程序；余下语义范围按来源合并并跨任务接续，不因积压数量关闭自动小批。聊天采集先依宿主绑定、项目根/worktree及完整注册根排除归属冲突；受管原文与旧已发布快照分别保留，消息精确定位从快照解析。任务 control 共用于采集和发布，已采集/已发布部分保留；采集数量、语义 pending 和向量覆盖各有边界。实际验收与未核范围见 [本轮进度](../archive/20261110-onboarding-simplification/progress.md)。

## 6. 产品源码内部怎样分工

```mermaid
flowchart LR
  main["E/src/basepack/\_\_main\_\_.py<br/>CLI 分发"]
  main -->|init| init["project/init.py<br/>读取 project/templates/"]
  main -->|config show / config ai / 项目调用| config["project/config.py<br/>ProjectConfig / MachineConfig"]
  main -->|doctor| doctor["project/doctor.py<br/>只读诊断"]
  main -->|embed / embedding| ecli["embedding/cli.py"]
  main -->|jobs| jcli["jobs/cli.py"]
  main -->|memory| mcli["memory/cli.py<br/>项目动作与宿主入口"]
  mcli -->|maintain：独立采集与机械预检| maintenance["memory/maintenance.py + codex.py<br/>归属证据、原文、未决范围与control"]
  mcli -->|原生领域查询与事务| memory["memory/store.py + schema.surql<br/>多层知识、关系、brief 与局部维护"]
  memory -->|严格原文 / 原图定位| content["memory/content.py + images.py"]
  memory -->|共享编码与兼容空间| vectors["memory/vectors.py"]
  vectors --> eclient
  mcli -->|实际 reader 分数与预算| selection["memory/selection.py<br/>排序、去重、正文交付"]
  ecli -->|请求| eclient["embedding/client.py<br/>公开 HTTP 客户端"]
  ecli -->|status / stop| manage["embedding/admin.py<br/>健康端点 / SCM 控制"]
  ecli -->|serve| serve["embedding/service.py<br/>薄 LitAPI + LitServe"]
  serve -->|编码与语义身份| model["embedding/qwen3_vl.py<br/>embedding/identity.py"]
  jcli -->|普通任务| jclient["jobs/client.py<br/>CondorClient"]
  jclient -->|生成标准提交材料| submit["jobs/submit.py<br/>JobSpec / Condor 字段"]
  submit -->|job.sub 指定启动模块| worker["jobs/worker.py<br/>Condor 启动的执行入口"]
  ecli -->|解析机器配置| config
```

图列主要调用与材料关系，不枚举每个 import；需要项目的命令从 `__main__` 取得解析后的配置再交给对应模块。`memory guide/rank/stop` 在配置解析前分派，按各自输入独立运行。memory skill 通过宿主的订阅 reader 执行理解、建图与评分，数据库使用原生 HTTP/SQL，服务与备份使用 SurrealDB CLI。旧自写 HTTP/supervisor/worker 登记、私有 RPC 和 `migrate` 已从 0.5.0 退役，历史材料见资源归档。依据：[源码入口](../../experiments/20261106-basepack/src/basepack/__main__.py)、[架构边界](architecture.md)。

## 7. 开发文档、skills 与临时材料放在哪里

```mermaid
flowchart TB
  entry["R/AGENTS.md + README.md<br/>按问题进入相关材料"]
  entry -->|目标与取舍| charter["R/devDoc/project-charter.md<br/>用户目标；修改正文须同意"]
  entry -->|了解已交付实现| system["R/devDoc/system/<br/>概览、架构、部署、模块、框图"]
  entry -->|继续开发| tasks["R/devDoc/tasks/<br/>计划、调查、进度与结果"]
  tasks -->|任务结束后整体归档| archive["R/devDoc/archive/<br/>历史条件和证据"]
  entry -->|产品与执行入口| route["E/README.md → E/docs/<br/>用户与管理员流程"]
  entry -->|结构建议 / 组织分工| general["R/skills/<br/>file-structure、agent-team、engineering-judgment"]
  route -->|资源操作指引| resources["E/skills/resources/"]
  general -->|本机发现联接| junction["R/.agents/skills/<br/>指向各 skill 的唯一维护源"]
  resources -->|本机发现联接| junction
  junction -->|宿主读取 skill| host["宿主 agent / subagent<br/>实际派发、模型与权限由宿主提供"]
  host -->|memory guide / 项目 instructions 定位并读取| memory["Im/memory/SKILL.md<br/>源码维护于 E/src/basepack/memory/"]
  tasks -->|一次性试验| temp["R/tmp/任务名/<br/>可随时清除，Git 忽略"]
  temp -->|选留复核原证| evidence["R/artifacts/runs/运行ID/<br/>长期原证，Git 忽略"]
  evidence -->|链接条件与结论| tasks
  system -->|按次记录已发生变化| changes["R/devDoc/change_log/<br/>major / minor"]
```

skill 是宿主读取的指令与参考；memory skill 随 wheel 安装，根通用 skill 与 resources skill 沿发现联接读取，各自保留唯一维护源。系统事实随实际实现更新，计划只在 tasks，结束材料进 archive；图和叙述冲突时应回查源码、配置与验收条件。依据：[文档约定](../documentation.md)、[结构说明](architecture.md)、[环境与发现入口](environment.md)。
