# basePack

`20261106-basepack` 是当前唯一 active 工程，源码版本为 0.7.0，面向 Windows、Python 3.13+。每个项目在自己的 `.basepack/` 保存配置、知识、原文依据和作业记录；通用程序与模型可以共用。首次安装从根 [README](../../README.md#安装轻量客户端) 的 clone、venv 和源码安装命令开始。

本项目自有源码与文档采用 [MIT 许可证](LICENSE)，与根许可证内容一致；第三方许可声明随包保留。

记忆使用 SurrealDB 4，文件摘要、实际章节、智能原文块及图片均可直接检索和作为图节点。宿主订阅 agent 同读完成分块、摘要、识图、关系与评分；程序核原文版本并原子发布内容与匹配向量。search、brief 和 read 只读已发布知识及其依据快照；维护通过独立 worker 推进，业务结束时停止未发布工作。新项目默认 vector，可按需要显式选择 text 或 hybrid。实际交付见 [整改进度](../../devDoc/tasks/20261110-rectification/progress.md)。

basePack 仍在开发，实际使用同时作为测试样本。使用问题沿自己的项目约定记录，并按 [反馈格式](docs/setup-project.md#问题记录与反馈) 形成可提交的 Issue 草稿。

## 按能力接入

| 使用路径 | 设施与入口 |
| --- | --- |
| 无模型的文字记忆 | 轻量客户端、每项目独立 SurrealDB，显式配置 text；[项目接入](docs/setup-project.md) → [数据库部署](docs/administrator.md#项目-surrealdb) → [记忆使用](docs/memory.md) |
| 图文向量 / 混合检索 | 再准备固定模型与 CPU/CUDA 共享服务；[管理员说明](docs/administrator.md) → [资源使用](docs/resources.md) |
| 普通重任务 | 再准备 HTCondor 单机 pool 与本站容量配置；[管理员说明](docs/administrator.md) → [作业使用](docs/resources.md) |
| 独立 skills | [根 README 的安装与发现步骤](../../README.md#独立-skills)；无需 Python、数据库或模型 |

图文编码复用 Qwen3-VL-Embedding-2B 常驻服务，默认优先可用 CUDA，否则 CPU；普通作业由 HTCondor 排队。设施准备见 [管理员说明](docs/administrator.md)。下面 `$python` 指已安装客户端的解释器；接入后沿用项目 instructions 记录的实际路径：

```powershell
& $python -m basepack init --project-root '<absolute-project>' --machine-config '<absolute-machine-config>'
& $python -m basepack --config '<absolute-project>/.basepack/config.toml' config show
& $python -m basepack --config '<absolute-project>/.basepack/config.toml' doctor
```

按 [数据库部署](docs/administrator.md#项目-surrealdb) 为本项目启动独立进程并在下一次调用核 `/ready`，按 [凭据步骤](docs/setup-project.md#凭据与新-shell-接续) 加载当前配置指定的密码，再调用：

```powershell
& $python -m basepack --config '<absolute-project>/.basepack/config.toml' memory init
& $python -m basepack --config '<absolute-project>/.basepack/config.toml' memory guide
& $python -m basepack --config '<absolute-project>/.basepack/config.toml' memory brief --task '当前任务'
```

启用后每个新 shell 沿 `.basepack/instructions.md` 重新加载凭据并读取 brief。纯文字路径保持 `[memory] search_mode = 'text'`；`memory search` 未传 `--mode` 时使用该值，显式 `--mode` 覆盖单次调用。完整 prepare/apply/search/read/neighbors 闭环见 [记忆示例](docs/memory.md#最小闭环示例)。项目配置、凭据、数据库和知识保持本地，不随 Git 分发。

项目也可单独使用资源工具，无需启用记忆：

```powershell
& $python -m basepack --config '<absolute-project>/.basepack/config.toml' embed --text '待编码文本'
& $python -m basepack --config '<absolute-project>/.basepack/config.toml' jobs run --spec '<job.json>'
```

业务项目无需复制模型或环境。embedding 客户端只连接服务；`--timeout` 结束调用方等待，服务端已开始的推理仍可继续。原生 Condor 用户继续使用 `request_gpus = 1` 和 `gpus_minimum_memory = <峰值> MB`，无需安装 basePack。

[项目接入](docs/setup-project.md) 说明配置、新 shell 接续、升级和换路径；[资源使用](docs/resources.md) 给出 Python API。记忆 skill 随包安装，由 `memory guide` 定位；[resources skill](skills/resources/SKILL.md)、两项通用 skills 和 examples 从源码获取，不包含在 wheel 中。

## 开发、检查与构建

从仓库根开发和构建时，显式指定本路线，使用选定的 Python 3.13：

```powershell
$buildTemp = Join-Path (Get-Location) 'tmp/basepack-build'
New-Item -ItemType Directory -Force -Path $buildTemp | Out-Null
$env:TEMP = $buildTemp
$env:TMP = $buildTemp
$env:UV_CACHE_DIR = Join-Path $buildTemp 'uv-cache'
$route = Join-Path (Get-Location) 'experiments/20261106-basepack'
$env:UV_PROJECT_ENVIRONMENT = Join-Path (Get-Location) 'tmp/basepack-dev'
uv sync --project $route --python 3.13 --locked --extra embedding --extra dev
$devPython = Join-Path $env:UV_PROJECT_ENVIRONMENT 'Scripts/python.exe'
& $devPython -c "import basepack; print(basepack.__file__)"
& $devPython -m pytest -c 'experiments/20261106-basepack/pyproject.toml' 'experiments/20261106-basepack/tests' --basetemp 'tmp/basepack-pytest'
uv build --project $route --wheel --out-dir (Join-Path $route 'dist')
```

依赖由 [pyproject.toml](pyproject.toml) 和 [uv.lock](uv.lock) 维护，CUDA PyTorch 发行源固定为 cu128；uv 来源和共享服务准备见管理员说明。源码回归应加载本路线 `src/basepack/`，普通 wheel 验证应从源码外加载本次安装的包。先核实际导入位置；同一解释器保留一种有效安装。开发环境、构建缓存和测试夹具放根 `tmp/`，正式客户端和共享服务使用稳定环境，交付与回滚 wheel 留在本路线 `dist/`。以上构建产物在本机生成，Git 中不附带作者机的 wheel、模型或运行原证；如提供下载包，使用对应 GitHub Release 附件。

开发规则见根 [AGENTS.md](../../AGENTS.md)，现行结构和部署合同见根 [system](../../devDoc/system/overview.md) 与 [deployment](../../devDoc/system/deployment.md)。计划、进度和结果只在根 `devDoc/` 维护；项目及路线索引见根 [README](../../README.md)。
