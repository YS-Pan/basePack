# 项目接入

按根 [安装步骤](../../../README.md#install-the-lightweight-client) 安装轻量客户端。项目记忆需要每项目独立的 SurrealDB 和共享 embedding 模型服务；普通重任务需要 HTCondor。设施由机器维护者按 [管理员说明](administrator.md) 准备。安装、升级或修改配置时先读 [项目配置维护要点](project-config-maintenance.md)，按受影响事件同步。

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

接入 agent 先读取宿主有效并发配置或明确报告，将上限归一化为不含主 agent、包含全部后代的 subagent 数 C，并保存简短来源与口径；未知时先取得明确值。下面的 `<C>` 与来源替换为采集结果，不能猜默认数。每个新项目执行一次；本页后续命令沿用同一 PowerShell 中的 `bp` 函数：

```powershell
$OutputEncoding = [Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = $OutputEncoding
function bp {
    & $python -X utf8 -m basepack @args
    if ($LASTEXITCODE -ne 0) { throw "basepack failed ($LASTEXITCODE)" }
}
bp init --project-root $project --machine-config $machineConfig --max-concurrent-subagents <C> --concurrency-source '<有效宿主配置位置与计数口径>'
$config = Join-Path $project '.basepack/config.toml'
bp --config $config config show
bp --config $config doctor
```

成功时生成 `.basepack/config.toml` 和 `.basepack/instructions.md`，根 AGENTS 加入入口指针，`.basepack/` 加入 Git 忽略。`config show` 应显示选定的 Python、机器文件、项目根及并发快照/来源，doctor 返回 core 检查；独立技能还需按下节安装并核宿主发现。文件已存在时 init 报错：继续使用已有入口，或为新项目选择正确目录；保留原配置与业务指令。

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
| basepack-setup | `experiments/20261106-basepack/skills/basepack-setup/` | 安装或升级所选 basePack 能力 |

这些独立技能不在 wheel 内；仅安装 wheel 的使用者可另取对应版本源码中的所选目录，无需重装客户端。记忆 skill 与协调者/reader 的英文维护提示词随 wheel 安装，通过 `memory guide`、`memory prompt` 与生成的 instructions 使用。

1. **选择安装位置。** 新项目优先把所选完整目录复制到 `<project>/.agents/skills/<name>/`。已有 `<project>/skills/<name>/` 维护原件时，保留该维护源，在 `.agents/skills/<name>` 建立指向它的目录联接。其它宿主按其技能安装规则选择发现位置。
2. **核对已有入口。** 修改前检查同名路径；正确的完整目录或指向预期原件的联接直接复用。同名用户技能、非预期目录或指向其它目标的联接保留原状，报告路径与目标冲突后再决定处理。重复执行时先做此核对，跳过已正确安装项。
3. **复制或联接。** 下列命令只用于尚无同名入口的所选技能；正确入口已存在时直接复用并跳到第 4 步。在复制与联接中选一种，示例一次安装一个技能；尖括号替换为实际绝对路径。

新项目复制完整目录：

```powershell
$repo = '<absolute-matching-source-checkout>'
$project = '<absolute-target-project>'
$name = 'agent-team' # 替换为所选技能名称。
$source = Join-Path $repo "skills/$name" # resources 和 basepack-setup 改为 Join-Path $repo "experiments/20261106-basepack/skills/$name"。
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

项目配置 `[ai]` 维护日常与检索默认等级，以及各等级的 `model` 和 `reasoning_effort`。模型映射每次读取项目配置，不在安装时冻结；初始值见 [项目模板](../src/basepack/project/templates/project.toml)，按宿主实际可用模型调整：

```powershell
bp --config $config config ai
bp --config $config config ai --purpose retrieval
bp --config $config config ai --tier tier2
```

`config ai` 默认解析日常用途；`--purpose retrieval` 核检索映射。记忆维护使用 `maintain`/`prompt` 返回的派工元数据，检索使用 `memory retrieve --question '<业务问题>'`；宿主创建时原样传入脚本给定的 `task_name`、`model` 和 `reasoning_effort`，实际接收最终结果后确认交付。协调者/reader 默认 tier2/tier1，显式 `--tier <tier>` 可改档并保留角色。命令与提示词不能代替宿主派工，basePack 不自行调用理解模型。交接见 [维护](memory.md#自动维护与手动维护) 和 [检索](memory.md#启动与检索)。

`[ai].max_concurrent_subagents` 与 `concurrency_source` 是宿主容量快照。修改宿主上限、切 profile/宿主或升级接入时，重新采集并用 `config set-concurrency --max-concurrent-subagents <C> --concurrency-source '<来源与口径>'` 更新受影响项目，再核 `config show`；不重跑普通 init、不迁移数据库。其它配置变更的联动见 [配置维护要点](project-config-maintenance.md)。

## 启用记忆

在 `memory init` 前核项目配置的 `[memory]`，选定本项目独立的 `data_dir`、显式回环 IP 的 `endpoint`，保留 init 生成的 `project_id`。endpoint 仅支持 HTTP(S) 的 127/8 或 `::1`，不使用 localhost、域名、通配或远端地址。新项目默认 `search_mode = 'vector'`，也可选 `hybrid`；search 使用项目检索模式并需要共享编码服务，`search --mode` 只覆盖本次查询。brief 直接读取已发布 mandatory、已有文件／章节摘要和已知缺口，不做任务搜索或 embedding。

默认端口 18080 被占用时修改新项目 endpoint。两个项目可共用程序和共享模型服务，分别使用：

| 项目 | memory.data_dir 的实际位置 | memory.endpoint | memory.project_id |
| --- | --- | --- | --- |
| A | `<project-A>/.basepack/memory` | `http://127.0.0.1:18080` | A 的 init 生成的 UUID |
| B | `<project-B>/.basepack/memory` | `http://127.0.0.1:18081` | B 的 init 生成的另一 UUID |

按 [项目 SurrealDB](administrator.md#项目-surrealdb) 为全新库准备一次随机密码文件，创建认证、仅回环监听的 launcher 与日志。已有库沿用原用户名和密码文件。启动后在下一次独立调用检查 `/ready`，客户端自动读取凭据，再执行：

```powershell
bp --config $config memory init
bp memory guide
bp --config $config memory brief --task '当前任务'
```

成功时 init 安装 schema、绑定数据库身份，并共用项目 init 的刷新入口更新 instructions 与 AGENTS 托管块；块外原字节保持，重复刷新幂等，损坏标记明确报错。普通 init 生成未启用记忆的指令，不要求连接数据库。guide 返回已安装流程的位置，空库 brief 返回空结果。误连另一 UUID 时修正 endpoint 和目录，保留原 UUID。按 [最小闭环](memory.md#最小闭环示例) 完成一次开发试用，核写入、检索及依据。

brief、search、read 只读上次已发布知识及其依据快照。主任务开始取得一次 brief；同任务接续沿用。直觉预计不超过十分钟时跳过整个自动 maintain；更长任务在宿主生命周期支持下异步运行 `memory maintain --mode automatic`，范围明显扩大时重估，子任务不递归开维护。显式维护使用 `--mode manual`，不受时长门槛限制。维护默认发现整个项目，不用当前业务文件缩小范围；来源、固定布局和派工详情见 [记忆使用](memory.md#自动维护与手动维护)。

## Codex 项目聊天接入

Codex 宿主按项目归属默认接入可取得的聊天，不要求逐 thread 配置。宿主从当前聊天与完整项目清单取得项目 ID、其它已注册项目根，在 `init` 时自动传 `--codex-project-id`、可重复的 `--codex-other-project-root` 和 `--codex-registry-complete`；已有项目由宿主更新配置的 `[memory.codex]`。这是宿主元数据接法，Codex 项目 ID 与 basePack 的 `memory.project_id` UUID 各自保留。

首次启用或旧项目升级时，instructions 指引 Codex 宿主补齐绑定；每次维护预检刷新完整注册根。`memory maintain --holder <本thread身份> --control <全新稳定路径> --codex-registry <UTF-8-JSON>` 可传本轮 `{project_id, other_project_roots, registry_complete:true}`，覆盖本轮采集绑定。注册清单工作文件放根 tmp，采集原件与定位回执保留在实际 memory 目录。非 Codex 宿主或绑定不可取时继续文件记忆，明确聊天覆盖缺口。

维护入口通过受支持的 App Server 列出 active 与 archived 聊天并分页读取正文。明确的项目 ID 优先；线程未带项目 ID 时，用项目根、Git worktree/common-dir 与宿主其它注册项目根排除冲突。不能确认的条目留在 unresolved/gaps；标题与关键词不判定归属。受管 UTF-8 导出保存在项目 `memory.data_dir/codex/`，由同一维护入口加入发现范围；无需把每个 thread 填入 `source_scope`，也不递归扫描数据库、控制文件和维护回执。

采集回执的 discovered、unresolved、gaps 和路径描述本轮原文发现与采集；`needs_semantic` 与语义回执描述仍需阅读的范围。brief 的 `codex_collection.status` 为 `unavailable`、`registry_incomplete` 或 `not_checked`，只表示绑定能力或查询未检查采集，不能证明全部聊天已入库。可取得的受支持 localImage 会作为独立原图来源保存到 codex-attachments；附件不可取得、缺少的 subagent 与归属不明范围保留缺口。当前实际验收边界见 [本轮进度](../../../devDoc/archive/20261110-onboarding-simplification/progress.md)；附件原件、完整分叉/继承身份和全部项目聊天覆盖仍需真实使用验证。

## 新 shell 接续

模板将 `[memory].username` 设为 root，已有库填写其实际用户名；可选 `password_file` 是相对项目根或绝对路径，省略时使用实际 `memory_dir/password.txt`。CLI 与 Python 在创建记忆客户端时自动读取同一个 UTF-8 密码文件，`config show` 只返回解析后的 `memory_password_file` 路径。

沿项目 `AGENTS.md → .basepack/instructions.md#startup` 执行本机入口；[生成模板](../src/basepack/project/templates/memory-enabled.md) 是 shell 初始化与任务启动步骤的维护源。新 PowerShell 进程只初始化本次所需 Python／配置参数与 UTF-8；主任务开始执行一次 brief，同任务继续读文件、写文档、反馈、stop/release 均沿用已获 brief。任务目标或上下文实质变化时才按需补取。stop/owner/release/recover-owner 只需配置，不依赖 brief、数据库或密码。

缺文件、权限错误和错误密码直接保留原始失败。恢复正确文件或修正配置后重试，不自动生成替代密码，也不回退免认证。连接失败时按生成入口检查本项目 `serve.ps1`、cwd 与日志，由项目维护者显式启动数据库。同项目多聊天共用数据库，聊天结束后保持运行。项目搬迁后核实际 Python/配置及包装/服务路径，再运行 `memory init` 刷新托管块；instructions 块外旧路径另行核对。

已知少量文件直接同批读取；需要发现资料时用 `memory retrieve --question '<业务问题>'`，不传 scope 为全项目，路径限制可用 `--scope 'devDoc/'`，中文及带空格前缀也可。宿主负责实际派工、接收最终结果与 delivery 回执，完整流程见 [检索](memory.md#启动与检索)。

## 版本升级

0.13.0.dev1统一使用程序分配的member UUID与冻结批次协议。**已有记忆库先停写并离线迁移，通过后同时切换库和客户端**；不要先覆盖现用环境再连接旧库，`memory init`也不自动迁移。先在隔离环境检查新wheel，保留原生export、旧wheel、配置/凭据、原文/图片和身份回执；用该版配套的离线恢复工具冻结一对一映射，转换成员引用、历史、图端点、交付/访问派生键并在独立物理副本完整比对。知识版本、原文与向量输入不变时保留，迁移不重新接受知识或计访问。工具与映射只作离线恢复材料，正常包无旧ID解析或双协议；尚未取得工具或迁移未通过时继续保留旧环境。具体交付和工具位置见[本次交付记录](../../../devDoc/tasks/20261114-delivery-closeout/result.md)。

切换前结清或明确作废持有旧ID的批次、维护回执和未确认交付；保留其恢复原件，后续重新prepare生成UUID引用。新建草稿省略永久ID，用局部数组位置引用，`memory freeze --drafts ... --output ...`分配并冻结UUID；更新复用prepare返回的UUID与expected，失败核实和重试沿用同一冻结文件。切换后执行`memory init`刷新生成入口，核旧知识/原证、历史与交付去重，并完成一次新建/更新流程。项目UUID、原凭据、配置schema 2和向量identity保留，外部项目各自安排迁移。

资源调用方同时更新worker所在的Python安装：jobs结果移除`cleanup_confirmed`，等待到期返回`observation_expired`且不取消作业，停止和限时由Condor原生策略负责。共享embedding的422及原请求索引诊断须服务端更新才生效，按[管理员流程](administrator.md#升级与回滚)处理；客户端安装不代表服务已更新。

0.11.0.dev1 增加短任务跳过整个自动维护、固定名称派工、脚本容量布局和独立检索派工。升级先按 [配置维护要点](project-config-maintenance.md) 重新取得宿主并发上限/来源，用 `config set-concurrency` 补齐或更新旧项目，再执行 `memory init` 刷新 AGENTS 与 instructions 托管块，保留原 UUID 和块外字节。已有维护须先 stop、取消自有后代、确认发布结束并 release，再更换客户端/入口；多项目共用解释器时逐项目安排升级，或先用独立环境。

自动维护显式使用 `--mode automatic`，手动维护使用 `--mode manual`（命令默认）；宿主按返回的名称、模型和推理强度派工。同项目仍由一个 owner 预检和发布。CLI 的 `apply` 须传 owner 的 control；Python 省略 control 时仅在空闲项目取得短期 owner，繁忙则明确失败。详见 [自动维护](memory.md#自动维护与手动维护)、[反馈与审计](memory.md#使用反馈与手动审计) 及随包 skill。

先按 [备份步骤](memory.md#备份与恢复) 保留知识、配置和原件恢复集合，再由客户端维护者安装新包。已有配置保持 schema 2、机器 schema 1 和原 UUID。

面向 0.9.0 的升级增加 `memory prompt` 和 `maintain` 派工元数据；默认全项目发现取代仅以 `source_scope` 发现。原有 `source_scope` 保留为 Git 项目的显式包含项与非 Git 项目的声明范围，不必将 Git 内新增源码逐个登记。已有来源和历史待维护范围仍全局接续；根据 `discovery` 与回执检查实际覆盖，升级不会自动完成全部语义接受。刷新 instructions 后按 [自动维护](memory.md#自动维护与手动维护) 派工。

0.8.1 已收敛的调用合同继续保留，升级前核对自己的 Python 脚本与配置：

- CLI 检索与 Python `Memory.vector_search`、`Memory.hybrid_search` 统一返回 `{matches, vector_coverage}`，从 `matches` 取候选；删除这些接口的 `include_coverage` 参数及裸列表返回格式。
- brief 删除恒空 `changes/change_count` 与重复 `vector_pending/vector_pending_count`，保留 `vector_coverage`、知识 pending、`coverage_gaps` 和 `change_check`；来源发现、原文采集与语义接受分别核对。
- 删除 `MachineConfig.state_dir`、机器模板 `[shared].state_dir` 及其回显。embedding 日志仍由 SCM/Shawl 服务定义指定，jobs 仍使用项目 `jobs_dir`，不用搬迁日志。
- 删除内部 `MemberContent/read_member` 当前原件读取接口；已发布原文通过 `memory read` 或 Python `Memory.read` 读取对应快照及显式 `source_version`。

`memory guide/rank` 无需 `--config`；owner/stop/release/recover-owner 需要本项目配置定位状态，但不读取数据库凭据。`memory prompt` 只读配置、模板与回执，不要求数据库、密码或模型。独立 skills 的安装合同不变，升级客户端不会替项目安装它们。

升级到 0.7.1 前先确认共享模型服务可用。旧 text 项目用显式 vector 查询核已发布活跃范围的向量覆盖：

```powershell
bp --config $config memory search --mode vector --text '<代表性主题>'
```

`vector_coverage` 的 total 与 compatible 相等且 pending 为 0 时，直接复用索引，将配置 `search_mode` 改为 `vector` 或 `hybrid`。有缺口或没有兼容向量时先运行 `memory embed` 补建，再查询确认覆盖；其 pending 还可能包含待语义维护的旧 stale 项，以查询返回的已发布活跃范围为切换条件。模型身份变化也按此补建，不回退到纯文字模式。

客户端升级后，按下面步骤保留已有认证与数据库，刷新入口；新 shell 无需手工加载凭据。执行 `memory init` 核 schema/UUID，再运行代表性 brief、search、read 和 neighbors。

旧配置缺少 `search_mode` 时明确补入所选模式；缺少 `[ai]` 时从 [项目模板](../src/basepack/project/templates/project.toml) 补入等级。0.8.1 保留 username/password_file，移除 password_env 与生成入口中的手工变量桥接。资源服务升级与回滚见 [管理员说明](administrator.md#升级与回滚)。

### 从既有认证客户端升级

1. 保留旧 wheel、项目配置、原密码文件和 [完整恢复集合](memory.md#备份与恢复)。核 `username` 与 `password_file` 指向当前服务使用的同一凭据；默认位置不变时可省略 password_file，删除 password_env。
2. 等正在调用的客户端完成后普通安装目标版本，更新配置中的 Python 路径（若解释器改变）。数据库、原密码、物理目录、端口与 UUID 保持；已有认证服务通常无需重启或迁库。
3. 重新采集宿主并发上限/来源，用 `config set-concurrency` 更新旧项目；执行 `memory init` 刷新 instructions 与 AGENTS 托管块。核 instructions 块外首段和包装脚本的实际路径，移除旧环境变量加载。新 shell 按入口初始化参数，再以代表性 brief/search/read/neighbors 核原知识及依据；已有兼容向量无需重新编码。这是升级验证，日常知识批次按作者生成和程序提交完成。

密码文件缺失时恢复原凭据，不为已有库生成新密码。改写文件不等于轮换数据库中保存的账户密码；确需轮换时先由数据库管理员更新账户，再同步唯一凭据文件和 launcher。失败保留原错，按保留的 wheel 与配置回退；不清库或重新总结。

正式项目升级结果见 [本轮进度](../../../devDoc/archive/20261110-onboarding-simplification/progress.md)。

## 移动与重新检出

移动启用记忆的项目时，先收尾维护和未明发布，再停止该项目数据库并确认进程退出，保留配置、业务原件和完整记忆数据；按新目录调整服务 cwd、日志与 endpoint，保留 project_id 后再启动并核 read/search。也可按 [原生备份恢复](memory.md#备份与恢复) 搬迁。Python 和机器配置绑定仍须有效；已保存作业材料中的绝对路径需按新位置修复，Condor 历史不会随目录移动。按 [配置维护要点](project-config-maintenance.md) 核入口块外路径、宿主容量及受影响设施。新检出通过 init 重建被忽略的配置和 instructions，AGENTS 与业务源码可正常提交；知识通过对应项目备份恢复。

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
