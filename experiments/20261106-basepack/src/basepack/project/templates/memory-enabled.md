<!-- basepack-memory:start -->
<a id="startup"></a>
## 任务启动

记忆已在本项目启用。本节是任务启动与 shell 接续的维护源；其它说明按此入口执行。每个新的 PowerShell 进程只初始化该次命令所需参数与 UTF-8；客户端读取配置指定的原密码文件：

```powershell
$$ErrorActionPreference = 'Stop'
$$OutputEncoding = [Text.UTF8Encoding]::new($$false)
[Console]::OutputEncoding = $$OutputEncoding
$$basepackPython = '$python'
$$basepackConfig = '$config'
```

主任务开始时先直觉粗判业务时长，再执行一次 brief；与应启动的长任务维护各自报告失败：

```powershell
& $$basepackPython -X utf8 -m basepack --config $$basepackConfig memory brief --task '<当前任务>'
if ($$LASTEXITCODE -ne 0) { throw "memory brief failed ($$LASTEXITCODE)" }
```

同一任务后续读写文件、反馈、stop/release 沿用已获 brief；任务目标或上下文实质变化时按需补取。后续命令复用本进程的参数，新进程只重新初始化。搬迁后核实际路径，再以新配置运行 `memory init` 刷新托管块；块外旧路径另核。

