# 当前文件与运行逻辑框图

按 2026 年 11 月 9 日的 0.5.0 实现、普通安装和本机部署绘制，核对基线为 main `6685c87`。沿用[参考 chat](codex://threads/01a1bb3f-4db8-7c10-8d71-c951aba18aa2) 按文件位置分层的方法；旧版服务与迁移机制以当前代码为准更新。图描述已交付关系，不表示服务此刻正在运行。[记忆方案图](../tasks/20261106-memory-system/diagrams.md) 单独维护。

## 路径与读图约定

| 代号 | 位置与含义 |
| --- | --- |
| R | 本源码仓库：`D:/project/20261106 memsys` |
| E | 当前 active 工程：`R/experiments/20261106-basepack` |
| Ic | core/jobs 安装包：`C:/Program Files/Python313/Lib/site-packages/basepack` |
| Is | embedding 安装包：`C:/ProgramData/basepack/envs/service/Lib/site-packages/basepack` |
| A | 本机共享设施：`D:/AgentTools` |
| C | 本机 HTCondor：`C:/condor` |
| P、P1、P2 | 接入 basePack 的业务项目示意，彼此独立；不表示本仓库已有实例 |

箭头按标签表示构建、调用、引用、读写或所有权，不能只按相邻位置推断依赖。以下机器绝对路径是本次部署实例；公共代码通过配置定位。完整合同见[部署说明](deployment.md)。

## 1. 源码怎样成为安装与项目接入

```mermaid
flowchart TB
  subgraph source["R / E：唯一产品维护源"]
    code["E/src/basepack/<br/>代码与 project/templates/"]
    deps["E/pyproject.toml + uv.lock<br/>依赖与发行声明"]
    wheel["E/dist/r9/<br/>basepack-0.5.0-*.whl"]
    policy["E/examples/condor/<br/>60_resources.conf、70_job_transforms.conf"]
    code -->|构建| wheel
    deps -->|发行版本与依赖声明| wheel
  end
  wheel -->|普通安装 core| core["Ic：系统 Python 中的 basepack"]
  wheel -->|同版 wheel，独立服务依赖| service["Is：纯净服务环境中的 basepack"]
  policy -->|管理员单独部署| condor["C/config/ 下的站点策略"]
  core -->|init 读取安装包内模板| instance["P/.basepack/<br/>config.toml + instructions.md"]
  core -->|init 合并短指针与忽略规则| entry["P/AGENTS.md<br/>P/.gitignore"]
```

wheel 不携带 devDoc、skills、测试、示例或模型。系统 Python 和服务 Python 安装同版代码，但依赖环境各自维护；运行不从 E 或 tmp 导入。`init` 只生成接入文件，jobs 目录按使用建立，memory 仍是预留路径。依据：[路线入口](../../experiments/20261106-basepack/README.md)、[项目接入实现](../../experiments/20261106-basepack/src/basepack/project/init.py)。

## 2. 两个业务项目如何绑定共享设施

```mermaid
flowchart LR
  subgraph one["业务项目 P1"]
    cfg1["P1/.basepack/config.toml<br/>schema 2"]
    data1["P1/.basepack/jobs/<br/>本项目提交材料与日志"]
    cfg1 -->|jobs.jobs_dir，相对 P1 根| data1
  end
  subgraph two["业务项目 P2"]
    cfg2["P2/.basepack/config.toml<br/>schema 2"]
    data2["P2/.basepack/jobs/<br/>本项目提交材料与日志"]
    cfg2 -->|jobs.jobs_dir，相对 P2 根| data2
  end
  cfg1 -->|显式 --config| resolve["Ic/project/config.py<br/>每次绑定一个项目配置"]
  cfg2 -->|显式 --config| resolve
  resolve -->|runtime.python：worker 解释器| python["C:/Program Files/Python313/python.exe<br/>Ic：core/jobs"]
  subgraph shared["机器级共享设施"]
    machine["A/basepack.toml<br/>schema 1：机器配置"]
    machine -->|embedding.model_root| model["A/models/Qwen/Qwen3-VL-Embedding-2B/<br/>revision/model.lock.json + model/"]
    machine -->|shared.state_dir| state["A/state/basepack/<br/>embedding/logs/"]
    machine -->|embedding.endpoint| http["127.0.0.1:8765<br/>共享 embedding HTTP 入口"]
    machine -->|htcondor.bin_dir、config_file| condor["C/bin/<br/>C/condor_config"]
  end
  resolve -->|runtime.machine_config| machine
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
  scheduler -->|启动配置指定的 Python| worker["Ic/jobs/worker.py<br/>UTF-8 参数桥接"]
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
  caller["P 中的 CLI / EmbeddingClient<br/>Ic/embedding/client.py"]
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

单推理 worker 不等于单个系统进程，LitServe 还使用 Manager 等辅助进程。模型常驻，不随客户端超时退出；排队期限不打断已开始推理。worker 故障由 LitServe 重建，主进程或 Shawl 故障后服务停止，由管理员手动启动；停止按 SCM → Shawl 整树回收。向量语义身份由模型和编码合同决定，部署路径不属于该身份。依据：[service.py](../../experiments/20261106-basepack/src/basepack/embedding/service.py)、[生命周期与接口](modules/resources.md)、[实际交付](../archive/20261107-resource-coordination/r9-result.md)。

## 5. 产品源码内部怎样分工

```mermaid
flowchart LR
  main["E/src/basepack/\_\_main\_\_.py<br/>CLI 分发"]
  main -->|init| init["project/init.py<br/>读取 project/templates/"]
  main -->|config show / 项目调用| config["project/config.py<br/>ProjectConfig / MachineConfig"]
  main -->|doctor| doctor["project/doctor.py<br/>只读诊断"]
  main -->|embed / embedding| ecli["embedding/cli.py"]
  main -->|jobs| jcli["jobs/cli.py"]
  ecli -->|请求| eclient["embedding/client.py<br/>公开 HTTP 客户端"]
  ecli -->|status / stop| manage["embedding/admin.py<br/>健康端点 / SCM 控制"]
  ecli -->|serve| serve["embedding/service.py<br/>薄 LitAPI + LitServe"]
  serve -->|编码与语义身份| model["embedding/qwen3_vl.py<br/>embedding/identity.py"]
  jcli -->|普通任务| jclient["jobs/client.py<br/>CondorClient"]
  jclient -->|生成标准提交材料| submit["jobs/submit.py<br/>JobSpec / Condor 字段"]
  submit -->|job.sub 指定启动模块| worker["jobs/worker.py<br/>Condor 启动的执行入口"]
  ecli -->|解析机器配置| config
```

图列主要调用与材料关系，不枚举每个 import；项目命令从 `__main__` 取得解析后的配置再交给对应模块。当前没有 memory 模块、记忆命令或数据库。旧自写 HTTP/supervisor/worker 登记、私有 RPC 和 `migrate` 已从 0.5.0 退役，历史材料见资源归档。依据：[源码入口](../../experiments/20261106-basepack/src/basepack/__main__.py)、[架构边界](architecture.md)。

## 6. 开发文档、skills 与临时材料放在哪里

```mermaid
flowchart TB
  entry["R/AGENTS.md + README.md<br/>按问题进入相关材料"]
  entry -->|目标与取舍| charter["R/devDoc/project-charter.md<br/>用户目标；修改正文须同意"]
  entry -->|了解已交付实现| system["R/devDoc/system/<br/>概览、架构、部署、模块、框图"]
  entry -->|继续开发| tasks["R/devDoc/tasks/<br/>计划、调查、进度与结果"]
  tasks -->|任务结束后整体归档| archive["R/devDoc/archive/<br/>历史条件和证据"]
  entry -->|产品与执行入口| route["E/README.md → E/docs/<br/>用户与管理员流程"]
  entry -->|结构建议 / 组织分工| general["R/skills/<br/>file-structure、agent-team"]
  route -->|资源操作指引| resources["E/skills/resources/"]
  general -->|本机发现联接| junction["R/.agents/skills/<br/>指向各 skill 的唯一维护源"]
  resources -->|本机发现联接| junction
  junction -->|宿主读取 skill| host["宿主 agent / subagent<br/>实际派发、模型与权限由宿主提供"]
  tasks -->|一次性试验| temp["R/tmp/任务名/<br/>可随时清除，Git 忽略"]
  temp -->|选留复核原证| evidence["R/artifacts/runs/运行ID/<br/>长期原证，Git 忽略"]
  evidence -->|链接条件与结论| tasks
  system -->|按次记录已发生变化| changes["R/devDoc/change_log/<br/>major / minor"]
```

skill 是指令与参考，不是装入 wheel 的 Python 模块；发现联接也不是另一份维护源。系统事实随实际实现更新，计划只在 tasks，结束材料进 archive；图和叙述冲突时应回查唯一源码/配置与验收条件。依据：[文档约定](../documentation.md)、[结构说明](architecture.md)、[环境与发现入口](environment.md)。
