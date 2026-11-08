# basePack

`20261106-basepack` 是本项目当前唯一 active 路线，提供 basepack 0.4.0：多个项目共用一套本地多模态 embedding，并通过 HTCondor 排队执行 CPU/GPU 重任务。项目配置、工具产物和作业记录集中在各自的 `.basepack/`；共享服务只加载一份模型。

本路线面向单机 Windows、单张 NVIDIA GPU，复用 Python 3.13、Qwen3-VL-Embedding-2B 权重和 HTCondor。普通作业使用官方 GPU 申请字段，容量与队列由 Condor 管理；embedding 独立运行。记忆检索、建图和数据库尚未实现，后续工作见根目录的 [记忆计划](../../devDoc/tasks/20261106-memory-system/plan.md)；资源库替换仍按 [R9](../../devDoc/tasks/20261107-resource-coordination/plan.md#r9-复用优先的资源实现) 推进。

在可供服务和 Condor 执行账户读取的 Python 中普通安装 wheel，然后接入业务项目：

```powershell
python -m pip install '<basepack-wheel>'
python -m basepack init --project-root '<project>' --machine-config '<absolute-machine-config>'
python -m basepack --config '<absolute-project>/.basepack/config.toml' config show
python -m basepack --config '<absolute-project>/.basepack/config.toml' jobs run --spec '<job.json>'
```

管理员准备机器配置和 Condor 策略，并在作业树外运行 `embedding --machine-config <file> serve`。业务项目无需复制模型或编写 Condor submit 文件。原生 Condor 用户继续使用 `request_gpus = 1` 和 `gpus_minimum_memory = <峰值> MB`，无需安装 basePack。

[项目接入](docs/setup-project.md) 说明配置、旧版本迁移与换路径；[资源使用](docs/resources.md) 给出图文 embedding、jobs 和 Python API；[管理员说明](docs/administrator.md) 负责安装、策略与服务生命周期。agent 可使用 [resources skill](skills/resources/SKILL.md)。0.3.0 项目须排空旧作业、停止旧服务并显式迁移后使用新接口。

从仓库根目录开发和构建时，显式指定本路线，使用选定的开发 Python：

```powershell
$buildTemp = Join-Path (Get-Location) 'tmp/basepack-build'
New-Item -ItemType Directory -Force -Path $buildTemp | Out-Null
$env:TEMP = $buildTemp
$env:TMP = $buildTemp
python -m pip install -e 'experiments/20261106-basepack[dev]'
python -c "import basepack; print(basepack.__file__)"
python -m pytest -c 'experiments/20261106-basepack/pyproject.toml' 'experiments/20261106-basepack/tests' --basetemp 'tmp/basepack-pytest'
python -m pip wheel --no-deps --wheel-dir 'experiments/20261106-basepack/dist/<build-id>' 'experiments/20261106-basepack'
```

源码回归应加载本路线 `src/basepack/`，普通 wheel 验证应从源码外加载本次安装的包；先核实际导入位置，避免误测已有系统安装。同一解释器保留一种有效安装，隔离验证环境、构建临时目录和 pytest 临时夹具放根 `tmp/`；pytest 不保留持久缓存。交付与回滚 wheel 留在本路线 `dist/`。

开发规则见根 [AGENTS.md](../../AGENTS.md)，现行结构和部署合同见根 [system](../../devDoc/system/overview.md) 与 [deployment](../../devDoc/system/deployment.md)。计划、进度和结果只在根 `devDoc/` 维护；本机实际安装与验收状态见 [资源进度](../../devDoc/tasks/20261107-resource-coordination/progress.md)，项目及路线索引见根 [README](../../README.md)。
