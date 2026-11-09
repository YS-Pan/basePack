# basePack

`20261106-basepack` 是本项目当前唯一 active 路线，提供 basepack 0.5.0：多个项目共用一套本地多模态 embedding，并通过 HTCondor 排队执行 CPU/GPU 重任务。项目配置、工具产物和作业记录集中在各自的 `.basepack/`。

本路线面向 Windows、Python 3.13 和单张 NVIDIA GPU。Sentence Transformers 编码现有 Qwen3-VL-Embedding-2B 权重，LitServe 管理单个常驻推理 worker，Shawl 托管 Windows 服务。普通作业使用官方 GPU 申请字段，容量与队列由 HTCondor 管理。记忆检索、建图和数据库由独立的 [记忆任务](../../devDoc/tasks/20261106-memory-system/plan.md) 接续；本机实际安装及验收状态见 [资源进度](../../devDoc/archive/20261107-resource-coordination/progress.md)。

管理员先按 [部署说明](docs/administrator.md) 准备机器配置、共享服务及 Condor。业务项目普通安装客户端 wheel 后接入：

```powershell
python -m pip install '<basepack-wheel>'
python -m basepack init --project-root '<project>' --machine-config '<absolute-machine-config>'
python -m basepack --config '<absolute-project>/.basepack/config.toml' config show
python -m basepack --config '<absolute-project>/.basepack/config.toml' embed --text '待编码文本'
python -m basepack --config '<absolute-project>/.basepack/config.toml' jobs run --spec '<job.json>'
```

业务项目无需复制模型或环境。embedding 客户端只连接服务；`--timeout` 结束调用方等待，服务端已开始的推理仍可继续。原生 Condor 用户继续使用 `request_gpus = 1` 和 `gpus_minimum_memory = <峰值> MB`，无需安装 basePack。

[项目接入](docs/setup-project.md) 说明配置与换路径；[资源使用](docs/resources.md) 给出图文 embedding、jobs 和 Python API；[管理员说明](docs/administrator.md) 负责安装、服务控制、升级及回退。agent 可使用 [resources skill](skills/resources/SKILL.md)。0.4.0 项目保持 schema 2；更早项目先用保留的 0.4.0 wheel 完成迁移，再升级。

从仓库根开发和构建时，显式指定本路线，使用选定的 Python 3.13：

```powershell
$buildTemp = Join-Path (Get-Location) 'tmp/basepack-build'
New-Item -ItemType Directory -Force -Path $buildTemp | Out-Null
$env:TEMP = $buildTemp
$env:TMP = $buildTemp
$route = Join-Path (Get-Location) 'experiments/20261106-basepack'
$env:UV_PROJECT_ENVIRONMENT = Join-Path (Get-Location) 'tmp/basepack-dev'
uv sync --project $route --python 3.13 --locked --extra embedding --extra dev
$devPython = Join-Path $env:UV_PROJECT_ENVIRONMENT 'Scripts/python.exe'
& $devPython -c "import basepack; print(basepack.__file__)"
& $devPython -m pytest -c 'experiments/20261106-basepack/pyproject.toml' 'experiments/20261106-basepack/tests' --basetemp 'tmp/basepack-pytest'
uv build --project $route --wheel --out-dir (Join-Path $route 'dist/<build-id>')
```

服务依赖由 [pyproject.toml](pyproject.toml) 和 [uv.lock](uv.lock) 维护，CUDA PyTorch 发行源显式固定为 cu128；共享服务环境的准备见管理员说明。源码回归应加载本路线 `src/basepack/`，普通 wheel 验证应从源码外加载本次安装的包。先核实际导入位置；同一解释器保留一种有效安装。开发环境、构建缓存和测试夹具放根 `tmp/`，正式服务使用稳定共享环境；交付与回滚 wheel 留在本路线 `dist/`。

开发规则见根 [AGENTS.md](../../AGENTS.md)，现行结构和部署合同见根 [system](../../devDoc/system/overview.md) 与 [deployment](../../devDoc/system/deployment.md)。计划、进度和结果只在根 `devDoc/` 维护；项目及路线索引见根 [README](../../README.md)。
