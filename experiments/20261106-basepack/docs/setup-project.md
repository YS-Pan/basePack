# 项目接入

按根 [安装步骤](../../../README.md#安装轻量客户端) 安装 basepack 0.6.4 客户端；可使用稳定的独立 Python 3.13 环境。文字记忆只需要客户端和每项目独立的 SurrealDB。图文检索再准备共享 embedding，普通重任务再准备 HTCondor，设施来源与安装见 [管理员说明](administrator.md)。

## 首次接入

机器配置是显式选择的本地 TOML 文件。纯文字路径只需 `schema_version = 1`；下面在用户自己的本地应用数据目录新建该文件，已有机器配置时沿用其路径，跳过新建步骤：

```powershell
$machineDir = Join-Path $env:LOCALAPPDATA 'basePack'
New-Item -ItemType Directory -Force -Path $machineDir | Out-Null
$machineConfig = Join-Path $machineDir 'text-only.toml'
New-Item -ItemType File -Path $machineConfig -Value 'schema_version = 1' -ErrorAction Stop | Out-Null
```

需要额外设施时，按管理员说明在该文件添加对应节。完整机器模板可从已安装包读取：

```powershell
& $python -c "from basepack.project.init import template; print(template('machine.toml'))"
```

每个新项目执行一次。下面的 `bp` 在原生命令失败时立即停止当前脚本；本页后续命令沿用同一 PowerShell 中的函数。`-X utf8` 保证 Python 取证输出为 UTF-8：

```powershell
$python = '<installed-client-python.exe 的绝对路径>'
$project = '<absolute-project>'
$OutputEncoding = [Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = $OutputEncoding
function bp {
    & $python -X utf8 -m basepack @args
    if ($LASTEXITCODE -ne 0) { throw "basepack failed ($LASTEXITCODE)" }
}
bp init --project-root $project --machine-config $machineConfig
$config = Join-Path $project '.basepack/config.toml'
bp --config $config config show
bp --config $config doctor
```

init 从安装包生成 `.basepack/config.toml` 和 `.basepack/instructions.md`，写入当前 Python 路径；根 AGENTS 只合并指向详细入口的短指针，原业务指令保留，Git 忽略整个 `.basepack/`。配置或入口已存在时直接报错。自定义配置可传 `--config-name .basepack/config/local.toml`，必须在 `.basepack/` 内；入口记录实际文件，project.root 按深度生成。调用显式传配置路径，不向父目录搜索。

项目配置使用 schema 2，机器配置使用 schema 1，完整字段以 [项目模板](../src/basepack/project/templates/project.toml) 为准。`runtime.python` 与 `runtime.machine_config` 必须是绝对路径；`project.root` 相对项目配置文件。`[jobs].jobs_dir`、`[memory].data_dir` 相对项目根，并位于 `.basepack/` 内。机器相对路径以机器文件所在目录为基准。各功能只读取自身必需节：只用 embedding 无需 memory 或 Condor 配置，只用 jobs 无需模型配置。init 不预建数据库或作业目录。

`config show` 返回配置位置、Python、安装身份、已解析路径、memory 设置及 agent 模型等级映射。`doctor` 默认只读检查 core，适合纯文字项目；按能力显式选择 `--facility embedding`、`--facility condor` 或 `--facility all`。它不测试数据库读写、模型推理或真实作业，这些使用结果需另行核验。

Python 入口为 `basepack.project.config.load_project_config`、`load_machine_config`、ProjectConfig 和 MachineConfig。embedding 使用 `EmbeddingClient(project.machine)`，普通作业使用 `CondorClient(project)`，具体调用见 [资源使用](resources.md)。共享机器管理不需要项目配置：

```powershell
& $python -X utf8 -m basepack embedding --machine-config '<absolute-machine-config>' status
```

## Agent 模型等级

项目配置 `[ai]` 中 `default_tier` 默认 `tier3`，`retrieval_tier` 默认 `tier1`；`[ai.tiers.tier1]` 至 `[ai.tiers.tier4]` 分别维护 `model` 和 `reasoning_effort`。初始值以 [项目模板](../src/basepack/project/templates/project.toml) 为准，可按宿主可用模型调整。已有项目配置升级时，从模板补入 `[ai]` 和各等级。

```powershell
bp --config $config config show
bp --config $config config ai
bp --config $config config ai --purpose retrieval
bp --config $config config ai --tier tier2
```

`config ai` 默认查询日常用途（等同 `--purpose task`），也可查询 `--purpose retrieval` 或显式等级；多轮检索、筛选和重排序使用检索用途。宿主读取结果后向其 agent 派工接口实际传入 `model` 和 `reasoning_effort`；basepack 不自行调用模型。

## 启用记忆

在 `memory init` 前，先核项目配置的 `[memory]`，为本项目选定独立的 `data_dir`、`endpoint` 和 init 生成的 `project_id`。新项目 `search_mode = 'text'` 可直接用于纯文字记忆；图文设施已准备好时再选择 `hybrid` 或 `vector`。`memory search` 未传 `--mode` 时取项目值，显式 `--mode` 只覆盖本次查询。模板的 18080 是待选择的默认端口；若已有项目占用它，编辑新项目 endpoint。例子中两个项目可以共用 exe、namespace/database 和共享模型服务，但各自使用下列值：

| 项目 | memory.data_dir 的实际位置 | memory.endpoint | memory.project_id |
| --- | --- | --- | --- |
| A | `<project-A>/.basepack/memory` | `http://127.0.0.1:18080` | A 的 init 生成的 UUID |
| B | `<project-B>/.basepack/memory` | `http://127.0.0.1:18081` | B 的 init 生成的另一 UUID |

按 [项目 SurrealDB](administrator.md#项目-surrealdb) 创建密码、launcher 与日志并启动。示例从目标配置读取 endpoint，普通用户隐藏进程可供同项目多聊天共用，SCM 托管是可选项。启动调用结束后，在下一次独立调用检查 `/ready`；确认可用并按下节加载凭据后执行：

```powershell
bp --config $config memory init
bp --config $config memory guide
bp --config $config memory brief --task '当前任务'
```

memory init 才安装 schema、绑定数据库身份，并把凭据、数据库接续、brief 与已安装 skill 的入口加入项目 instructions；普通 init 不启动服务、不建库。误连另一 UUID 的库会失败，保留 UUID 随本项目移动与恢复。由宿主实际读取并执行入口，才会取得启动信息。首建、检索、任务内小批维护与恢复见 [记忆使用](memory.md)。配置 source_scope 后，启动快检也发现声明范围内的新增文件；默认只检查已登记原件。

## 凭据与新 shell 接续

`[memory].password_env` 指定传给客户端的进程环境变量名。密码文件默认是当前 `memory.data_dir` 下的 `password.txt`；可用 `[memory].password_file` 指向项目根相对路径或绝对路径，也可沿用使用者自己的秘密来源。密码文件保留在忽略目录或受控秘密存储中。`config show` 返回解析后的 `memory_password_file`，不会输出密码。

首次 `memory init` 前，使用刚创建的项目配置绝对路径加载凭据。启用后每个新 PowerShell 或 agent 聊天从项目 `AGENTS.md` 读取 `.basepack/instructions.md`，使用其中的实际 Python 和配置绝对路径。每个调用进程先独立加载：

```powershell
$ErrorActionPreference = 'Stop'
$OutputEncoding = [Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = $OutputEncoding
$python = '<instructions 中的 Python 绝对路径>'
$config = '<absolute-project>/.basepack/config.toml'
$settings = & $python -X utf8 -m basepack --config $config config show | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw "config show failed ($LASTEXITCODE)" }
[Environment]::SetEnvironmentVariable($settings.memory.password_env, [IO.File]::ReadAllText($settings.memory_password_file), 'Process')
```

首次启用在当前 shell 执行一次：

```powershell
& $python -X utf8 -m basepack --config $config memory init
if ($LASTEXITCODE -ne 0) { throw "memory init failed ($LASTEXITCODE)" }
```

已启用项目完成凭据加载后，直接诊断、读取 brief 并检索；无需每次重新 init：

```powershell
& $python -X utf8 -m basepack --config $config doctor
if ($LASTEXITCODE -ne 0) { throw "doctor failed ($LASTEXITCODE)" }
& $python -X utf8 -m basepack --config $config memory brief --task '当前任务'
if ($LASTEXITCODE -ne 0) { throw "brief failed ($LASTEXITCODE)" }
& $python -X utf8 -m basepack --config $config memory search --text '当前主题'
if ($LASTEXITCODE -ne 0) { throw "search failed ($LASTEXITCODE)" }
```

生成入口还给出当前 memory 目录内的 `serve.ps1`、cwd、日志、`/ready` 检查和恢复步骤。端点不可用时沿该入口检查本项目进程与日志并显式启动，保持同一项目数据库供其它聊天共用。修改 memory 目录或密码文件配置后，下一次加载从 `config show` 读取新位置。

## 版本升级

0.6.3 → 0.6.4 仅补 MIT 许可证与包许可元数据，普通更新客户端即可；项目格式、配置、UUID 与数据不变，无需重启数据库或模型服务。

0.6.2 → 0.6.3 保持项目 schema 2、机器 schema 1、UUID 和记忆数据。先按 [备份步骤](memory.md#备份与恢复) 保留本项目知识与配置，再安装新客户端，并在已有 `[memory]` 明确补入 `search_mode = 'text'`、`'hybrid'` 或 `'vector'`；程序不会为旧配置静默选择。为入口准备当前 memory 目录下的 `password.txt`，或显式配置 `password_file`。按上面的独立调用示例加载凭据后，重新执行 `memory init`，幂等核 schema/UUID 并刷新 instructions 的记忆激活段；其它正文与业务尾注保留。原入口的通用说明可按 [当前模板](../src/basepack/project/templates/instructions.md) 更新。最后核 `config show`、新 shell 中的 brief 和实际检索；显式 hybrid/vector 失败保留原始错误。

较早版本从 [项目模板](../src/basepack/project/templates/project.toml) 核所需字段，资源接口升级与回滚见 [管理员说明](administrator.md#升级与回滚)。当前不提供旧项目 `migrate` 命令；历史 schema 1 项目需要先完成当时版本的迁移流程，历史说明只用于追溯，不是首次安装前提。

## 移动与重新检出

移动启用记忆的项目时，先停止该项目数据库并确认进程退出，保留配置、业务原件和完整记忆数据；按新目录调整服务 cwd、日志与 endpoint，保留 project_id 后再启动并核 read/search。也可按 [原生备份恢复](memory.md#备份与恢复) 搬迁。Python 和机器配置绑定仍须有效；已保存作业材料中的绝对路径需按新位置修复，Condor 历史不会随目录移动。新检出通过 init 重建被忽略的配置和 instructions，AGENTS 与业务源码可正常提交；知识通过对应项目备份恢复。

本路线开发安装使用 `python -m pip install -e '<repo>/experiments/20261106-basepack'`，源码位置须稳定且可供执行账户读取。普通部署构建 wheel 后安装到解释器管理的 site-packages，项目不保存包目录或 PYTHONPATH。依赖或安装元数据变化时重新安装，受影响的运行进程须按管理员流程重启。具体开发、构建和根 tmp 验证命令见 [路线 README](../README.md)。

## 问题记录与反馈

basePack 仍在开发，实际使用同时作为测试样本。外部业务项目沿自己的记录约定，无需复制本仓库 devDoc 结构；本仓库问题留在所属任务进度，无所属任务时先登记到 [重建总进度](../../../devDoc/tasks/20261106-rebuild/progress.md)。记录现象、版本、必要复现条件与处理状态，修复后补验证结果。

外部问题同时形成以下可复制草稿。证据去除密码、token 与私人材料，复现尽量使用小型公开或合成材料。由使用者提交至 [GitHub Issues](https://github.com/YS-Pan/basePack/issues)，或取得明确授权后由 agent 提交：

```text
标题：<简短问题现象>
版本与环境：basepack <版本>；Windows / Python / 所用设施版本
预期与实际：<预期结果>；<实际现象或原始错误>
最小复现：<命令、相关配置字段和必要材料，不含凭据>
当地记录：<项目内相对位置或可分享位置>
处理状态与验证：<待处理 / 已绕过 / 已修复；实际验证结果>
```
