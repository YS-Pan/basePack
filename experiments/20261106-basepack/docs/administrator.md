# 机器部署与维护

本页供 Windows x64 机器维护者安装和管理共享设施。先安装轻量客户端，再准备所用能力：文字检索需要每项目独立的 SurrealDB；向量检索和图文编码需要共享模型服务；普通重任务需要 HTCondor。项目使用者从 [项目接入](setup-project.md) 开始。

## 官方来源与能力选择

| 所用能力 | 工具入口 | 首次准备 |
| --- | --- | --- |
| 客户端 | [Python](https://www.python.org/downloads/windows/) | 安装 64-bit Python；版本范围以 [包元数据](../pyproject.toml) 为准，记录解释器绝对路径 |
| 环境与锁定依赖 | [uv](https://docs.astral.sh/uv/getting-started/installation/) | 安装后重新打开终端，运行 `uv --version` |
| 项目记忆 | [SurrealDB 4.0.0](https://github.com/surrealdb/surrealdb/releases/tag/v4.0.0) | 下载原生 Windows amd64 EXE 到稳定目录并命名为 `surreal.exe`；下文使用此 EXE 的 `start` 命令 |
| 共享 embedding 托管 | [Shawl](https://github.com/mtkennerly/shawl/releases) | 解压 Windows x64 版到稳定目录 |
| 普通重任务 | [HTCondor Windows 安装包](https://htcss-downloads.chtc.wisc.edu/tarball/25.x/25.4.0/release/) | 管理员安装单机池，步骤见下文 |
| CUDA 编码与 GPU 作业 | [NVIDIA 驱动](https://www.nvidia.com/en-us/drivers/) | 安装适合 GPU 和 PyTorch CUDA wheel 的驱动，并完成下文 CUDA 编码冒烟 |

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Python 全用户安装、Shawl 注册服务和 Condor 安装需要管理员终端；用户可写目录中的客户端环境及项目数据库由普通用户维护。SurrealDB 如报告缺失 `VCRUNTIME140/MSVCP140`，按 [官方 Windows 安装说明](https://surrealdb.com/docs/running/installation/windows) 安装 Microsoft Visual C++ Redistributable。工具版本与硬件实测保留在 [开发环境](../../../devDoc/system/environment.md)。

## 安装与执行账户

在稳定目录创建独立客户端环境，普通安装仓库中的包。以下尖括号均替换为选定的绝对路径；包路径须带实验目录：

```powershell
$repo = '<absolute-cloned-repository>'
$clientEnv = '<absolute-client-environment>'
uv venv --python '<absolute-python.exe>' $clientEnv
$python = Join-Path $clientEnv 'Scripts/python.exe'
uv pip install --python $python "$repo/experiments/20261106-basepack"
Set-Location -LiteralPath '<directory-outside-repository>'
& $python -s -c "import basepack; print(basepack.__version__); print(basepack.__file__)"
& $python -m basepack --help
```

成功时导入位置在所选环境的 site-packages，`--help` 列出命令。若导入指向源码或其它环境，先修正该解释器的安装，再继续 [项目接入](setup-project.md)。也可安装已发布或自行构建的 wheel：

```powershell
uv pip install --python $python '<basepack-wheel>'
& $python -s -c "import basepack; print(basepack.__file__)"
```

共享模型服务使用独立、稳定的纯净环境。选择一个依赖分支，按工程锁安装，再安装普通包：

| 后端 | embeddingExtra | 机器 device |
| --- | --- | --- |
| CPU | `embedding-cpu` | `cpu`，或由 `auto` 选择 |
| CUDA | `embedding-cuda` | `cuda:0`，或由 `auto` 选择 |

```powershell
$env:UV_PROJECT_ENVIRONMENT = '<absolute-shared-service-env>'
$embeddingExtra = 'embedding-cpu' # CUDA 服务改为 embedding-cuda；两个分支选一个。
uv sync --project '<repo>/experiments/20261106-basepack' --python '<absolute-python.exe>' --locked --extra $embeddingExtra --no-dev --no-install-project
$servicePython = Join-Path $env:UV_PROJECT_ENVIRONMENT 'Scripts/python.exe'
uv pip install --python $servicePython --no-deps '<repo>/experiments/20261106-basepack'
& $servicePython -c "import basepack; print(basepack.__file__)"
```

CPU 与 CUDA cu128 依赖源由 [pyproject.toml](../pyproject.toml) 和 [uv.lock](../uv.lock) 维护。成功时包从服务环境的 site-packages 导入。服务环境不继承 system-site-packages；已有 MCP 2 环境可能与 LitServe 的可选 FastMCP 集成导入冲突，使用上述纯净环境解决。环境、Shawl、模型与正式日志放稳定共享目录。

模型和机器配置须对服务账户可读；Condor 执行账户须能加载客户端包、读取输入并写项目结果。下文服务定义采用 LocalSystem，普通作业使用 Condor slot 账户。首次部署用所选功能的一次编码或小作业确认实际账户可访问这些路径。

项目绑定 Python 和机器配置，代码通过正常安装使用。开发安装与构建见 [路线 README](../README.md)。

CondorClient 按机器配置的 bin_dir/config_file 调用原生命令并设置 CONDOR_CONFIG。`condor_status` 和 `condor_q` 分别检查容量与队列。遇到受限 sandbox 的 Windows SSPI 认证错误，保留原错，在获准的正常用户终端用同一配置复核；认证政策由站点管理员维护，普通作业仍按站点配置使用 slot 账户。

## 项目 SurrealDB

多个项目可共用 SurrealDB 程序，每个项目分别使用物理数据目录、端口和 init 生成的 UUID，见 [双项目示例](setup-project.md#启用记忆)。namespace/database 不能代替物理隔离。同项目多个聊天共用一个数据库进程。

下面的 `serve.ps1` 保存到配置的 memory.data_dir（默认 `.basepack/memory/`）。先创建该目录及 `logs/`，将本项目密码原文写入 `config show` 返回的 memory_password_file，限制文件读取权限。默认密码文件为 memory 目录的 `password.txt`，路径可通过 `[memory].password_file` 指定。执行账户需要读凭据、读写数据与日志。SURREAL_USER/PASS 只在新库首次启动时创建 root，重启已有库沿用原凭据。

新库尚无密码时，可生成一次随机密码而不打印；已存在的文件直接报错，避免覆盖既有库凭据：

```powershell
& $python -c "import secrets,sys; from pathlib import Path; p=Path(sys.argv[1]); p.parent.mkdir(parents=True,exist_ok=True); p.open('x',encoding='utf-8').write(secrets.token_urlsafe(32))" '<absolute-memory-password-file>'
if ($LASTEXITCODE -ne 0) { throw "Password preparation failed ($LASTEXITCODE)" }
```

替换三个绝对路径，Python 使用项目 instructions 中的实际入口；Windows PowerShell 5.1 的 `.ps1` 保存为带 BOM 的 UTF-8，以正确读取中文路径。脚本从同一个项目配置读取 endpoint、username 和数据目录；以该目录为 cwd，`surrealkv://store` 因而始终指向该项目的 store：

```powershell
$ErrorActionPreference = 'Stop'
$python = '<absolute-python.exe>'
$config = '<absolute-project-config>'
$surreal = '<absolute-surreal.exe>'
$json = & $python -X utf8 -m basepack --config $config config show
if ($LASTEXITCODE -ne 0) { throw "Cannot load project config ($LASTEXITCODE)" }
$settings = $json | ConvertFrom-Json
Set-Location -LiteralPath $settings.memory_dir
$env:SURREAL_USER = $settings.memory.username
$env:SURREAL_PASS = [IO.File]::ReadAllText($settings.memory_password_file)
& $surreal start --bind ([Uri]$settings.memory.endpoint).Authority 'surrealkv://store'
exit $LASTEXITCODE
```

普通用户启动：memoryDir 使用上述配置解析出的实际目录。日志保留标准输出与错误，返回 PID 属于 PowerShell launcher：

```powershell
$ErrorActionPreference = 'Stop'
$memoryDir = '<absolute-memory.data_dir>'
New-Item -ItemType Directory -Force -Path "$memoryDir/logs" | Out-Null
$memoryProcess = Start-Process powershell.exe -ArgumentList @('-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', ('"' + "$memoryDir/serve.ps1" + '"')) -WorkingDirectory $memoryDir -WindowStyle Hidden -RedirectStandardOutput "$memoryDir/logs/surreal.stdout.log" -RedirectStandardError "$memoryDir/logs/surreal.stderr.log" -PassThru
$memoryProcess.Id
```

启动调用结束后，在新 shell 或下一次宿主工具调用检查连接并绑定项目。每个 shell 从同一密码文件加载凭据：

```powershell
$ErrorActionPreference = 'Stop'
$python = '<absolute-python.exe>'
$config = '<absolute-project-config>'
$json = & $python -X utf8 -m basepack --config $config config show
if ($LASTEXITCODE -ne 0) { throw "Cannot load project config ($LASTEXITCODE)" }
$settings = $json | ConvertFrom-Json
Invoke-WebRequest -UseBasicParsing -Uri ($settings.memory.endpoint.TrimEnd('/') + '/ready') -ErrorAction Stop | Select-Object StatusCode
[Environment]::SetEnvironmentVariable($settings.memory.password_env, [IO.File]::ReadAllText($settings.memory_password_file), 'Process')
$settings.memory.project_id
& $python -X utf8 -m basepack --config $config memory init
if ($LASTEXITCODE -ne 0) { throw "memory init failed ($LASTEXITCODE)" }
& $python -X utf8 -m basepack --config $config memory brief --task '核对项目接入'
if ($LASTEXITCODE -ne 0) { throw "memory brief failed ($LASTEXITCODE)" }
```

成功时 `/ready` 返回 200，init 和 brief 返回本项目数据，再按 [最小记忆闭环](memory.md#最小闭环示例) 写入并读回一条知识。连接失败先查 stdout/stderr；若隐藏进程被宿主回收，在普通用户终端前台运行同一 serve.ps1，核路径、cwd、账户和权限并使用可存续的启动方式。同一 store 只启动一个进程。

需要 SCM 托管时，管理员可为同一 launcher 注册服务，替换服务名和路径：

```powershell
$shawl = '<absolute-shawl.exe>'
$memoryDir = '<absolute-project>/.basepack/memory'
$memoryService = '<unique-project-service-name>'
& $shawl add --name $memoryService --no-restart --kill-process-tree --stop-timeout 3000 --log-dir "$memoryDir/logs" --cwd $memoryDir -- powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "$memoryDir/serve.ps1"
Set-Service -Name $memoryService -StartupType Manual
Start-Service -Name $memoryService
```

launcher 绑定所选 loopback endpoint；执行账户须能读写项目目录。SCM 启动后执行相同的连接和知识读写检查。

停止手动进程时确认所属进程树与监听端口退出；SCM 方式使用 Stop-Service 并等待 Stopped。项目搬迁后更新 cwd/launcher 与日志位置，保留 project_id。原生 export、必要 assets、配置与业务原件共同构成恢复集合，步骤见 [备份恢复](memory.md#备份与恢复)。

## 首次准备图文模型

向量检索与图文编码使用同一 Qwen3-VL-Embedding-2B 模型，CPU 和 CUDA 都采用 FP16。机器配置 `device = 'auto'` 在 PyTorch 可用 CUDA 时选择 `cuda:0`，否则选择 CPU；也可显式设为 `cpu` 或 `cuda:0`。CPU 不要求 NVIDIA 工具或 GPU 预算。CUDA 需要与锁定 cu128 wheel 兼容的驱动及下文显存预算。实际加载或 OOM 失败时按原始错误调整设备、预算或支持负载。

将模型放仓库外的稳定共享目录，选定一个新目录作为机器配置的 model_root。运行 [准备脚本](../examples/prepare_embedding_model.py)：它只编排官方 `hf download`、`hf cache verify` 和本机锁文件生成；下载与恢复由官方工具负责，校验失败直接保留原错。

```powershell
$modelRoot = '<absolute-shared-model-root>'
$hf = Join-Path $env:UV_PROJECT_ENVIRONMENT 'Scripts/hf.exe'
& $servicePython '<repo>/experiments/20261106-basepack/examples/prepare_embedding_model.py' $modelRoot --hf $hf
if ($LASTEXITCODE -ne 0) { throw "Model preparation failed ($LASTEXITCODE)" }
```

固定 revision 为 [`9f2f7e710d6d81056aa5c0a4f04764fec6bb7bda`](https://huggingface.co/Qwen/Qwen3-VL-Embedding-2B/tree/9f2f7e710d6d81056aa5c0a4f04764fec6bb7bda)。脚本依次执行官方 `hf download` 和 `hf cache verify`；缺件或 hash 错误时沿官方工具输出修复模型，再重新准备。

准备结果为：

```text
model_root/
  model.lock.json
  model/
    config.json
    model.safetensors
    1_Pooling/config.json
    ...其它固定 revision 文件及官方工具缓存
```

成功时生成 `model.lock.json` 和完整 `model/`。保留已投用的锁，推理从本地加载。模型清单变化会改变 embedding_identity，须按新身份补建向量；锁格式和生成规则由 [准备脚本](../examples/prepare_embedding_model.py) 维护。

从包内机器模板创建配置，将 model_root 指向该目录，选择 CPU 线程和支持负载。使用 CUDA 时，管理员在开放共享前将 `gpu_memory_mib` 改为正 MiB 预算，并配置普通 GPU 池：

1. 首次标定期间先不开放 Condor GPU 作业。记录物理显存 T、桌面及其它常驻程序的峰值，再扣留安全余量，给 embedding 一个能容纳模型和测试负载的正预算 E；E 小于 T。CPU 线程、max_length、max_pixels 和 batch_size 一起确定支持负载。
2. 按 [共享服务与身份](#共享服务与身份) 启动服务。在另一终端用 `nvidia-smi --query-gpu=timestamp,memory.used,memory.total --format=csv -lms 250` 采样，按承诺负载编码文本批次和图片，记录峰值和服务日志；OOM 时调整预算或负载。
3. 根据加载及编码全过程峰值确定背景总预留 B，含 embedding、其它程序、非 PyTorch CUDA 开销及余量。普通 GPU 池 G = T − B，只有 G 为正且能容纳目标作业时才开放；再测 embedding 与声明峰值的实际 GPU 作业并存。E 只控制 PyTorch 分配器，不能代替外部全卡峰值。WDDM 下 CUDA free 不代表全卡空闲。

这项共享预算由管理员维护。普通用户只运行所选后端的一次编码冒烟，兼容回归和峰值研究由开发者按对应任务执行。

## Condor 容量与策略

只在需要普通重任务时安装，CPU 作业不要求模型或 NVIDIA GPU。按 [官方 Windows 单机安装](https://htcondor.readthedocs.io/en/25.0/getting-htcondor/install-windows-as-administrator.html)，管理员运行上表 MSI：创建新池并命名，允许 submit jobs，执行策略选择 always run jobs，禁用 VM universe，选择稳定安装目录。这台机器同时承担 central manager（collector/negotiator）、submit（schedd）和 execute（startd），安装器启动 `Condor` 后台服务；后续若处于 Stopped，再由管理员 `Start-Service -Name Condor`。

普通作业容量和调度由 Condor 管理，运行时无需调用 basePack。以下以安装器常用 `C:/condor` 为例，实际目录写入机器配置的 htcondor.bin_dir/config_file。在正常用户终端先分别核状态与队列：

```powershell
$condorBin = '<absolute-condor-bin>'
$env:CONDOR_CONFIG = '<absolute-condor_config>'
& "$condorBin/condor_version.exe"
& "$condorBin/condor_config_val.exe" DAEMON_LIST
& "$condorBin/condor_status.exe" -json
& "$condorBin/condor_q.exe" -json
```

DAEMON_LIST 应包含 MASTER、COLLECTOR、NEGOTIATOR、SCHEDD、STARTD；状态能看到执行节点，空队列可正常返回。容量和队列各自必须成功。受限 sandbox 的 SSPI 错误应保留并在获准的正常用户终端复核，不能据此修改站点认证。

按这台机器的 CPU 线程数、RAM 和其它常驻程序需求确定普通作业 NUM_CPUS、MEMORY（MiB），给系统和背景服务保留余量。纯 CPU 池在本地配置目录新建 `60_resources.conf`，填写下列配置；此处 MEMORY 已是扣除背景占用后的普通池大小，RESERVED_MEMORY 因而设为 0。纯 CPU 池不加载 GPU 发现和 70 转换。

```ini
NUM_CPUS = <ordinary-CPU-threads>
MEMORY = <ordinary-RAM-MiB>
RESERVED_MEMORY = 0
NUM_SLOTS = 1
NUM_SLOTS_TYPE_1 = 1
SLOT_TYPE_1 = 100%
SLOT_TYPE_1_PARTITIONABLE = TRUE
```

需要单卡共享时，先完成上节背景峰值标定，再编辑并安装本路线两份 [样例](../examples/condor/)：

| 配置 | 职责 |
| --- | --- |
| [60_resources.conf](../examples/condor/60_resources.conf) | CPU/RAM、同卡名额、内部显存资源及 START 条件 |
| [70_job_transforms.conf](../examples/condor/70_job_transforms.conf) | schedd 标准字段转换与提交拒绝 |

将 `60_resources.conf` 中 CPU、RAM、`-repeat` 同卡作业名额和显存池改为本机预算；同卡名额是共享令牌。若 GPU 只供普通作业，也要给桌面和其它程序预留峰值。额度只在 60 定义，70 引用；合并配置时保留已有的 JOB_TRANSFORM_NAMES、SUBMIT_REQUIREMENT_NAMES 和匹配策略。

先查询主配置的 `LOCAL_CONFIG_DIR`，将改好的 60/70 放该目录；若未定义，则在主配置中显式设置 `LOCAL_CONFIG_DIR = <absolute-local-config-dir>`。按 [官方加载规则](https://htcondor.readthedocs.io/en/25.0/admin-manual/introduction-to-configuration.html)，目录内按文件名字典序加载，再加载 LOCAL_CONFIG_FILE；后者可能覆盖前面的值。核最终来源后才重载：

```powershell
& "$condorBin/condor_config_val.exe" LOCAL_CONFIG_DIR
# 在返回的目录中保存已经按本机预算改好的 60/70，再继续。
& "$condorBin/condor_config_val.exe" -config
& "$condorBin/condor_config_val.exe" -verbose NUM_CPUS MEMORY
# 以下 GPU 策略查询仅在配置了 60/70 单卡共享策略时执行。
& "$condorBin/condor_config_val.exe" -verbose MACHINE_RESOURCE_GPUMemoryMiB JOB_TRANSFORM_NAMES SUBMIT_REQUIREMENT_NAMES
& "$condorBin/condor_reconfig.exe"
& "$condorBin/condor_restart.exe" -peaceful -daemon startd
# 纯 CPU 池跳过这一整行 schedd GPU 策略查询。
& "$condorBin/condor_config_val.exe" -schedd JOB_TRANSFORM_NAMES SUBMIT_REQUIREMENT_NAMES
& "$condorBin/condor_status.exe" -json
```

这些命令针对新池；调整已有池前先暂停新提交并排空作业。成功时 `-config` 列出实际 60（GPU 共享池还需 70），最终值与本机预算一致。容量或 slot 定义变化需要重启 startd，reconfig 不会重建已有 slot。最后按 [资源使用](resources.md#普通重任务) 跑一个 CPU 作业，确认 `result.txt` 为 499500、终态 completed、exit_code 为 0、success 为 true；需要 GPU 时再跑有明确数值结果的小计算。失败保留 job ID，从输出、事件日志与 worker 回执定位。

basePack 和原生用户都提交官方 `request_gpus = 1`、`gpus_minimum_memory = <峰值> MB`。schedd 从 GPUsMinMemory 生成内部 RequestGPUMemoryMiB，并向原 Requirements 追加显存门槛，保留 RequireGPUs 及硬件筛选；CPU 作业不转换。内部资源改名只需同步站点配置，客户端不镜像额度。

本站要求显存申请在提交时可解析为正数；MB 为 MiB、GB 为 GiB，内部整数额度向上取整。省略显存时预订整池；显式 undefined、零、负值、依赖 TARGET 的动态表达式、超池或多 GPU 申请会被拒绝。有效申请在资源不足时排队。规则对本 schedd 的所有标准提交端生效。字段的设备容量筛选含义保留，累计预订来自本站策略，详见 [官方提交字段](https://htcondor.readthedocs.io/en/25.x/man-pages/htcondor-jdl.html) 和 [原生转换](https://htcondor.readthedocs.io/en/25.x/admin-manual/ap-policy-configuration.html)。

`jobs capacity` 观测父 slot 总量与剩余量，额外 MachineResources 按原名、原生单位显示。普通作业的匹配、准入和排队由 Condor 负责。显存申报量用于调度，应用仍须限制实际峰值并保留 Condor 的 CUDA_VISIBLE_DEVICES。

诊断资源分配时，collector 快照可能滞后；从 `condor_config_val STARTD_ADDRESS_FILE` 指向文件的首行取得地址，用 `condor_status -direct <address> -json` 查询 startd。GPU 的 AssignedGPUs 可为短 UUID，按前缀和原生 DeviceUuid 核对设备；回收问题结合原生终态、worker 记录的进程树和实际额度判断。

改变 CPU、slot 定义、GPU 名额或资源总量时，暂停新提交、排空作业并平稳重启 startd，再核实际发布容量；reconfig 不会重建已有 slot。只改变提交规则时按影响重载 schedd。本站配置机制及历史实测见 [R6 结果](../../../devDoc/archive/20261107-resource-coordination/native-condor.md) 和 [R7 结果](../../../devDoc/archive/20261107-resource-coordination/standard-submit-result.md)。

embedding 分配器额度由机器 `[embedding].gpu_memory_mib` 维护，独立于 Condor。模型或推理设置改变且可能影响峰值时，重新测量背景用量再调整普通池。PyTorch allocated/reserved/peak 是本进程指标；WDDM 下 CUDA free 不代表全卡其它进程占用，全卡峰值须使用外部 nvidia-smi 时间采样。动态 free 不参与准入。

## 共享服务与身份

机器 `[embedding]` 在原模型设置之外包含：

```toml
endpoint = 'http://127.0.0.1:8765'
service_name = 'BasepackEmbedding'
queue_timeout = 600
```

endpoint 是同机客户端共享的 loopback 地址。模型加载后常驻，使用一个推理 worker；客户端等待期限与 queue_timeout 的区别见 [资源使用](resources.md#共享-embedding)。

安装 [Shawl 1.9.0](https://github.com/mtkennerly/shawl/releases/tag/v1.9.0) 到稳定目录。在管理员 PowerShell 用原生命令定义服务，替换下面路径：

```powershell
$shawl = '<absolute-shawl.exe>'
$servicePython = '<absolute-service-env>/Scripts/python.exe'
$machineConfig = '<absolute-machine-config>'
$serviceName = 'BasepackEmbedding'
$serviceLogs = '<absolute-shared-log-directory>'
$serviceCwd = '<absolute-shared-directory>'
New-Item -ItemType Directory -Force -Path $serviceCwd, $serviceLogs | Out-Null
& $shawl add --name $serviceName --no-restart --kill-process-tree --stop-timeout 3000 --log-dir $serviceLogs --cwd $serviceCwd -- $servicePython -u -m basepack embedding --machine-config $machineConfig serve
Set-Service -Name $serviceName -StartupType Manual
Start-Service -Name $serviceName
```

启动后在下一次调用核健康状态、模型身份与实际 device；连接拒绝或 503 时查 serviceLogs 中的导入与模型加载日志：

```powershell
$servicePython = '<absolute-service-env>/Scripts/python.exe'
$machineConfig = '<absolute-machine-config>'
& $servicePython -m basepack embedding --machine-config $machineConfig status
```

服务健康后，使用项目配置做一次所选后端的冒烟：

```powershell
& $python -m basepack --config '<absolute-project-config>' embed --text '每周导出数据库快照' --output '<absolute-project>/.basepack/vector-smoke.json'
```

新服务 status 报告实际 device 和 dtype；CPU 路径为 `cpu`，CUDA 路径为 `cuda:0`，两者 dtype 均为 `float16`。兼容旧服务沿用其设备配置。成功时命令返回 count 为 1 与 embedding_identity，输出 JSON 含一条 2048 维向量。失败按原始连接、模型或 CUDA 错误处理；客户端等待超时后服务端推理仍可能运行，先查日志再决定下一步。

Shawl `add` 创建服务，`run` 由服务管理器调用。服务保持 Manual 启动，管理员停止后保持停止。LitServe 重建死亡的推理 worker，失败请求保留原错；主进程或 Shawl 故障时管理员查日志后用 `Start-Service` 恢复。

停止同样走服务管理器：

```powershell
& $servicePython -m basepack embedding --machine-config $machineConfig stop
(Get-Service -Name $serviceName).WaitForStatus('Stopped', [TimeSpan]::FromSeconds(30))
```

确认 Stopped、相关进程退出，CUDA 服务还需确认显存释放。正式停止使用 SCM 和 Shawl 的进程树回收；`serve` 用于前台调试。

Shawl 的 log-dir 保存包装器和服务输出。`status` 使用 `/health` 和 `/info`，model 字段包含 embedding_identity 和软件版本，新服务还报告 device/dtype。向量身份覆盖模型、前处理、精度和编码软件；设备、地址和路径不改变语义身份，同身份的 CPU/CUDA 索引可复用。

## 升级与回滚

保留旧 wheel、机器配置和各项目 [恢复集合](memory.md#备份与恢复)，待共用客户端的调用结束后普通安装新包，核实际 Python 和导入位置。0.7.0 项目入口与检索迁移见 [项目升级](setup-project.md#版本升级)。本轮共享 embedding 的 HTTP 协议与语义身份保持兼容，已有服务可继续运行；客户端升级不要求重启模型或 Condor。

更新共享模型服务时先暂停请求，经 SCM 停止并确认进程树回收，再更新独立环境和配置，启动后执行所选后端的一次编码冒烟。模型、精度或前处理合同改变时按新 identity 补建项目向量；设备或路径变化可复用同身份索引。改变 Condor 容量按上节排空和重启 startd，修改提交规则按影响重载 schedd。

回退服务先暂停请求和提交、排空作业，停止并确认整树回收后恢复保留的配置与环境。客户端回退保留项目数据；数据库格式或 schema 回退按对应版本从原生备份恢复。更早接口迁移见 [R9 结果](../../../devDoc/archive/20261107-resource-coordination/r9-result.md)。

卸载时先停止并删除 Windows 服务，再在各目标解释器运行 `python -m pip uninstall basepack`。专用服务环境及共享软件按环境管理器和保留要求清理；模型、项目数据和运行证据由各自维护者决定保留，不随客户端卸载删除。
