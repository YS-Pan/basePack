# 机器部署与维护

本页属于当前 active 路线 [20261106-basepack](../README.md)，说明 0.6.0 客户端、项目 SurrealDB 4 与共享资源设施的部署。面向 Windows、Python 3.13；图文模型使用单张 NVIDIA GPU。机器格式保持 schema 1，项目格式保持 schema 2。资源基线见 [R9 结果](../../../devDoc/archive/20261107-resource-coordination/r9-result.md)，记忆正式安装与试用状态见 [专项进度](../../../devDoc/tasks/20261106-memory-system/progress.md)。

## 安装与执行账户

客户端普通安装 wheel，可使用稳定的独立 Python 3.13 环境；本机 0.6.0 客户端位于 `D:/AgentTools/envs/basepack-client/`，系统及共享模型环境保持原状。若选择系统目录安装，通常需要管理员终端；核 pip 没有回落 user-site：

```powershell
python -m pip install --no-user '<basepack-wheel>'
python -s -c "import basepack; print(basepack.__file__)"
```

新建共享模型服务时，使用独立、稳定的纯净环境，按工程原生锁准备依赖，再安装普通 wheel。已有兼容的 0.5.0 服务可继续供 0.6.0 客户端使用，本次客户端升级无需重新加载模型：

```powershell
$env:UV_PROJECT_ENVIRONMENT = '<absolute-shared-service-env>'
uv sync --project '<repo>/experiments/20261106-basepack' --python '<python-3.13>' --locked --extra embedding --no-dev --no-install-project
$servicePython = Join-Path $env:UV_PROJECT_ENVIRONMENT 'Scripts/python.exe'
uv pip install --python $servicePython --no-deps '<basepack-wheel>'
& $servicePython -c "import basepack; print(basepack.__file__)"
```

依赖与 CUDA cu128 发行源由 [pyproject.toml](../pyproject.toml) 和 [uv.lock](../uv.lock) 维护。服务环境不继承 system-site-packages，也不对现有系统 Python 做清理式同步。LitServe 0.2.19 会探测环境中的可选 FastMCP 集成，已有 MCP 2 环境可能触发不兼容导入；纯净服务环境只安装锁定依赖。环境、Shawl 和正式日志放稳定共享目录，开发环境和构建缓存放根 tmp。本机服务环境选在 `C:/ProgramData/basepack/envs/service`：已实测 D 盘纯净环境的 Transformers 逐文件扫描使导入缓慢；模型仍在 D 盘，通用代码通过配置定位路径。

模型、配置和业务输入须对服务账户可读；Condor 执行账户须能加载客户端包、读取输入并写项目结果。当前服务定义采用 LocalSystem，普通作业使用 Condor slot 账户。用真实小作业验证实际账户的文件和 loopback 访问；doctor 的只读结果不能代替该验证。

项目只绑定 Python 和机器配置，代码通过正常安装使用。开发 editable 与普通 wheel 在同一解释器中只保留一种有效安装，构建入口和交付包位置见 [路线 README](../README.md)。机器模板通过 `from basepack.project.init import template` 读取，项目接入见 [说明](setup-project.md)。

CondorClient 使用机器配置的 bin_dir/config_file，向原生命令显式传 CONDOR_CONFIG。受限 sandbox 的 Windows SSPI 认证可能失败；保留原错误，在正常用户上下文复核，不因此改认证政策。

## 项目 SurrealDB

安装官方 SurrealDB 4 的发行 exe 到稳定位置，多个项目可共用程序；每个项目使用自己的物理数据目录、端口和进程。同项目多个聊天共用这个进程，namespace/database 不能代替物理隔离。本机选用 `D:/AgentTools/bin/surrealdb-4.0.0/surreal.exe`；产品配置只绑定 endpoint 与逻辑库，不写死 exe 路径。

