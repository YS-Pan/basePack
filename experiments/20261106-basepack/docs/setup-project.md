# 项目接入

按根 [安装步骤](../../../README.md#安装轻量客户端) 安装轻量客户端。项目记忆需要每项目独立的 SurrealDB 和共享 embedding 模型服务；普通重任务需要 HTCondor。设施由机器维护者按 [管理员说明](administrator.md) 准备。

## 首次接入

设置已安装客户端、项目和机器配置路径：

```powershell
$python = '<installed-client-python.exe 的绝对路径>'
$project = '<absolute-project>'
$machineConfig = '<absolute-machine-config>'
```

已有机器配置时沿用该文件。启用记忆前，由管理员配置其中的共享模型路径、服务 endpoint 和所选 CPU/CUDA 后端。完整机器模板可从已安装包读取：

```powershell
& $python -c "from basepack.project.init import template; print(template('machine.toml'))"
```

每个新项目执行一次；本页后续命令沿用同一 PowerShell 中的 `bp` 函数：

```powershell
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

成功时生成 `.basepack/config.toml` 和 `.basepack/instructions.md`，根 AGENTS 加入入口指针，`.basepack/` 加入 Git 忽略。`config show` 应显示选定的 Python、机器文件和项目根，doctor 返回 core 检查。文件已存在时 init 报错：继续使用已有入口，或为新项目选择正确目录；保留原配置与业务指令。

项目配置使用 schema 2，机器配置使用 schema 1，字段见 [项目模板](../src/basepack/project/templates/project.toml)。每次调用显式传配置路径；`runtime.python` 与 `runtime.machine_config` 使用绝对路径，项目数据目录在本项目 `.basepack/` 内。自定义配置可传 `--config-name .basepack/config/local.toml`。init 生成入口，不启动设施或创建数据库。

启用记忆前运行 `doctor --facility embedding`，并按下节完成记忆读写；只用普通重任务时运行 `doctor --facility condor` 和 [一次小作业](resources.md#普通重任务)。doctor 报错时按原始路径、模型或认证错误修正对应设施。

共享模型的健康与身份可独立查询：

```powershell
& $python -X utf8 -m basepack embedding --machine-config '<absolute-machine-config>' status
```

## Agent 模型等级

项目配置 `[ai]` 维护日常与检索默认等级，以及各等级的 `model` 和 `reasoning_effort`。初始值见 [项目模板](../src/basepack/project/templates/project.toml)，按宿主实际可用模型调整：

```powershell
bp --config $config config ai
bp --config $config config ai --purpose retrieval
bp --config $config config ai --tier tier2
```

`config ai` 默认解析日常用途；多轮检索、筛选和重排序使用 `--purpose retrieval`，专项维护分工见 [记忆使用](memory.md)。宿主向 agent 派工接口传入返回的 `model` 和 `reasoning_effort`；basepack 不自行调用理解模型。

## 启用记忆

在 `memory init` 前核项目配置的 `[memory]`，选定本项目独立的 `data_dir`、`endpoint`，保留 init 生成的 `project_id`。新项目默认 `search_mode = 'vector'`，也可选 `hybrid`；两者都需要共享编码服务。search 与 brief 的任务相关推荐使用项目检索模式，`search --mode` 只覆盖本次查询。

默认端口 18080 被占用时修改新项目 endpoint。两个项目可共用程序和共享模型服务，分别使用：

| 项目 | memory.data_dir 的实际位置 | memory.endpoint | memory.project_id |
| --- | --- | --- | --- |
| A | `<project-A>/.basepack/memory` | `http://127.0.0.1:18080` | A 的 init 生成的 UUID |
| B | `<project-B>/.basepack/memory` | `http://127.0.0.1:18081` | B 的 init 生成的另一 UUID |

按 [项目 SurrealDB](administrator.md#项目-surrealdb) 创建密码、launcher 与日志并启动。启动调用结束后，在下一次独立调用检查 `/ready`；按 [凭据加载步骤](#凭据与新-shell-接续) 加载本项目凭据，然后执行：

```powershell
bp --config $config memory init
bp --config $config memory guide
bp --config $config memory brief --task '当前任务'
```

成功时 init 安装 schema、绑定数据库身份并刷新 instructions 的记忆入口；guide 返回已安装流程的位置，空库 brief 返回空结果。误连另一 UUID 会报错，应修正 endpoint 和目录，保留本项目 UUID。最后按 [最小闭环](memory.md#最小闭环示例) 写入一条知识，用所选检索模式找回并读取依据，即完成首次使用。

brief、search、read 只读上次已发布知识及其依据快照。变化发现和维护从独立入口进行；`source_scope` 声明维护时发现新增文件的范围。自动维护、显式手动维护和原件更新见 [记忆使用](memory.md)。

## 凭据与新 shell 接续

`[memory].password_env` 指定客户端读取的环境变量名。密码文件默认为 memory 目录的 `password.txt`；可用 `[memory].password_file` 指定其它路径。密码保存在忽略目录或受控秘密存储中，`config show` 只返回路径。

首次启用和每个新 shell 都先加载凭据。启用后从项目 AGENTS 指向的 `.basepack/instructions.md` 取得实际 Python 和配置路径：

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

已启用项目加载凭据后直接查询：

```powershell
& $python -X utf8 -m basepack --config $config memory brief --task '当前任务'
if ($LASTEXITCODE -ne 0) { throw "brief failed ($LASTEXITCODE)" }
& $python -X utf8 -m basepack --config $config memory search --text '当前主题'
if ($LASTEXITCODE -ne 0) { throw "search failed ($LASTEXITCODE)" }
```

成功时 brief 和 search 返回已发布知识及其依据。缺少凭据时核密码文件和变量名；连接失败时按生成入口检查本项目 `serve.ps1`、cwd 与日志并显式启动数据库。同项目多聊天共用数据库，聊天结束后保持运行。修改 memory 目录或密码文件配置后，下次加载会读取新位置。

查编号、文件名或指定原文片段时使用 `memory search --mode hybrid --literal --text '<查找内容>'`：在 title、text 和 path 中做不区分大小写的子串查找，精确匹配优先，以 lexical_rank 标记，随后附语义候选。vector 模式不接受 `--literal`；模型或向量缺失时按原始错误修复设施或补建。

## 版本升级

先按 [备份步骤](memory.md#备份与恢复) 保留知识、配置和原件恢复集合，再由客户端维护者安装新包。已有配置保持 schema 2、机器 schema 1 和原 UUID。

升级到 0.7.1 前先确认共享模型服务可用。旧 text 项目用显式 vector 查询核已发布活跃范围的向量覆盖：

```powershell
bp --config $config memory search --mode vector --text '<代表性主题>'
```

`vector_coverage` 的 total 与 compatible 相等且 pending 为 0 时，直接复用索引，将配置 `search_mode` 改为 `vector` 或 `hybrid`。有缺口或没有兼容向量时先运行 `memory embed` 补建，再查询确认覆盖；其 pending 还可能包含待语义维护的旧 stale 项，以查询返回的已发布活跃范围为切换条件。模型身份变化也按此补建，不回退到纯文字模式。

安装新包后在新 shell 加载凭据并执行 `memory init`，核 schema/UUID 并刷新查询与维护入口，然后运行代表性 brief、search 和 read。

旧配置缺少 `search_mode` 时明确补入所选模式；缺少 `[ai]` 时从 [项目模板](../src/basepack/project/templates/project.toml) 补入等级。密码文件使用当前 memory 目录的 `password.txt` 或显式 `password_file`。资源服务升级与回滚见 [管理员说明](administrator.md#升级与回滚)。

## 移动与重新检出

移动启用记忆的项目时，先停止该项目数据库并确认进程退出，保留配置、业务原件和完整记忆数据；按新目录调整服务 cwd、日志与 endpoint，保留 project_id 后再启动并核 read/search。也可按 [原生备份恢复](memory.md#备份与恢复) 搬迁。Python 和机器配置绑定仍须有效；已保存作业材料中的绝对路径需按新位置修复，Condor 历史不会随目录移动。新检出通过 init 重建被忽略的配置和 instructions，AGENTS 与业务源码可正常提交；知识通过对应项目备份恢复。

开发安装、构建和产品回归见 [路线 README](../README.md)。

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
