# basePack

`20261106-basepack` 是本项目当前唯一 active 路线。basepack 0.6.2 提供项目局部记忆、共享图文 embedding 与 HTCondor 重任务协调。每个项目在自己的 `.basepack/` 保存配置、知识、原文依据和作业记录；通用程序与模型可以共用。

记忆使用 SurrealDB 4，文件摘要、实际章节、智能原文块及图片均可直接检索和作为图节点。宿主订阅 agent 同读完成分块、摘要、识图、关系与评分；程序核原文版本并原子提交，保留更正与旧依据。任务启动的 brief 交付必保留信息、项目地图、相关线索与变化，宿主按预算维护受影响的小批。默认混合检索融合跨层全文与兼容图文向量，文字模式可独立运行。流程见 [记忆使用](docs/memory.md)，完整验收状态见 [记忆进度](../../devDoc/tasks/20261106-memory-system/progress.md)。

本路线面向 Windows、Python 3.13；图文编码复用单张 NVIDIA GPU 上的 Qwen3-VL-Embedding-2B、Sentence Transformers 与 LitServe 常驻服务，普通作业由 HTCondor 排队。0.6.2 客户端兼容已有 0.5.0 embedding 服务的协议与语义身份，客户端升级无需重新加载共享模型。资源部署基线见 [R9 结果](../../devDoc/archive/20261107-resource-coordination/r9-result.md)。

按 [部署说明](docs/administrator.md) 准备所需设施。下面 python 指选定的客户端解释器；接入后使用项目 instructions 记录的实际路径：

```powershell
python -m pip install '<basepack-wheel>'
python -m basepack init --project-root '<project>' --machine-config '<absolute-machine-config>'
python -m basepack --config '<absolute-project>/.basepack/config.toml' config show
```

启用记忆前，按 [部署说明](docs/administrator.md#项目-surrealdb) 为这个项目启动独立数据库进程，并提供配置指定的密码环境变量；普通用户进程即可供同项目多个聊天共用：

```powershell
python -m basepack --config '<absolute-project>/.basepack/config.toml' memory init
python -m basepack --config '<absolute-project>/.basepack/config.toml' memory guide
python -m basepack --config '<absolute-project>/.basepack/config.toml' memory brief --task '当前任务'
```

项目也可单独使用资源工具：

```powershell
python -m basepack --config '<absolute-project>/.basepack/config.toml' embed --text '待编码文本'
python -m basepack --config '<absolute-project>/.basepack/config.toml' jobs run --spec '<job.json>'
```

业务项目无需复制模型或环境。embedding 客户端只连接服务；`--timeout` 结束调用方等待，服务端已开始的推理仍可继续。原生 Condor 用户继续使用 `request_gpus = 1` 和 `gpus_minimum_memory = <峰值> MB`，无需安装 basePack。

[项目接入](docs/setup-project.md) 说明配置与换路径；[资源使用](docs/resources.md) 给出图文 embedding、jobs 和 Python API；[管理员说明](docs/administrator.md) 负责安装、服务控制、升级及回退。记忆操作 skill 随包安装，由 `memory guide` 定位；资源任务使用 [resources skill](skills/resources/SKILL.md)。项目格式保持 schema 2，机器格式保持 schema 1；更早项目先用保留的 0.4.0 wheel 完成迁移。

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
