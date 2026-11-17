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

主任务直觉预计不超过十分钟时，仅保留 brief，跳过整个自动 maintain；明显更长时，在宿主支持开始/完成事件与可取消子任务的条件下并行业务维护。范围明显扩大时重新判断，可首次启动；子任务遵循委托，不递归开维护。用户明确要求维护时直接按显式维护执行，不受时长门槛限制。

Codex 原件先独立运行 `memory collect --output <采集回执.json>`，请求采集时刷新完整项目注册清单；采集无维护 owner，失败保留原错与回执。绑定 Codex 的项目随后明确用 `--collection <采集回执.json>` 或 `--retained` 维护已有原件；retained 不证明当前聊天 freshness。未绑定的纯文件项目无需该选择。采集回执是逐聊天观察，加载时核原件 hash；prepare 再固定实际版本。[来源选择](<$skill#maintain-sources>)。

启动时分配全新且稳定的 control（本项目 `$memory_dir/maintenance/` 内），以本 thread 身份运行 `memory maintain --mode automatic --holder <thread> --control <control>` 并附上述来源选择；宿主已有本轮可用 subagent 额度时传 `--available-subagents <A>`，包含检索等占用后的额度，不提前扣脚本预留。程序在预检前原子取得项目所有权；`acquired=false` 时报告已有 owner 并继续业务。默认全项目工作集；显式 `--scope` 实际限制新增、已登记、缺失及待处理来源，范围外余项保留。缺少生命周期能力时说明自动维护不可用，使用显式维护任务。[所有权与失败收尾](<$skill#maintain-sources>)。

<a id="dispatch"></a>
## 维护派工

仅 `acquired=true` 且 `needs_semantic=true` 并返回 worker 时，按 `worker.spawn_arguments` 实际派唯一协调者；保留原父 stop、全部宿主句柄及一个协调者恢复名额。协调者规划有限独立任务并启动固定 reader 池，固定初始化回执后结束第一 turn。原父确认该 turn 实际结束、协调者 idle 后封口，向已启动 reader 逐一发送明确 go；reader 在首 turn 用宿主事件等待，不提前领取。容量不足保持待处理，不启动无 reader 协调者。[派工与固定波次](<$skill#maintain-sources>)。

reader 自主领取、阅读、写稿、提交并再领取；普通退出不唤醒协调者。最后正常退出者固定回执，先登记通知意图，再实际 followup 同一非根协调者并记录宿主受理结果。协调者第二 turn 核 owner/stop，按固定稿和唯一 publisher 合同发布后即结束，不等待通知确认；原父观察其 FINAL 与最后 reader 的通知结果/宿主终态后关闭波次。pending/未明通知、claimed 失败、在途发布由原父按实际宿主证据恢复，不盲重发或超时抢占。[波次、恢复与阶段边界](<$skill#maintain-sources>)。

<a id="stop"></a>
## 维护收尾

持有者在业务结束时运行 `memory stop --control <自有control>`，取消自有协调者及后代，再以 `memory owner` 核执行状态并 `memory release --control <同一control>`。这些命令只需本项目配置，不依赖数据库、密码或重新 brief。stop 不撤销已获准发布；确认发布阶段结束后才释放，失败或结果未明保留 owner 与原错，业务答复说明余项。异常恢复先独立核旧持有者已结束及发布已解决；他人不能解锁或按文件年龄抢占。[停止与恢复详情](<$skill#start-and-stop>)。

<a id="explicit-maintenance"></a>
## 显式维护

用户明确要求维护时，使用 `memory maintain --mode manual` 并附来源选择，维护本身属于交付：按授权范围报告实际处置、阻塞和余项。已有 owner 时报告持有者，不能将跳过或少量优先批次当作完成。按工作量和容量启用固定 reader 池，并为协调者恢复保留席位；没有 reader 容量时保留余项。固定候选内先处理用户约定、当前阶段及稳定成果入口，再补历史；披露实际接受版本、后续未接受成果的原件入口与有限后续范围。业务收尾按父任务停止边界执行。[完成口径](<$skill#maintain-sources>)。

<a id="feedback"></a>
## 使用反馈

检索 worker 和调用 agent 均可运行 `memory feedback-report`，提供疑点、观察版本及可用来源；无 ID 漏检提供查询或来源线索。报告不取得维护 owner，业务继续；未决报告随下次维护交单一 owner 判断修复，处理结果保存在项目数据库并随导出恢复。[反馈命令与版本合同](<$skill#use-feedback>)。

<a id="audit"></a>
## 手动审计

建立、普通维护及修复在作者生成和程序成功提交后结束，默认无额外语义审计、例行回读/检索抽查。仅用户明确表达记忆系统审计意图时，按该次范围启动手动审计；讨论该词、普通维护或报告问题均不触发。审计写入修复仍取得维护 owner。[手动审计详情](<$skill#manual-audit>)。

检索按配置 `memory.search_mode` 使用 `vector` 或 `hybrid`；`hybrid --literal` 优先精确子串并以 `lexical_rank` 标识，`vector --literal` 明确拒绝。业务需要的检索、筛选、评分和原文阅读见 [检索流程](<$skill#retrieve-in-one-delegation>)。
<!-- basepack-memory:end -->
