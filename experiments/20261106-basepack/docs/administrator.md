# 机器部署与维护

本页说明 Windows x64、Python 3.13 上的首次设施部署和维护。机器格式为 schema 1，项目格式为 schema 2。先安装轻量客户端，再按所用能力准备设施：文字记忆只需 SurrealDB；图文 embedding 再安装模型服务；普通重任务再安装 HTCondor。两项通用 skills 可独立使用，见 [路线入口](../README.md)。

## 官方来源与能力选择

下表是作者机已运行的版本及官方下载入口；首次安装命令来自官方说明，不表示已经完成空白机器重装。当前实际环境与历史验收保留在 [环境说明](../../../devDoc/system/environment.md) 和 [R9 结果](../../../devDoc/archive/20261107-resource-coordination/r9-result.md)。

| 所用能力 | 工具及已测版本 | 首次准备 |
| --- | --- | --- |
| 客户端 | [Python 3.13.17](https://www.python.org/downloads/release/python-31317/) | 下载 Windows installer (64-bit)，安装 pip；记录稳定解释器绝对路径，用 `--version` 核对 |
| 环境与锁定依赖 | [uv 0.13.7](https://docs.astral.sh/uv/getting-started/installation/) | 用下方官方固定版本安装脚本，重新打开终端后运行 `uv --version` |
| 文字记忆 | [SurrealDB 4.0.0](https://github.com/surrealdb/surrealdb/releases/tag/v4.0.0) | 下载 `surreal-v4.0.0.windows-amd64.exe` 到稳定目录并命名为 `surreal.exe`，用 `version` 核对；下文使用此原生 EXE 的 `start` 命令 |
| 共享 embedding 的 SCM 托管 | [Shawl 1.9.0](https://github.com/mtkennerly/shawl/releases/tag/v1.9.0) | 解压 `shawl-v1.9.0-win64.zip` 到稳定目录，用 `--version` 核对 |
| 普通重任务 | [HTCondor 25.4.0](https://htcss-downloads.chtc.wisc.edu/tarball/25.x/25.4.0/release/) | 管理员运行 `condor-25.4.0-Windows-x64.msi`，按下文创建单机池 |
| CUDA 图文与 GPU 作业 | [NVIDIA 驱动](https://www.nvidia.com/en-us/drivers/)；已测 617.42、RTX 4060 Ti 16380 MiB | 安装适合该 GPU 的驱动，再核 `nvidia-smi` 和实际 PyTorch CUDA 运算；服务依赖固定为 cu128 |

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/0.13.7/install.ps1 | iex"
```

Python 全用户安装、Shawl 注册服务和 Condor 安装需要管理员终端；用户可写目录中的客户端环境及项目数据库可由普通用户维护。SurrealDB 如报告缺失 `VCRUNTIME140/MSVCP140`，按 [官方 Windows 安装说明](https://surrealdb.com/docs/running/installation/windows) 安装 Microsoft Visual C++ Redistributable。该网页的新组件 CLI 使用 `surreal db start`，本页固定原生 4.0.0 EXE，不混用两套命令。

## 安装与执行账户

在稳定目录创建独立客户端环境，普通安装仓库中的包；只有 psutil 这一项运行依赖，不安装 embedding extra。以下尖括号均替换为使用者选择的绝对路径。根目录不是 Python 包，安装路径须带实验目录：

```powershell
$repo = '<absolute-cloned-repository>'
$clientEnv = '<absolute-client-environment>'
uv venv --python '<absolute-python-3.13.exe>' $clientEnv
$python = Join-Path $clientEnv 'Scripts/python.exe'
uv pip install --python $python "$repo/experiments/20261106-basepack"
Set-Location -LiteralPath '<directory-outside-repository>'
& $python -s -c "import basepack; print(basepack.__version__); print(basepack.__file__)"
& $python -m basepack --help
```

导入位置须在所选环境的 site-packages；从源码外继续 [项目接入](setup-project.md)，按所选能力运行 doctor。也可将已发布或自行构建的 wheel 普通安装到该环境：

```powershell
uv pip install --python $python '<basepack-wheel>'
& $python -s -c "import basepack; print(basepack.__file__)"
```

新建共享模型服务时，使用独立、稳定的纯净环境，按工程原生锁准备依赖，再安装普通包。兼容的既有 0.5.0 服务可继续使用；新建环境执行：

```powershell
$env:UV_PROJECT_ENVIRONMENT = '<absolute-shared-service-env>'
uv sync --project '<repo>/experiments/20261106-basepack' --python '<absolute-python-3.13.exe>' --locked --extra embedding --no-dev --no-install-project
$servicePython = Join-Path $env:UV_PROJECT_ENVIRONMENT 'Scripts/python.exe'
uv pip install --python $servicePython --no-deps '<repo>/experiments/20261106-basepack'
& $servicePython -c "import basepack; print(basepack.__file__)"
```

依赖与 CUDA cu128 发行源由 [pyproject.toml](../pyproject.toml) 和 [uv.lock](../uv.lock) 维护。服务环境不继承 system-site-packages，也不对现有系统 Python 做清理式同步。LitServe 0.2.19 会探测可选 FastMCP 集成，已有 MCP 2 环境可能触发不兼容导入；纯净服务环境只安装锁定依赖。环境、Shawl 和正式日志放稳定共享目录，开发环境和构建缓存按项目临时材料约定处理。

模型、配置和业务输入须对服务账户可读；Condor 执行账户须能加载客户端包、读取输入并写项目结果。当前服务定义采用 LocalSystem，普通作业使用 Condor slot 账户。用真实小作业验证实际账户的文件和 loopback 访问；doctor 的只读结果不能代替该验证。

项目只绑定 Python 和机器配置，代码通过正常安装使用。开发 editable 与普通 wheel 在同一解释器中只保留一种有效安装，构建入口和交付包位置见 [路线 README](../README.md)。机器模板通过 `from basepack.project.init import template` 读取，项目接入见 [说明](setup-project.md)。

CondorClient 使用机器配置的 bin_dir/config_file，向原生命令显式传 CONDOR_CONFIG。容量查询 `condor_status` 与队列查询 `condor_q` 分别核验；前者成功不能证明后者可用。受限 sandbox 的 Windows SSPI 认证可能失败；保留原错误，使用获准的正常用户上下文和同一配置复核，认证政策按站点合同维护。查询上下文与作业执行账户分别核对：正常用户查询不等于启用作业 `run_as_owner = True`，普通作业仍按站点配置使用 slot 账户。

## 项目 SurrealDB

从上表官方发行页安装原生 SurrealDB 4.0.0 EXE，多个项目可共用程序；在 `memory init` 前选定每个项目的独立物理数据目录、端口和 UUID，见 [双项目示例](setup-project.md#启用记忆)：A 使用 18080，B 使用 18081，各自保存 init 生成的 project_id。namespace/database 不能代替物理隔离。同项目多个聊天共用进程，产品通过配置定位 endpoint。

普通用户可手动启动隐藏进程。下面的 `serve.ps1` 保存到配置的 memory.data_dir（默认 `.basepack/memory/`）；先创建该目录及 `logs/`，从使用者选定的秘密来源取得本项目密码，原文写入 `config show` 返回的 memory_password_file，不添加末尾换行，并限制该文件的读取权限。省略 `[memory].password_file` 时默认为该 memory 目录的 `password.txt`；显式 password_file 可为相对项目根或绝对路径。秘密文件应放项目忽略目录或使用者的秘密位置；执行账户需要读凭据、读写数据与日志。SURREAL_USER/PASS 只在新库首次启动时创建 root，重启已有库不改密码。客户端每个新进程从同一文件加载配置中的 password_env，不能依赖部署 shell 留下的变量。

新库尚无密码时，可用项目解释器生成一次随机密码而不打印；替换为上面的实际秘密文件路径。`x` 模式在文件已存在时直接报错，不能用新密码覆盖既有库的凭据：

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
$json = & $python -X utf8 -c "import json,sys; from basepack.project.config import load_project_config; c=load_project_config(sys.argv[1]); print(json.dumps({'endpoint':c.raw['memory']['endpoint'],'username':c.raw['memory']['username'],'data_dir':str(c.memory_dir),'password_file':str(c.memory_password_file)}))" $config
if ($LASTEXITCODE -ne 0) { throw "Cannot load project config ($LASTEXITCODE)" }
$memory = $json | ConvertFrom-Json
Set-Location -LiteralPath $memory.data_dir
$env:SURREAL_USER = $memory.username
$env:SURREAL_PASS = [IO.File]::ReadAllText($memory.password_file)
& $surreal start --bind ([Uri]$memory.endpoint).Authority 'surrealkv://store'
exit $LASTEXITCODE
```

启动调用 A：memoryDir 是上述配置解析出的实际目录。日志分别保留标准输出与错误，返回 PID 属于 PowerShell launcher，仅供观察：

```powershell
$ErrorActionPreference = 'Stop'
$memoryDir = '<absolute-memory.data_dir>'
New-Item -ItemType Directory -Force -Path "$memoryDir/logs" | Out-Null
$memoryProcess = Start-Process powershell.exe -ArgumentList @('-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', ('"' + "$memoryDir/serve.ps1" + '"')) -WorkingDirectory $memoryDir -WindowStyle Hidden -RedirectStandardOutput "$memoryDir/logs/surreal.stdout.log" -RedirectStandardError "$memoryDir/logs/surreal.stderr.log" -PassThru
$memoryProcess.Id
```

让调用 A 完整结束，再在独立调用 B（新 shell 或下一次宿主工具调用）执行下面的检查。`/ready` 的成功只证明节点 ready；随后用目标配置 init/brief 触发 UUID 检查。每个 shell 单独加载 password_env，过程中不打印密码：

```powershell
$ErrorActionPreference = 'Stop'
$python = '<absolute-python.exe>'
$config = '<absolute-project-config>'
$json = & $python -X utf8 -c "import json,sys; from basepack.project.config import load_project_config; c=load_project_config(sys.argv[1]); print(json.dumps({'endpoint':c.raw['memory']['endpoint'],'password_env':c.raw['memory']['password_env'],'project_id':c.raw['memory']['project_id'],'data_dir':str(c.memory_dir),'password_file':str(c.memory_password_file)}))" $config
if ($LASTEXITCODE -ne 0) { throw "Cannot load project config ($LASTEXITCODE)" }
$memory = $json | ConvertFrom-Json
Invoke-WebRequest -UseBasicParsing -Uri ($memory.endpoint.TrimEnd('/') + '/ready') -ErrorAction Stop | Select-Object StatusCode
[Environment]::SetEnvironmentVariable($memory.password_env, [IO.File]::ReadAllText($memory.password_file), 'Process')
$memory.project_id
& $python -X utf8 -m basepack --config $config memory init
if ($LASTEXITCODE -ne 0) { throw "memory init failed ($LASTEXITCODE)" }
& $python -X utf8 -m basepack --config $config memory brief --task '核对项目接入'
if ($LASTEXITCODE -ne 0) { throw "memory brief failed ($LASTEXITCODE)" }
```

同项目另开调用也须能继续 brief，再按 [最小记忆闭环](memory.md#最小闭环示例) 验证知识读写。若调用 A 后进程被宿主回收，保留该次原错误与 stdout/stderr，核 exe/Python/配置绝对路径、cwd、执行账户和目录权限；在普通用户终端前台运行同一个 serve.ps1 以定位并使用可存续的启动方式。PID、ready 或 doctor 各自都不能代替这些后续调用。服务未 ready 时先查日志，不重复启动同一 store。Windows `Start-Process` 的本地与远程会话寿命有差异，见 [Microsoft 文档](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/start-process)；ready 的语义见 [SurrealDB HTTP 文档](https://surrealdb.com/docs/reference/rest-api/http-protocol#-get-ready)。

需要 SCM 托管时，管理员可为同一 launcher 注册服务，替换服务名和路径；这是可选部署方式，本轮没有创建该服务：

```powershell
$shawl = '<absolute-shawl.exe>'
$memoryDir = '<absolute-project>/.basepack/memory'
$memoryService = '<unique-project-service-name>'
& $shawl add --name $memoryService --no-restart --kill-process-tree --stop-timeout 3000 --log-dir "$memoryDir/logs" --cwd $memoryDir -- powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "$memoryDir/serve.ps1"
Set-Service -Name $memoryService -StartupType Manual
Start-Service -Name $memoryService
```

launcher 只绑定所选 loopback endpoint；执行账户须能读写项目目录。SCM 启动后也执行上面的独立 ready/init/brief 和知识检查。

手动进程由该项目维护者管理，停止时核对所属进程树与监听端口均已退出；共享 embedding 独立运行。SCM 方式使用 Stop-Service 并等待 Stopped，保持 Manual，Shawl 不自动重启。项目搬迁后更新 cwd/launcher 与日志位置，保留 project_id。原生 export、必要 assets、配置与业务原件共同构成恢复集合，步骤见 [备份恢复](memory.md#备份与恢复)。

## 首次准备图文模型

只在需要图文 embedding 时准备。当前已测硬件为一张 RTX 4060 Ti、16380 MiB；其它 GPU 和最低显存尚未验收。所选 NVIDIA GPU 必须能运行锁定的 PyTorch cu128 FP16 运算，且容纳下述实际负载。先从官方驱动页安装该卡适用的驱动；[CUDA 12.8 发行说明](https://docs.nvidia.com/cuda/archive/12.8.0/cuda-toolkit-release-notes/index.html) 列出 Windows 对应驱动 570.65，首次部署可使用该版本或更新的兼容驱动。不要仅凭 `nvidia-smi` 的 CUDA 版本判断 PyTorch 可用。

准备上文纯净服务环境后，先验证真实 CUDA 运算：

```powershell
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
& $servicePython -c "import torch; assert torch.cuda.is_available(); print(torch.__version__, torch.version.cuda, torch.cuda.get_device_name(0)); x=torch.ones((64,64),device='cuda',dtype=torch.float16); print((x@x)[0,0].item()); torch.cuda.synchronize()"
```

输出应包含实际设备、cu128 对应的 CUDA 12.8 和矩阵结果 64。无需为这些预编译 wheel 另装完整 CUDA 编译工具链；编译自定义 CUDA 扩展是另一个需求。

将模型放仓库外的稳定共享目录，选定一个新目录作为机器配置的 model_root。运行 [准备脚本](../examples/prepare_embedding_model.py)：它只编排官方 `hf download`、`hf cache verify` 和本机锁文件生成；下载与恢复由官方工具负责，校验失败直接保留原错。

```powershell
$modelRoot = '<absolute-shared-model-root>'
$hf = Join-Path $env:UV_PROJECT_ENVIRONMENT 'Scripts/hf.exe'
& $servicePython '<repo>/experiments/20261106-basepack/examples/prepare_embedding_model.py' $modelRoot --hf $hf
if ($LASTEXITCODE -ne 0) { throw "Model preparation failed ($LASTEXITCODE)" }
```

固定仓库为 `Qwen/Qwen3-VL-Embedding-2B`，revision 为 [`9f2f7e710d6d81056aa5c0a4f04764fec6bb7bda`](https://huggingface.co/Qwen/Qwen3-VL-Embedding-2B/tree/9f2f7e710d6d81056aa5c0a4f04764fec6bb7bda)。原生命令等价于 `hf download <model> --revision <revision> --local-dir <model_root>/model`，随后执行同目录的 `hf cache verify <model> --revision <revision> --local-dir <model_root>/model --fail-on-missing-files --fail-on-extra-files`；[官方 CLI 文档](https://huggingface.co/docs/huggingface_hub/guides/cli#hf-cache-verify) 说明完整性检查。校验必须通过，不能把缺件或 hash 错误视为准备成功。

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

锁文件是 UTF-8 JSON，公开合同为 `{"model":"Qwen/Qwen3-VL-Embedding-2B","hf_revision":"<完整commit>","files":[{"path":"model/config.json","bytes":1570,"sha256":"<实际文件SHA256>"}]}`。`files` 按相对 model_root 的 POSIX 路径排序，从实际文件计算大小和 SHA256；官方缓存及 `.gitattributes` 不进入模型清单。锁只在准备阶段生成，推理本地加载 `model/`，不下载或逐请求 hash。保留已投用的锁；`files` 清单内容（包括条目内额外字段）变化会改变 embedding_identity，应按新身份重建向量，不能覆盖锁后继续混用旧索引。

从包内机器模板创建自己的配置，将 model_root 指向该目录。模板的 `gpu_memory_mib = 0` 是待填写项，加载前必须改为正的 MiB 预算：

1. 首次标定期间先不开放 Condor GPU 作业。记录物理显存 T、桌面及其它常驻程序的峰值，再扣留安全余量，给 embedding 一个能容纳模型和测试负载的正预算 E；E 小于 T。CPU 线程、max_length、max_pixels 和 batch_size 一起确定支持负载。
2. 按 [共享服务与身份](#共享服务与身份) 注册并启动服务。在另一终端用 `nvidia-smi --query-gpu=timestamp,memory.used,memory.total --format=csv -lms 250` 连续采样，同时按 [资源使用](resources.md#共享-embedding) 完成真实文字和图片编码，并覆盖准备承诺的最大文本批次和图片尺寸。保存向量有限性、维数、近单位范数和服务日志；OOM 说明该预算或工作负载尚未可用。
3. 根据加载及编码全过程峰值确定背景总预留 B，含 embedding、其它程序、非 PyTorch CUDA 开销及余量。普通 GPU 池 G = T − B，只有 G 为正且能容纳目标作业时才开放；再测 embedding 与声明峰值的实际 GPU 作业并存。E 只控制 PyTorch 分配器，不能代替外部全卡峰值。WDDM 下 CUDA free 不代表全卡空闲。

验证后多个项目可连接这一份模型。新机器从头下载、首次模型加载及 GPU 并存仍须在目标硬件执行；作者已有服务的结果不能代替这些检查。

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

`60_resources.conf` 中 12 CPU、24576 MiB RAM、`-repeat 4` 和 7164 MiB GPU 池只是作者机的样例，不能原样套到新机器。替换为本机普通 CPU/RAM 预算、允许的同卡作业名额和 G；同卡名额是共享令牌，不是物理 GPU 数。若 GPU 只供普通作业而无 embedding，仍须预留桌面和其它程序的峰值。额度只在 60 定义，70 引用；保留已有的 JOB_TRANSFORM_NAMES、SUBMIT_REQUIREMENT_NAMES 和匹配策略。

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

这些命令针对新池；调整已有池前先暂停新提交并排空自己的作业，操作需要管理员权限。`-config` 必须列出实际 60（GPU 共享池还需 70），最终值与本机预算一致；改变容量或 slot 定义需要重启 startd，reconfig 不会重建已有 slot。纯 CPU 池只查询 NUM_CPUS/MEMORY，跳过两行 GPU 策略查询。最后按 [资源使用](resources.md#普通重任务) 跑一个结果为 499500 的 CPU 作业，GPU 路径再跑有明确数值结果的小计算，并核运行中的分配、终态、进程退出与容量归还。

basePack 和原生用户都提交官方 `request_gpus = 1`、`gpus_minimum_memory = <峰值> MB`。schedd 从 GPUsMinMemory 生成内部 RequestGPUMemoryMiB，并向原 Requirements 追加显存门槛，保留 RequireGPUs 及硬件筛选；CPU 作业不转换。内部资源改名只需同步站点配置，客户端不镜像额度。

本站要求显存申请在提交时可解析为正数；MB 为 MiB、GB 为 GiB，内部整数额度向上取整。省略显存时预订整池；显式 undefined、零、负值、依赖 TARGET 的动态表达式、超池或多 GPU 申请会被拒绝。有效申请在资源不足时排队。规则对本 schedd 的所有标准提交端生效。字段的设备容量筛选含义保留，累计预订来自本站策略，详见 [官方提交字段](https://htcondor.readthedocs.io/en/25.x/man-pages/htcondor-jdl.html) 和 [原生转换](https://htcondor.readthedocs.io/en/25.x/admin-manual/ap-policy-configuration.html)。

`jobs capacity` 显示父 slot 总量与剩余量，额外 MachineResources 仅在两种数值均发布时按原名、原生单位显示。客户端只检查 CPU/RAM 总量；GPU 拒绝、排队和终态由 Condor 决定。申报量不提供显存硬隔离，也不承诺吞吐提升；应用须限制线程和框架实际峰值，保留 Condor 的 CUDA_VISIBLE_DEVICES。

短作业的 collector 快照可能滞后。需要核对运行中分配与结束后额度恢复时，从 `condor_config_val STARTD_ADDRESS_FILE` 指向文件的首行取得实际地址，再用 `condor_status -direct <address> -json` 查询 startd；保留查询时刻和父子 slot。GPU 的 AssignedGPUs 可为短 UUID，需与 CUDA_VISIBLE_DEVICES 全 UUID 按前缀及原生 DeviceUuid 交叉核对。命令成功不等于作业完成或回收：同时核业务结果、Condor 终态、已知作业进程退出和额度恢复；Windows venv 可形成 worker → redirector → payload 进程链，应检查实际 payload PID。

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
$serviceCwd = '<absolute-shared-directory>'
New-Item -ItemType Directory -Force -Path $serviceCwd, $serviceLogs | Out-Null
& $shawl add --name $serviceName --no-restart --kill-process-tree --stop-timeout 3000 --log-dir $serviceLogs --cwd $serviceCwd -- $servicePython -u -m basepack embedding --machine-config $machineConfig serve
Set-Service -Name $serviceName -StartupType Manual
Start-Service -Name $serviceName
```

SCM 的 Running 只说明服务已启动；先观察 serviceLogs 中的导入、模型加载和 worker 日志，再在下一次调用核健康状态及模型身份。首次加载可能较慢，status 的连接拒绝或 503 需要结合原始日志判断，不能当作模型 ready，也不重复注册或并行启动：

```powershell
$servicePython = '<absolute-service-env>/Scripts/python.exe'
$machineConfig = '<absolute-machine-config>'
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

0.6.2 → 0.6.3：普通安装新客户端；已有项目按 [项目接入](setup-project.md) 补默认检索模式并更新生成入口，使新 shell 可独立加载凭据。保留原有项目配置、UUID、数据和兼容共享服务，不因客户端升级重启模型或 Condor。

0.6.1 → 0.6.2：已有项目从模板补入 `[ai]` 和等级映射，操作见 [项目接入](setup-project.md#agent-模型等级)。

0.6.0 → 0.6.1：保留旧 wheel、配置、UUID 与原生知识备份，普通安装新客户端，记录 wheel SHA256、实际 Python 和导入位置，再从源码外执行首次接入、特殊 ID、小批维护及恢复。共享 embedding 的 HTTP 协议和 embedding_identity 合同未变，已有 0.5.0 服务继续运行；Condor 策略保持。0.5.0 升级也沿此流程，启用记忆时补齐项目配置。回退客户端时保留项目库，旧 0.5.0 仍只提供资源工具。修改底座或知识 schema 前先保留原生 export，按相应版本验证恢复。

旧 0.4 → 0.5 的服务接口切换、回退及更早 schema 迁移见 [R9 结果](../../../devDoc/archive/20261107-resource-coordination/r9-result.md)。需要回退服务时先暂停请求与提交、排空作业，经 SCM 停止并确认整树回收，再恢复已保留的配置和环境；客户端回退保留项目数据。

卸载时先停止并删除 Windows 服务，再在各目标解释器运行 `python -m pip uninstall basepack`。专用服务环境及共享软件按环境管理器和保留要求清理；模型、项目数据和运行证据由各自维护者决定保留，不随客户端卸载删除。