前台命令见 [记忆启用](memory.md#启用)。普通用户也可手动启动隐藏进程供多聊天共用：以项目 `.basepack/memory/` 为 cwd，数据路径用 `surrealkv://store`。凭据从本机秘密文件读入 SURREAL_USER/SURREAL_PASS 环境后启动原生进程；basepack 客户端只读 password_env，产品配置与源码不保存密码。本机把 password.txt 与 serve.ps1 放在被忽略的 memory 目录；脚本只读取凭据并执行原生命令。

serve.ps1 使用下面的原生命令，替换 exe 路径；password.txt 保存该实例的密码原文，不添加末尾换行。文件由管理员在项目的忽略目录准备：

```powershell
$env:SURREAL_USER = 'root'
$env:SURREAL_PASS = Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'password.txt')
& '<absolute-surreal.exe>' start --bind 127.0.0.1:18080 'surrealkv://store'
exit $LASTEXITCODE
```

普通用户隐藏启动示例，保留返回 PID 供该项目维护者观察：

```powershell
$memoryDir = '<absolute-project>/.basepack/memory'
$memoryProcess = Start-Process powershell.exe -ArgumentList @('-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', ('"' + "$memoryDir/serve.ps1" + '"')) -WorkingDirectory $memoryDir -WindowStyle Hidden -PassThru
$memoryProcess.Id
```

需要 SCM 托管时，管理员可为同一 launcher 注册服务，替换服务名和路径；这是可选部署方式，本轮没有创建该服务：

```powershell
$shawl = '<absolute-shawl.exe>'
$memoryDir = '<absolute-project>/.basepack/memory'
$memoryService = '<unique-project-service-name>'
& $shawl add --name $memoryService --no-restart --kill-process-tree --stop-timeout 3000 --log-dir "$memoryDir/logs" --cwd $memoryDir -- powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "$memoryDir/serve.ps1"
Set-Service -Name $memoryService -StartupType Manual
Start-Service -Name $memoryService
```

launcher 显式绑定 loopback endpoint（本机为 `127.0.0.1:18080`），配置中的 endpoint 必须一致；执行账户须能读写项目目录。先核 `/ready`，再用实际项目配置运行 memory init/brief，随后首建和 read/search；进程启动成功不代替知识验收。调用 shell 也须提供 password_env 指定的变量。

手动进程由该项目维护者管理，停止时核对所属进程树与监听端口均已退出；共享 embedding 独立运行。SCM 方式使用 Stop-Service 并等待 Stopped，保持 Manual，Shawl 不自动重启。项目搬迁后更新 cwd/launcher 与日志位置，保留 project_id。原生 export、必要 assets、配置与业务原件共同构成恢复集合，步骤见 [备份恢复](memory.md#备份与恢复)。

## Condor 容量与策略

普通作业容量和调度由 Condor 管理，运行时无需调用 basePack。本站入口为 `C:/condor/condor_config`，加载两份配置，本路线的 `examples/condor/` 样例是维护源，机器上部署的配置仍由管理员维护：

| 配置 | 职责 |
| --- | --- |
| [60_resources.conf](../examples/condor/60_resources.conf) | CPU/RAM、同卡名额、内部显存资源及 START 条件 |
| [70_job_transforms.conf](../examples/condor/70_job_transforms.conf) | schedd 标准字段转换与提交拒绝 |

本机容量合同保持 12 CPU/24576 MiB RAM、4 个同卡名额及 7164 MiB 普通 GPU 池；背景程序合计预留 9216 MiB。4 个名额是同一物理 GPU 的共享令牌。额度只在 60 配置定义，70 引用；保留已有的 JOB_TRANSFORM_NAMES、SUBMIT_REQUIREMENT_NAMES 和匹配策略。

basePack 和原生用户都提交官方 `request_gpus = 1`、`gpus_minimum_memory = <峰值> MB`。schedd 从 GPUsMinMemory 生成内部 RequestGPUMemoryMiB，并向原 Requirements 追加显存门槛，保留 RequireGPUs 及硬件筛选；CPU 作业不转换。内部资源改名只需同步站点配置，客户端不镜像额度。

本站要求显存申请在提交时可解析为正数；MB 为 MiB、GB 为 GiB，内部整数额度向上取整。省略显存时预订整池；显式 undefined、零、负值、依赖 TARGET 的动态表达式、超池或多 GPU 申请会被拒绝。有效申请在资源不足时排队。规则对本 schedd 的所有标准提交端生效。字段的设备容量筛选含义保留，累计预订来自本站策略，详见 [官方提交字段](https://htcondor.readthedocs.io/en/25.x/man-pages/htcondor-jdl.html) 和 [原生转换](https://htcondor.readthedocs.io/en/25.x/admin-manual/ap-policy-configuration.html)。

`jobs capacity` 显示父 slot 总量与剩余量，额外 MachineResources 仅在两种数值均发布时按原名、原生单位显示。客户端只检查 CPU/RAM 总量；GPU 拒绝、排队和终态由 Condor 决定。申报量不提供显存硬隔离，也不承诺吞吐提升；应用须限制线程和框架实际峰值，保留 Condor 的 CUDA_VISIBLE_DEVICES。

改变 CPU、slot 定义、GPU 名额或资源总量时，暂停新提交、排空作业并平稳重启 startd，再核实际发布容量；reconfig 不会重建已有 slot。只改变提交规则时按影响重载 schedd。本站配置机制及历史实测见 [R6 结果](../../../devDoc/archive/20261107-resource-coordination/native-condor.md) 和 [R7 结果](../../../devDoc/archive/20261107-resource-coordination/standard-submit-result.md)。

embedding 分配器额度由机器 `[embedding].gpu_memory_mib` 维护，独立于 Condor。模型或推理设置改变且可能影响峰值时，重新测量背景用量再调整普通池。PyTorch allocated/reserved/peak 是本进程指标；WDDM 下 CUDA free 不代表全卡其它进程占用，全卡峰值须使用外部 nvidia-smi 时间采样。动态 free 不参与准入。

## 共享服务与身份

机器 `[embedding]` 在原模型设置之外包含：

```toml
endpoint = 'http://127.0.0.1:8765'
service_name = 'BasepackEmbedding'
queue_timeout = 600
```

endpoint 是同机客户端共享的固定地址；服务只绑定该 loopback 地址。模型在 LitAPI.setup 加载并常驻，单 GPU、单推理 worker 和一个可并发接入请求的 API server。请求内分批由 Sentence Transformers 处理；跨请求动态合批未启用。客户端等待期限与 queue_timeout 的区别见 [资源使用](resources.md#共享-embedding)。

安装 [Shawl 1.9.0](https://github.com/mtkennerly/shawl/releases/tag/v1.9.0) 到稳定目录。在管理员 PowerShell 用原生命令定义服务，替换下面路径：

```powershell
$shawl = '<absolute-shawl.exe>'
$servicePython = '<absolute-service-env>/Scripts/python.exe'
$machineConfig = '<absolute-machine-config>'
$serviceName = 'BasepackEmbedding'
$serviceLogs = '<absolute-shared-log-directory>'
& $shawl add --name $serviceName --no-restart --kill-process-tree --stop-timeout 3000 --log-dir $serviceLogs --cwd '<absolute-shared-directory>' -- $servicePython -u -m basepack embedding --machine-config $machineConfig serve
Set-Service -Name $serviceName -StartupType Manual
Start-Service -Name $serviceName
& $servicePython -m basepack embedding --machine-config $machineConfig status
```

Shawl 的 `add` 创建 Windows 服务，`run` 仅供服务管理器启动；不要从普通终端直接运行 `shawl run`。`--kill-process-tree` 使用 Job Object 回收整棵树。服务保持 Manual 启动；Shawl 不自动重启命令，管理员停止后保持停止。LitServe 的 `restart_workers=True` 负责推理 worker 死亡后的重建，失败请求报告错误且不重投。主进程或 Shawl 故障时整项服务停止，管理员查看日志后用 `Start-Service` 恢复。

停止同样走服务管理器：

```powershell
& $servicePython -m basepack embedding --machine-config $machineConfig stop
(Get-Service -Name $serviceName).WaitForStatus('Stopped', [TimeSpan]::FromSeconds(30))
```

`stop` 的返回只表示原生 `sc.exe stop` 已接受；确认 Stopped、相关进程退出和显存释放后才算完成。生产停止依靠 Shawl 的进程树所有权；LitServe 0.2.19 的原生 `/shutdown` 在 Windows 小试中存在进程残留，故不作为本版停止入口。`serve` 可用于前台调试，正式运行由上面的服务定义托管。

Shawl 的 log-dir 保存包装器和命令输出；推理异常保留在服务日志。`status` 使用 LitServe 原生 `/health` 和 `/info`；`/info` 的 model 字段包含 embedding_identity 及软件版本。向量身份覆盖模型 revision/文件、Sentence Transformers 版本、FP16、指令、图像预处理和 pooling；路径、线程、批次与等待期限不改变身份。0.5.0 使用新的向量身份，调用方按此处理索引兼容。

## 升级与回滚

0.5.0 → 0.6.0：保留客户端 wheel、配置与项目知识备份，普通安装新客户端，核实际安装来源，再从源码外执行记忆首建、查询、维护与恢复。共享 embedding 的 HTTP 协议和 embedding_identity 合同未变，已有 0.5.0 服务继续运行；Condor 策略保持。回退客户端时保留项目库，旧 0.5.0 仍只提供资源工具。修改底座或知识 schema 前先保留原生 export，按相应版本验证恢复。

下面是 0.4.0 → 0.5.0 的历史资源接口切换，仅从该旧版升级时使用：

1. 保留旧 wheel、机器配置和调用脚本，暂停新请求与作业提交，核当前服务和 Condor 队列，等待在途作业终结并确认回收。
2. 用仍安装的 0.4.0 执行 `python -m basepack embedding --machine-config '<machine-config>' stop`，确认旧 supervisor/worker 已退出。保留旧安装直至具备回退包和配置，按当前实际状态操作。
3. 机器配置新增 endpoint、service_name、queue_timeout，移除 idle_seconds；模型路径、GPU 预算及 Condor 策略保持。项目 schema 2 配置和业务数据保留。客户端安装 0.5.0，按上文准备纯净服务环境并安装新 wheel，再用 Shawl 创建和启动服务。
4. 调用方切换为 `EmbeddingClient(machine).embed(inputs, timeout=...)`；取消、close、request_id、tokens_only 和旧 RPC 已退役。用源码外两项目验证图文向量、CPU/GPU 结果、共享模型、超时隔离、日志与进程回收，再恢复请求和提交。

更早的项目先用保留的 0.4.0 wheel 执行其显式 `migrate --from-config '<old-config>'`，完成 schema 2 迁移后再按上文升级。0.5.0 不再提供旧项目迁移命令。

需要回退时暂停请求与提交，排空新作业；通过服务管理器停止新服务并确认整树回收。永久退回旧版时执行 `sc.exe delete '<service-name>'` 删除新服务定义；短期演练可保留处于 Stopped 的定义。恢复备份机器配置、0.4.0 wheel 和调用脚本，核旧安装来源。确认旧 supervisor 已退出后，将历史 `state_dir/embedding/broker.json` 移入升级备份，让旧服务重新登记；Windows 上启动时并发读取过期登记可能阻止原子替换。随后从作业树外用旧版 `embedding --machine-config '<machine-config>' serve` 启动并验证。项目数据与 Condor 60/70 策略无需因本次服务替换回滚。

卸载时先停止并删除 Windows 服务，再在各目标解释器运行 `python -m pip uninstall basepack`。专用服务环境及共享软件按环境管理器和保留要求清理；模型、项目数据和运行证据由各自维护者决定保留，不随客户端卸载删除。
