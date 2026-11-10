# 项目接入

本文描述 0.8.0 候选；免认证方案是否采用仍待最终决定，正式 0.7.1 实例保持现状。按根 [安装步骤](../../../README.md#install-the-lightweight-client) 安装轻量客户端。项目记忆需要每项目独立的 SurrealDB 和共享 embedding 模型服务；普通重任务需要 HTCondor。设施由机器维护者按 [管理员说明](administrator.md) 准备。

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

成功时生成 `.basepack/config.toml` 和 `.basepack/instructions.md`，根 AGENTS 加入入口指针，`.basepack/` 加入 Git 忽略。`config show` 应显示选定的 Python、机器文件和项目根，doctor 返回 core 检查；独立技能还需按下节安装并核宿主发现。文件已存在时 init 报错：继续使用已有入口，或为新项目选择正确目录；保留原配置与业务指令。

项目配置使用 schema 2，机器配置使用 schema 1，字段见 [项目模板](../src/basepack/project/templates/project.toml)。每次调用显式传配置路径；`runtime.python` 与 `runtime.machine_config` 使用绝对路径，项目数据目录在本项目 `.basepack/` 内。自定义配置可传 `--config-name .basepack/config/local.toml`。init 生成入口，不启动设施或创建数据库。

启用记忆前运行 `doctor --facility embedding`，并按下节完成记忆读写；只用普通重任务时运行 `doctor --facility condor` 和 [一次小作业](resources.md#普通重任务)。doctor 报错时按原始路径、模型或资源设施错误修正对应设施。

共享模型的健康与身份可独立查询：

```powershell
& $python -X utf8 -m basepack embedding --machine-config '<absolute-machine-config>' status
```

## 独立 skills 安装与发现

`init` 只生成程序配置与入口；core doctor 检查程序接入范围。两者成功都不表示独立 skills 已安装或被宿主发现。按项目需要选择以下技能，保留完整目录及其中的参考文件：

| 技能 | 配套源码目录 | 所需设施 |
| --- | --- | --- |
| agent-team | `skills/agent-team/` | 支持 skills 与订阅 agent 的宿主 |
| file-structure | `skills/file-structure/` | 支持 skills 的宿主 |
| engineering-judgment | `skills/engineering-judgment/` | 支持 skills 的宿主 |
| resources | `experiments/20261106-basepack/skills/resources/` | 已接入的 embedding 或 HTCondor 工具 |

这些独立技能不在 wheel 内；仅安装 wheel 的使用者可另取对应版本源码中的所选目录，无需重装客户端。记忆 skill 随 wheel 安装，通过 `memory guide` 与生成的 instructions 直接定位。

1. **选择安装位置。** 新项目优先把所选完整目录复制到 `<project>/.agents/skills/<name>/`。已有 `<project>/skills/<name>/` 维护原件时，保留该维护源，在 `.agents/skills/<name>` 建立指向它的目录联接。其它宿主按其技能安装规则选择发现位置。
2. **核对已有入口。** 修改前检查同名路径；正确的完整目录或指向预期原件的联接直接复用。同名用户技能、非预期目录或指向其它目标的联接保留原状，报告路径与目标冲突后再决定处理。重复执行时先做此核对，跳过已正确安装项。
3. **复制或联接。** 下列命令只用于尚无同名入口的所选技能；正确入口已存在时直接复用并跳到第 4 步。在复制与联接中选一种，示例一次安装一个技能；尖括号替换为实际绝对路径。

新项目复制完整目录：

```powershell
$repo = '<absolute-matching-source-checkout>'
$project = '<absolute-target-project>'
$name = 'agent-team' # 替换为所选技能名称。
$source = Join-Path $repo "skills/$name" # resources 使用上表中的实验目录。
$skillRoot = Join-Path $project '.agents/skills'
$entry = Join-Path $skillRoot $name
New-Item -ItemType Directory -Force -Path $skillRoot | Out-Null
if (@(Get-ChildItem -LiteralPath $skillRoot -Force | Where-Object Name -eq $name).Count) { throw "Inspect and reuse or resolve existing skill: $entry" }
Copy-Item -LiteralPath $source -Destination $entry -Recurse
```

已有项目内维护原件时建立联接：

```powershell
$project = '<absolute-target-project>'
$name = 'agent-team'
$original = (Resolve-Path -LiteralPath (Join-Path $project "skills/$name")).Path
$skillRoot = Join-Path $project '.agents/skills'
$entry = Join-Path $skillRoot $name
New-Item -ItemType Directory -Force -Path $skillRoot | Out-Null
if (@(Get-ChildItem -LiteralPath $skillRoot -Force | Where-Object Name -eq $name).Count) { throw "Inspect and reuse or resolve existing skill: $entry" }
New-Item -ItemType Junction -Path $entry -Value $original | Out-Null
```

4. **核对入口与引用。** 查看 `Get-Item -LiteralPath $entry -Force | Select-Object FullName, LinkType, Target`，读取 `$entry/SKILL.md`，逐项确认其中相对引用的同目录文件可达。复制应包含整个技能目录；联接应指向本项目稳定的维护原件。资源 skill 的产品文档使用公开仓库链接，复制后不依赖原源码目录的层级。
5. **核对实际发现。** 在目标项目重新打开或新建聊天，核宿主的技能列表显示所选名称及项目作用域，再按名称调用或明确要求读取对应 `SKILL.md`。文件可达只能证明安装路径；未取得宿主列表时记录“安装已核，自动发现待核”。本步骤验收安装与发现，效果沿真实使用反馈维护。

复制的目录可随项目提交并在新检出后使用。目录联接按项目现有约定作为本机入口忽略，Git 保存其维护原件；新检出后按上述步骤重建联接。移动项目后重新核对联接目标。安装选择与本机入口的约定记在目标项目已有入口或维护记录中。

## Agent 模型等级

项目配置 `[ai]` 维护日常与检索默认等级，以及各等级的 `model` 和 `reasoning_effort`。初始值见 [项目模板](../src/basepack/project/templates/project.toml)，按宿主实际可用模型调整：

```powershell
bp --config $config config ai
bp --config $config config ai --purpose retrieval
bp --config $config config ai --tier tier2
```

`config ai` 默认解析日常用途；多轮检索、筛选和重排序使用 `--purpose retrieval`，专项维护分工见 [记忆使用](memory.md)。宿主向 agent 派工接口传入返回的 `model` 和 `reasoning_effort`；basepack 不自行调用理解模型。

## 启用记忆

在 `memory init` 前核项目配置的 `[memory]`，选定本项目独立的 `data_dir`、显式回环 IP 的 `endpoint`，保留 init 生成的 `project_id`。endpoint 仅支持 HTTP(S) 的 127/8 或 `::1`，不使用 localhost、域名、通配或远端地址。新项目默认 `search_mode = 'vector'`，也可选 `hybrid`；两者都需要共享编码服务。search 与 brief 的任务相关推荐使用项目检索模式，`search --mode` 只覆盖本次查询。

默认端口 18080 被占用时修改新项目 endpoint。两个项目可共用程序和共享模型服务，分别使用：

| 项目 | memory.data_dir 的实际位置 | memory.endpoint | memory.project_id |
| --- | --- | --- | --- |
| A | `<project-A>/.basepack/memory` | `http://127.0.0.1:18080` | A 的 init 生成的 UUID |
| B | `<project-B>/.basepack/memory` | `http://127.0.0.1:18081` | B 的 init 生成的另一 UUID |

按 [项目 SurrealDB](administrator.md#项目-surrealdb) 核免认证风险并创建仅回环监听的 launcher 与日志。该候选允许本机客户端及可触达端口的恶意网页写库，CORS 不阻止简单 POST，UUID 只防误连。接受该边界并启动后，在下一次独立调用检查 `/ready`，无需密码文件或环境变量，再执行：

```powershell
bp --config $config memory init
bp memory guide
bp --config $config memory brief --task '当前任务'
```

成功时 init 安装 schema、绑定数据库身份并刷新 instructions 的记忆入口；guide 返回已安装流程的位置，空库 brief 返回空结果。误连另一 UUID 会报错，应修正 endpoint 和目录，保留本项目 UUID。最后按 [最小闭环](memory.md#最小闭环示例) 写入一条知识，用所选检索模式找回并读取依据，即完成首次使用。

brief、search、read 只读上次已发布知识及其依据快照。`memory maintain` 在独立维护路径先采集可归属聊天、比较原件并完成机械小批，余下语义范围交给宿主 agent；`source_scope` 声明新增文件的发现范围。自动维护、显式手动维护和原件更新见 [记忆使用](memory.md#自动维护与手动维护)。

## Codex 项目聊天接入

Codex 宿主按项目归属默认接入可取得的聊天，不要求逐 thread 配置。宿主从当前聊天与完整项目清单取得项目 ID、其它已注册项目根，在 `init` 时自动传 `--codex-project-id`、可重复的 `--codex-other-project-root` 和 `--codex-registry-complete`；已有项目由宿主更新配置的 `[memory.codex]`。这是宿主元数据接法，Codex 项目 ID 与 basePack 的 `memory.project_id` UUID 各自保留。

首次启用或旧项目升级时，生成的 instructions 指引 Codex 宿主补齐绑定；每次维护预检刷新完整注册根。`memory maintain --codex-registry <UTF-8-JSON>` 可传入本轮的 `{project_id, other_project_roots, registry_complete:true}`，覆盖配置中的绑定用于该轮采集。非 Codex 宿主或无法取得绑定时继续文件记忆，并明确显示聊天覆盖缺口。

维护入口通过受支持的 App Server 列出 active 与 archived 聊天并分页读取正文。明确的项目 ID 优先；线程未带项目 ID 时，用项目根、Git worktree/common-dir 与宿主其它注册项目根排除冲突。不能确认的条目留在 unresolved/gaps；标题与关键词不判定归属。受管 UTF-8 导出保存在项目 `memory.data_dir/codex/`，由同一维护入口加入发现范围；无需把每个 thread 填入 `source_scope`，也不递归扫描数据库、控制文件和维护回执。

采集回执的 discovered、unresolved、gaps 和路径描述本轮原文发现与采集；`needs_semantic` 与语义回执描述仍需阅读的范围。brief 的 `codex_collection.status` 为 `unavailable`、`registry_incomplete` 或 `not_checked`，只表示绑定能力或查询未检查采集，不能证明全部聊天已入库。可取得的受支持 localImage 会作为独立原图来源保存到 codex-attachments；附件不可取得、缺少的 subagent 与归属不明范围保留缺口。当前实际验收边界见 [本轮进度](../../../devDoc/tasks/20261110-onboarding-simplification/progress.md)；附件原件、完整分叉/继承身份和全部项目聊天覆盖仍需真实使用验证。

## 新 shell 接续

0.8.0 候选不提供 memory username、password_env 或 password_file 配置，也不发送 Basic Authorization。新 shell/新聊天直接沿项目 `AGENTS.md → .basepack/instructions.md` 取得实际 Python 与配置路径，运行 brief：

```powershell
$ErrorActionPreference = 'Stop'
$OutputEncoding = [Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = $OutputEncoding
$python = '<instructions 中的 Python 绝对路径>'
$config = '<absolute-project>/.basepack/config.toml'
& $python -X utf8 -m basepack --config $config memory brief --task '当前任务'
if ($LASTEXITCODE -ne 0) { throw "brief failed ($LASTEXITCODE)" }
& $python -X utf8 -m basepack --config $config memory search --text '当前主题'
if ($LASTEXITCODE -ne 0) { throw "search failed ($LASTEXITCODE)" }
```

成功时 brief 和 search 返回已发布知识及其依据。连接失败时按生成入口检查本项目 `serve.ps1`、cwd 与日志，由项目维护者显式启动数据库。同项目多聊天共用数据库，聊天结束后保持运行。项目搬迁后更新 Python/配置绝对路径，或重新 `memory init` 刷新入口。

查编号、文件名或指定原文片段时使用 `memory search --mode hybrid --literal --text '<查找内容>'`：在 title、text 和 path 中做不区分大小写的子串查找，精确匹配优先，以 lexical_rank 标记，随后附语义候选。vector 模式不接受 `--literal`；模型或向量缺失时按原始错误修复设施或补建。

## 版本升级

先按 [备份步骤](memory.md#备份与恢复) 保留知识、配置和原件恢复集合，再由客户端维护者安装新包。已有配置保持 schema 2、机器 schema 1 和原 UUID。

0.8.0 收敛了以下调用合同，升级前核对自己的 Python 脚本与配置：

- 检索统一返回 `{matches, vector_coverage}`，从 `matches` 取候选；删除 `include_coverage` 参数及裸列表返回格式。
- brief 删除恒空 `changes/change_count` 与重复 `vector_pending/vector_pending_count`，保留 `vector_coverage`、知识 pending、`coverage_gaps` 和 `change_check`；来源发现、原文采集与语义接受分别核对。
- 删除 `MachineConfig.state_dir`、机器模板 `[shared].state_dir` 及其回显。embedding 日志仍由 SCM/Shawl 服务定义指定，jobs 仍使用项目 `jobs_dir`，不用搬迁日志。
- 删除内部 `MemberContent/read_member` 当前原件读取接口；已发布原文通过 `memory read` 或 `SurrealMemory.read` 读取对应快照及显式 `source_version`。

`memory guide/rank/stop` 无需 `--config`；项目动作仍需配置。独立 skills 的发行与安装合同不变，升级客户端不会替目标项目安装它们。

升级到 0.7.1 前先确认共享模型服务可用。旧 text 项目用显式 vector 查询核已发布活跃范围的向量覆盖：

```powershell
bp --config $config memory search --mode vector --text '<代表性主题>'
```

`vector_coverage` 的 total 与 compatible 相等且 pending 为 0 时，直接复用索引，将配置 `search_mode` 改为 `vector` 或 `hybrid`。有缺口或没有兼容向量时先运行 `memory embed` 补建，再查询确认覆盖；其 pending 还可能包含待语义维护的旧 stale 项，以查询返回的已发布活跃范围为切换条件。模型身份变化也按此补建，不回退到纯文字模式。

采用免认证候选并进入迁移窗口后，按下面步骤一致切换；新 shell 无需加载凭据，执行 `memory init` 核 schema/UUID 并刷新入口，然后运行代表性 brief、search、read 和 neighbors。

旧配置缺少 `search_mode` 时明确补入所选模式；缺少 `[ai]` 时从 [项目模板](../src/basepack/project/templates/project.toml) 补入等级。0.8.0 候选删除 memory.username/password_env/password_file 及对应 config show 回显。资源服务升级与回滚见 [管理员说明](administrator.md#升级与回滚)。

### 从 0.7.1 认证库切换候选

本轮只交付候选代码、文档与隔离验证；正式切换须先决定采用上述免认证边界，并安排维护窗口。共用客户端的所有在用项目和调用方须同时纳入计划，避免客户端与服务认证方式错配。

1. 保留原生 export、原配置与 launcher、旧 wheel、必要回退凭据，以及业务原件、受管聊天/附件、assets。先恢复到独立目录/端口验证旧 UUID、快照、关系和兼容向量；不打开正式 store 的第二个进程。
2. 停止该项目自动维护及调用，确认停写；停止其数据库，核监听与进程树退出。逐项目操作，以原 store 和 UUID 启动候选的 loopback/unauthenticated launcher。
3. 在同一受控窗口普通升级共用客户端，删除在用配置旧凭据字段，刷新 instructions，并同步项目已有手写入口或包装脚本。不要用清库或重新总结绕过失败；按保留的 wheel/配置/launcher 和凭据回退。
4. 在没有密码环境变量与运行时密码文件的新进程中，核 init、brief/search/read/neighbors、UUID 误连拒绝及非回环 endpoint 拒绝，再恢复业务。确认回退材料已保存后移除原在用密码文件；历史备份按既有保留约定管理。

保留知识 ID、source_version、原件、stale/retired 与原 UUID；未变输入和兼容向量无需重新编码。已知外部调用方核查有明确范围，未知自定义脚本由使用者按上面的删除接口清单核对。正式迁移状态见 [本轮进度](../../../devDoc/tasks/20261110-onboarding-simplification/progress.md)。

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