brief 只读已发布 mandatory、概况入口和已知缺口，不做 embedding、任务搜索或原件扫描。直接保留 mandatory；stale=true 按业务需要回源确认。已知少量文件直接同批阅读；判断项目现状、剩余工作、待决策或历史要求时，先用一次完整检索核既有决定，再形成选项；已点名聊天直接读并沿引用核后续发布。此类跨历史依据统一交 [检索 worker](<$skill#retrieve-in-one-delegation>)，先固定基础锚点，再完成多轮搜索、回源、一次综合评分与 rank；主任务实收后确认交付。[客户端与凭据](<$skill#start-and-stop>)。

brief、检索和回读返回 `private=true` 的内容按项目限制分发约定处理，涵盖隐私、机密及版权/许可边界；公开写入仅提炼本项目允许公开的内容与结论。交接保留所见标记，旧记录缺标不代表已核公开。[私有来源与公开边界](<$skill#private-sources-and-publication>)。

本项目数据库的 launcher 为 `$memory_dir/serve.ps1`，cwd 为 `$memory_dir`，日志为其中 `logs/surreal.stdout.log` 与 `logs/surreal.stderr.log`。先检查 endpoint 的 `/ready`；不可用时查日志，由维护者显式启动 launcher。多聊天共用该进程，业务结束保持数据库运行。[首次部署](https://github.com/YS-Pan/basePack/blob/main/experiments/20261106-basepack/docs/administrator.md#项目-surrealdb)、[恢复集合](https://github.com/YS-Pan/basePack/blob/main/experiments/20261106-basepack/docs/memory.md#备份与恢复)；新增状态按本机 skill 的恢复说明保留。

<a id="maintenance"></a>
## 自动维护

主任务直觉预计不超过十分钟时，仅保留 brief，跳过整个自动维护。明显更长且宿主支持开始/完成事件与可取消子任务时，按下节以 `--mode automatic` 并行业务启动。范围明显扩大时重新判断。子任务按委托执行，显式维护不受时长门槛限制。缺少宿主生命周期能力时说明自动维护不可用，使用显式维护任务。

<a id="dispatch"></a>
## 维护启动与派工

原父用本 thread 身份运行 `memory maintain-start --holder <thread> --mode automatic|manual`。默认全项目，按授权加 `--scope <项目相对路径...>`。宿主已知本轮可用容量时加 `--available-subagents <A>`，计入检索等占用但由程序扣除恢复预留。已有成功采集回执可用 `--collection <回执>`，明确使用已保留原件可加 `--retained`。绑定 Codex 且无来源选择时交协调者采集新原件。本轮授权允许采集失败后使用已保留原件时，加 `--allow-retained` 将该选择传给干净上下文的协调者。

遇 `busy` 报告已有 owner。遇 `capacity_unavailable` 保留语义余项，可在授权范围内用普通 `memory maintain --available-subagents 0` 维护项目文件或已保留原件，使用新 control 与相应来源选择，跳过自动采集审批。[来源选择与容量不足](<$skill#maintain-sources>)。

返回 `prepared` 时保留 `attempt_id` 和 control，按原样用 `spawn_arguments` 实际派一次协调者，保留句柄和恢复名额。协调者按生成的提示执行。需采集时读取 `memory collect-prompt --attempt <id>`，在受影响的 Windows Codex 且可用 Auto-review 时仅为采集请求一次审批，等待期间不持有 owner。权限路径受阻时报告采集缺口，按授权选择来源。预检在普通沙箱使用原父 holder/control。协调者如需语义维护则启动有限 reader 池，交固定初始化回执后结束第一 turn。原父确认该 turn 实际结束、协调者 idle 后封口，向实际已启动的 reader 各发一次 go。Reader 在首 turn 通过宿主事件等待。[固定波次与采集回执](<$skill#maintain-sources>)。

reader 自主领取、阅读、写稿、提交并再领取；普通退出不唤醒协调者。最后正常退出者固定回执，先登记通知意图，再实际 followup 同一非根协调者并记录宿主受理结果。协调者第二 turn 核 owner/stop，按固定稿和唯一 publisher 合同发布后即结束，不等待通知确认；原父观察其 FINAL 与最后 reader 的通知结果/宿主终态后关闭波次。pending/未明通知、claimed 失败、在途发布由原父按实际宿主证据恢复，不盲重发或超时抢占。[波次、恢复与阶段边界](<$skill#maintain-sources>)。

<a id="stop"></a>
## 维护收尾

原父在业务结束时先运行 `memory stop --attempt <自有attempt_id>`，再取消自有协调者及实际后代。初始化回执不全时通过宿主核对实际后代。核实宿主调用与发布终态，并用 `memory owner` 确认本次取得所有权后，才执行 `memory release --control <同一control>`。普通 `maintain` 轮次用 `memory stop --control <自有control>`。这些命令只需项目配置，沿用已获 brief。失败或发布未明时保留 owner 和原错，报告余项。[停止与恢复详情](<$skill#start-and-stop>)。

<a id="explicit-maintenance"></a>
## 显式维护

用户明确要求维护时，按 [维护启动与派工](#dispatch) 使用 `--mode manual`，传用户授权的范围和来源选择。已有 owner 时报告持有者；采集受阻时仅在授权范围内选用保留原件。固定候选内先处理用户约定、当前阶段及稳定成果入口，再补历史。交付实际接受版本、阻塞、未接受成果的原件入口和剩余范围；按原父任务停止边界收尾。[完成口径](<$skill#maintain-sources>)。

<a id="feedback"></a>
## 使用反馈

检索 worker 和调用 agent 均可运行 `memory feedback-report`，提供疑点、观察版本及可用来源；无 ID 漏检提供查询或来源线索。报告不取得维护 owner，业务继续；未决报告随下次维护交单一 owner 判断修复，处理结果保存在项目数据库并随导出恢复。[反馈命令与版本合同](<$skill#use-feedback>)。

<a id="audit"></a>
## 手动审计

建立、普通维护及修复在作者生成和程序成功提交后结束，默认无额外语义审计、例行回读/检索抽查。仅用户明确表达记忆系统审计意图时，按该次范围启动手动审计；讨论该词、普通维护或报告问题均不触发。审计写入修复仍取得维护 owner。[手动审计详情](<$skill#manual-audit>)。

检索按配置 `memory.search_mode` 使用 `vector` 或 `hybrid`；`hybrid --literal` 优先精确子串并以 `lexical_rank` 标识，`vector --literal` 明确拒绝。业务需要的检索、筛选、评分和原文阅读见 [检索流程](<$skill#retrieve-in-one-delegation>)。
<!-- basepack-memory:end -->
