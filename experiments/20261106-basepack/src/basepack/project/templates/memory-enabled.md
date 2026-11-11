<!-- basepack-memory:start -->
<a id="startup"></a>
## 任务启动

记忆已在本项目启用。每个新的 PowerShell 进程执行整段；客户端读取配置指定的原密码文件：

```powershell
$$ErrorActionPreference = 'Stop'
$$OutputEncoding = [Text.UTF8Encoding]::new($$false)
[Console]::OutputEncoding = $$OutputEncoding
$$basepackPython = '$python'
$$basepackConfig = '$config'
& $$basepackPython -X utf8 -m basepack --config $$basepackConfig memory brief --task '<当前任务>'
if ($$LASTEXITCODE -ne 0) { throw "memory brief failed ($$LASTEXITCODE)" }
```

后续命令复用本进程的 `$$basepackPython` 和 `$$basepackConfig`；新进程重新执行整段。搬迁后以新配置重新运行 `memory init` 刷新本段及 AGENTS。直接保留 mandatory；stale=true 按业务需要回源确认。brief/search/read 查询已发布知识及其依据快照。[启动详情](<$skill#start-and-stop>)。

本项目数据库的 launcher 为 `$memory_dir/serve.ps1`，cwd 为 `$memory_dir`，日志为其中 `logs/surreal.stdout.log` 与 `logs/surreal.stderr.log`。先检查 endpoint 的 `/ready`；不可用时查日志，由维护者显式启动 launcher。多聊天共用该进程，业务结束保持数据库运行。[首次部署](https://github.com/YS-Pan/basePack/blob/main/experiments/20261106-basepack/docs/administrator.md#项目-surrealdb)、[恢复集合](https://github.com/YS-Pan/basePack/blob/main/experiments/20261106-basepack/docs/memory.md#备份与恢复)；新增状态按本机 skill 的恢复说明保留。

<a id="maintenance"></a>
## 自动维护

宿主支持任务开始/完成事件与可取消子任务时，分配全新且稳定的 control（本项目 `$memory_dir/maintenance/` 内），以本 thread 身份运行 `memory maintain --holder <thread> --control <control>`，和业务并行。程序在预检前原子取得项目所有权；`acquired=false` 时报告已有 owner 并继续业务。默认全项目发现，不用当前业务文件缩小范围。缺少生命周期能力时说明自动维护不可用，使用显式维护任务。Codex 宿主每次先刷新项目注册清单，保留采集缺口。[所有权、来源与采集详情](<$skill#maintain-sources>)。

<a id="dispatch"></a>
## 维护派工

仅 `acquired=true` 且 `needs_semantic=true` 时，以 `worker.model`/`worker.reasoning_effort` 实际派协调者；只给英文启动句和 `worker.render_command`，由其运行并遵循 JSON `prompt`。协调者持续接续固定回执内的批次，作者完成必要原文理解后交程序发布；已阅处置、粗层表示及待细化按同一合同计入进度。[派工与批次详情](<$skill#maintain-sources>)。

<a id="stop"></a>
## 维护收尾

持有者在业务结束时运行 `memory stop --control <自有control>`，取消自有协调者及后代，再以 `memory owner` 核执行状态并 `memory release --control <同一control>`。stop 不撤销已获准发布；确认发布阶段结束后才释放，失败或结果未明保留 owner 与原错，业务答复说明余项。异常恢复先独立核旧持有者已结束及发布已解决；他人不能解锁或按文件年龄抢占。[停止与恢复详情](<$skill#start-and-stop>)。

<a id="explicit-maintenance"></a>
## 显式维护

用户明确要求维护时，维护本身属于交付：按授权范围报告实际处置、阻塞和余项。已有 owner 时报告持有者，不能将跳过或少量优先批次当作完成。采用固定候选/聊天截点，每批 prepare 当前版本；回执外新增材料留后续。[完成口径](<$skill#maintain-sources>)。

<a id="feedback"></a>
## 使用反馈

检索 worker 和调用 agent 均可运行 `memory feedback-report`，提供疑点、观察版本及可用来源；无 ID 漏检提供查询或来源线索。报告不取得维护 owner，业务继续；未决报告随下次维护交单一 owner 判断修复，处理结果保存在项目数据库并随导出恢复。[反馈命令与版本合同](<$skill#use-feedback>)。

<a id="audit"></a>
## 手动审计

建立、普通维护及修复在作者生成和程序成功提交后结束，默认无额外语义审计、例行回读/检索抽查。仅用户明确表达记忆系统审计意图时，按该次范围启动手动审计；讨论该词、普通维护或报告问题均不触发。审计写入修复仍取得维护 owner。[手动审计详情](<$skill#manual-audit>)。

检索按配置 `memory.search_mode` 使用 `vector` 或 `hybrid`；`hybrid --literal` 优先精确子串并以 `lexical_rank` 标识，`vector --literal` 明确拒绝。业务需要的检索、筛选、评分和原文阅读见 [检索流程](<$skill#retrieve-in-one-delegation>)。
<!-- basepack-memory:end -->
