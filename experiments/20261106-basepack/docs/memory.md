# 项目记忆

记忆在本项目的 SurrealDB 中保存文件摘要、章节摘要、原文块、图片描述与定位，并保留知识版本、层级、原文范围、语义演变关系和修改依据；图片原字节快照保存在项目记忆目录的 assets 中。宿主订阅 agent 负责智能分块、摘要、识图、建图和评分，数据库执行存储、事务与查询。搜索使用共享模型服务，支持 `vector` 与 `hybrid`，新项目默认 `vector`。小文件不必虚造章节。

## 启用

按 [项目接入](setup-project.md#启用记忆) 选独立目录、回环 endpoint 和 UUID，再按 [项目 SurrealDB](administrator.md#项目-surrealdb) 准备认证服务与唯一密码文件，在独立调用核 ready/init/brief。同项目多聊天复用服务，另一个项目使用自己的物理目录、端口及 UUID；通用 exe 和模型可共用。服务在查询期间保持运行。前台排错可在普通用户终端直接执行同一个 serve.ps1，其 cwd 与 endpoint 仍来自目标配置。

普通 init 只生成配置和未启用记忆的入口；memory init 才安装 schema 并绑定 UUID、刷新 instructions 与 AGENTS 的记忆指令块。共用托管块更新保留块外原字节；重复刷新幂等，损坏标记明确报错。误连其它 UUID 的库会失败。任务启动与 [新 shell 接续](setup-project.md#新-shell-接续) 以生成的 `.basepack/instructions.md#startup` 为准；客户端自动读 password_file（默认 memory_dir/password.txt）。升级或搬迁时先按 [配置维护要点](project-config-maintenance.md) 核实际路径，再运行 memory init 刷新托管块；instructions 块外旧路径另核。只用资源工具无需记忆数据库。

## 首建与维护

可重建的 reading、batch、排名和一次性验证放项目根 `tmp/<任务或运行标识>/`；选留原证放根 `artifacts/runs/<运行标识>/`。数据库、凭据、原件/assets、control、仍在使用或恢复必要的回执保持配置指定的稳定位置；反馈在数据库内持久保存。控制文件可能早于回执创建，发布未明时不能清除。以下函数使依赖命令非零即停止；JSON 使用 UTF-8，保存成 `.ps1` 时为 Windows PowerShell 5.1 使用 UTF-8 BOM：

```powershell
$python = '<instructions 中的 absolute-python.exe>'
$config = '<absolute-project-config>'
$OutputEncoding = [Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = $OutputEncoding
function memory {
    & $python -X utf8 -m basepack --config $config memory @args
    if ($LASTEXITCODE -ne 0) { throw "memory command failed ($LASTEXITCODE)" }
}
memory maintain --mode manual --holder '<本thread身份>' --control '<memory.data_dir>/maintenance/<全新标识>.control'
# 仅 acquired=true 时继续；已有 owner 时报告持有者。
memory prepare --paths '说明.md' '决定.md' --output '<project-root>/tmp/<run>/reading.json'
# 阅读 prepare 输出，写出 agent-batch.json 后继续。
memory apply --batch '<agent-batch.json>' --control '<同一control>'
memory stop --control '<同一control>'
memory release --control '<同一control>'
memory changes --scope '资料目录'
```

`prepare --paths` 接受文件而非目录。需要处理目录时先枚举文件，再传项目相对路径，例如：`Get-ChildItem -File 资料目录 | ForEach-Object { Resolve-Path -Relative $_.FullName }`。SQL 事务与自动分包使用当前安装的程序/部署合同，真实失败保留原错；调用 agent 不承担例行 SQL 大小审核或拆包。

prepare 时包括本批所用依据与关系两端的材料；它提供新旧编号原文、已有与关联成员、节点、关系及 expected 知识版本，图片返回可打开的原图路径。关联记录的来源原文仍需 read 或扩充 prepare 范围核实。将材料交给订阅 agent，在同次阅读中选择最终块边界并生成摘要、节点和图边；结构备读单元只用于定位。批次 JSON 合同与操作流程在 `memory guide` 返回的已安装 skill 中，源码维护源为 [SKILL.md](../src/basepack/memory/SKILL.md)。

apply 核对来源版本，以及本批改写、退役、更正目标、实际依据、父引用和关系端点的 expected 版本，再原子写入；无关 expected 不阻塞，缺 expected 仅允许本批新建记录。chunk 按范围取原词；摘要、依据、更正和旧快照持久保存。旧草稿冲突重新 prepare、阅读后提交。作者完成必要理解、生成批次并由程序成功发布即完成普通批次，不追加独立语义复核、例行回读/检索抽查。失败或结果未明保持未决。

粗层摘要使用实际已读的精选 chunks 支持，保留独有事实及已有 mandatory。已阅但无新增知识/重复可登记 `sources[].dispositions`；已读而暂不细化可登记 `deferred_refinement`，不冒充未读缺口已完成。有效同版处置避免每次重复首建，来源或必要依赖变化重新处理。字段、范围与失效规则见 [批次合同](../src/basepack/memory/SKILL.md#direct-batch-interface)。

新内容由 apply 使用 [共享 embedding](resources.md) 编码；已有内容补建或重建索引时运行 `memory embed`，不另外加载模型。文件/章节使用已接受摘要，块使用原文，图片使用原始图片；兼容且输入未变的向量复用。超限保留原错误，交回原阅读 agent 调整分块或摘要，不能静默截断。模型不可用时停止本批发布或查询，并保留原错误。

图片先由视觉 agent 实际打开，描述与 OCR 单独标明，程序按 hash 保留必要原字节快照。必要 PDF 页可由宿主读取/渲染为项目内图片，locator 记录原文件、版本、页与区域；原 PDF 变化时重新核相关页面，不声称自动解析所有 PDF。

## 自动维护与手动维护

任务开始按生成入口取得一次 brief，同任务接续沿用。直觉预计不超过十分钟时跳过整个自动 maintain，包括预检、采集和取得 owner；明显更长时，在宿主有可取消子任务句柄及开始/完成事件的条件下，与业务并行启动一次全项目维护。范围明显扩大时重新判断，必要时首次启动，不等待计时门槛。子任务遵循委托和渲染提示词，不递归开维护。用户明确要求维护时用 `--mode manual`，不受时长门槛限制；缺少宿主生命周期能力时说明自动维护不可用，采用显式维护任务。

启动时分配稳定且全新的 control。程序预检前原子取得项目所有权；每个 thread 仍可 brief、报告问题及正常业务：

```powershell
memory maintain --mode automatic --holder '<本thread身份>' --control '<memory.data_dir>/maintenance/<全新标识>.control' --output '<project-root>/tmp/<run>/summary.json'
```

默认面向整个项目的受管来源，不按当前业务任务的文件缩小维护范围。Git 项目枚举项目内已跟踪和未忽略的未跟踪文件，并加入 `memory.source_scope` 显式包含项，排除工具状态、环境与缓存；非 Git 项目使用声明的 `source_scope`。所有已登记来源、历史 pending/未接受范围和可归属 Codex 原件持续参与维护。`--scope <文件或目录> ...` 只覆盖本轮新文件发现，不把历史来源限制到该范围。无需为日常维护递归扫描 `.`；不支持的二进制材料留缺口，读取失败保留原错。

零行文字来源且没有活动知识时，只需登记来源，不创建无效行范围的 member。已有正文被清空时，仍须退役旧成员并处理依赖；完成后不反复派发该空来源，重新出现正文会继续发现。

预检先按 [Codex 绑定](setup-project.md#codex-项目聊天接入) 取得本次可读的持久化聊天截点，再比较来源及旧成员实际接受版本。Git 干净仍可能有尚未接受的原文。发现清单、聊天采集、语义接受和向量覆盖分别检查，不能据其中一项声称全部项目材料已接受。`changes` 提供显式变化查看，`maintain` 才负责机械更新与语义交接；查询不调用两者。

程序在依据闭合时处理原字节 hash 相同的元数据变化、完整正文仅 CRLF/LF 变化，以及有唯一定位且上下文可确认未变的原文块；相互依赖的机械候选共同发布，无法证明依赖仍有效的范围留给语义共读。完整回执保留机械批次、旧/新行映射、变化片段、受影响成员与关系；换行归一只用于比较，快照仍按真实原字节保存。编码输入及身份未变才复用向量；实际输入变化按现有 apply 合同编码。已有 stale、更正、退役或语义证据不足的范围保留待核，局部文字相同不表示父级摘要或关系均有效。

`acquired=false` 时返回已有 owner 的 holder/run_id/执行状态，跳过自身维护并继续业务；显式维护请求需报告该阻塞。`acquired=true` 时返回机械计数、`needs_semantic`、`receipt`、`control`、固定的 `layout`、来源/采集边界及容量允许时的 `worker`。未决反馈也触发语义维护，原件未变或 pending 为零并不关闭它。`needs_semantic=false` 时不创建语义 agent；为 true 且存在 worker 时，宿主实际设置 `worker.task_name`、`worker.model` 和 `worker.reasoning_effort`，干净历史派协调者，只传：

```text
Run the following command and follow the `prompt` field in its JSON output:
<worker.render_command>
```

子 agent 自己执行该命令并遵循返回的 `prompt`。`memory prompt --receipt <receipt> --control <control> --team 0` 渲染第 0 队协调者；reader 使用 `--team <t> --role reader --reader <r> --paths <项目文件...>`。其它队协调者也必须有有界 `--paths`，派前将返回命令中的来源占位符替换为实际分配文件。脚本统一给出名称、父子位置、模型、推理强度和发布权限；宿主原样设置，不临时设计人数或自由起名。角色与档位独立：协调者默认 tier2，reader 默认 tier1；显式 `--tier <tier>` 仍保留角色。渲染只读配置、模板与固定回执，不读密码、不连数据库或模型，也不改控制文件或状态；配置变化不重写已开始的一轮布局。

布局使用接入时保存的宿主上限 C（不含主 agent、含全部后代）。宿主已有实时可用额度 A 时传 `--available-subagents <A>`：A 已扣其它占用（含检索），尚未扣本轮业务预留；自动维护预留 1 席，手动维护预留 0 席。脚本计算 `M=max(0,min(C,A)-预留)`。无 A 时仅返回配置允许的组织上限，实时额度未核，实际创建仍受宿主准入约束；容量快照的刷新见 [配置维护要点](project-config-maintenance.md#修改并发上限或切换宿主profile)。

自动模式始终仅第 0 队：M 为 1–3 时单协调者，M≥4 时加至多 4 名 reader。手动模式 M 为 1–4 时单协调者；M≥5 时启用 `min(10,floor(M/5))` 个满队，每队 1 协调者和 4 reader，余量留空。M=0 不派 worker，未处理材料保持待办。材料不足时少启用整队；零 reader 的协调者亲自 prepare、读原文、分块、摘要、建图、处置与发布，不等待 reader。所有队共用一份 owner/control/receipt，第 0 队协调者是唯一 apply 发布者及反馈结案者；其它队在其子树内交稿，不独立开维护或发布。

批次接续使用已知自有句柄；下一轮仅在上一轮及发布已结束后复用合规句柄，并使用全新 control。名称本身不证明实例归属。容量准入失败时保留原错与未派项、停止新增派工；取得新额度后用 `memory pending-dispatch --receipt <receipt> --available-subagents <A> --started-task-names <已启动名称...>` 仅缩减未启动清单，保留已启动名称和权限。不开第二个 owner，不以未派工冒充完成。

协调者按来源分批，安排 reader，首次生成跨来源关系时共读两端并统一发布；持续接批直到业务停止、固定候选耗尽或实际阻碍。每批 prepare/expected/apply 发布，不追加日常发布后的审计。采用固定候选与聊天截点；prepare 读各批当时的原件，不声称任务开始时全项目原子冻结。回执外新增材料留后续；处置、粗层和待细化分别报告。

采集与发布沿用自有 control。业务完成时，以本项目配置 `memory stop --control <control>`，取消协调者及后代；通过 `memory owner` 核发布状态，再 `memory release --control <同一control>`。这些命令独立于 brief，不需要数据库或密码。stop 不撤销已获准提交，release 要求已停止且无未完成/未明发布。control 是协作授权凭证，只给持有者及其 worker，不能复用或按清理习惯删除。失败保留原错与 owner，业务答复报告余项。异常遗留先独立核旧持有者/后代已结束及事务结果已解决，再显式 `memory recover-owner --run-id <id> --owner-ended --publication-resolved`；不按文件年龄抢占。此机制用于协作互斥，不隔离有文件系统访问权的对手。

自动小批接续已有积压，任务相关性只影响优先级。显式维护按授权范围交付实际处置、阻塞和余项，不以剩余数量或优先小批自行结案。普通业务结束不承诺清空历史；连续短任务的积压留下一次长任务或显式维护。特殊任务可按授权调整范围，固定名称和本轮容量仍由脚本提供。

## 使用反馈与手动审计

检索 worker 与调用 agent 共用 `memory feedback-report --kind knowledge|retrieval --issue '<疑点>'`。有目标带 `--target <ID> --observed-revision <观察时knowledge_revision>`；search/brief 保留当时版本，不能事后 read 新版冒充。无 ID 漏检提供 `--query '<查询>'` 或 `--source '<预期来源/定位>'`；可加 `--reporter '<身份>'`。轻量记录即可，业务继续，无需另做审计或完整修复方案。

报告无需维护 owner；`memory feedback-list` 默认返回未决（`--all` 含结果）。单一 owner 按当前版本及原件处理，沿 apply/corrections 修复后运行 `feedback-resolve <id> --control <同一control> --outcome fixed|invalid|duplicate|obsolete --result '<说明>'`；有目标需 `--expected-revision <当前版本>`。旧报告冲突不能覆盖新版，失败/未决保持可见。反馈是数据库运行状态，纳入导出恢复，不自摄入为业务知识。

仅用户明确表达记忆系统审计意图时，按该次范围启动手动审计；讨论该词、普通维护、实际问题均不自动触发。只读审计/记录可与维护并行，写入修复仍取得项目 owner。普通建立及修复的完成口径保持作者生成和程序提交。

## 聊天来源与精确回读

Codex 维护采集真实用户消息与可取得的助手文字，保留 thread/turn/item/part 身份和角色；系统、AGENTS、hook 与工具元数据不冒充用户 prompt。同一线程分页内重复的 turn/item 按身份去重，内容冲突保留错误；人类有意重复发送仍是不同消息。跨线程不按文字去重，完整继承身份尚未证实。每次以已捕获的持久化消息截点分页，当前任务中新增长度下次接续。采集只更新受管原件，不表示已经阅读、总结或发布知识。

受管聊天原文保存在 `memory.data_dir/codex/<thread>.txt`，版本 hash 属于该导出的真实 UTF-8 字节。接受后沿现有 source_version 保存快照；`read` 的 `original.chat_locations` 从所选已核快照返回聊天链接、thread/turn/item/part、UTF-8 字节范围及本次读取的正文交集，生成头与分隔符不当作人类原文。旧已发布版本可在原聊天续写或修订后继续核实。

可读取且格式受支持的 `localImage` 按内容 hash 复制到 `memory.data_dir/codex-attachments/`，作为独立图片原件进入同一维护范围。语义回执的 `codex` 及 reader 提示提供项目 ID、本轮采集回执（如有）和保留聊天/附件目录；worker 按随包 skill 从采集记录或历史 framed 原件核对同项目及同附件的 chat part 身份，实际打开图片，再将原记录身份作为 locator 接受。附件缺失、身份不可核或格式不支持时留 gap；真实聊天附件仍未验，不能据模拟 PNG 回归宣称全部附件可用。

当前宿主列表中的部分项目/父子字段缺失时依项目根与 worktree 证据归属；显式 subagent 引用须以直接 thread/read 返回的父级身份核对且无项目冲突，才递归采集。无法确认的范围明确留 gap。附件不可取时、引用的 subagent 未能列出或读取时也保留缺口，不按不存在退役旧知识。完整分叉/继承身份、附件原件及全部聊天覆盖仍未完成真实验收；采集回执、语义待核与向量覆盖分别检查，`pending=0` 不等于全部聊天已接受。

## 最小闭环示例

在已完成 init/brief 且共享模型服务可用的干净试用项目执行 [memory_minimal.py](../examples/memory_minimal.py)。配置 `memory.search_mode` 为 `vector` 或 `hybrid`。它新建四行 UTF-8 的 `memory-example.md`，拒绝覆盖同名文件，并依次 prepare → 生成完整批次 → apply（含编码）→ 按编号和文件名查询 → read/neighbors；每个子命令使用 `subprocess.run(check=True)`，apply 失败后即停止。该脚本用于检查命令闭环，真实材料的理解与批次制作由宿主 agent 按 skill 完成。

```powershell
$python = '<instructions 中的 absolute-python.exe>'
$config = '<absolute-project-config>'
& $python -X utf8 '<basepack-repo>/experiments/20261106-basepack/examples/memory_minimal.py' --config $config
if ($LASTEXITCODE -ne 0) { throw "memory example failed ($LASTEXITCODE)" }
```

示例在项目根 `tmp/example-<UUID>/` 保存批次/编号原文；control 保留在实际 memory 目录的 maintenance 中，并显式取得、停止和释放 owner。`expected`、source path/revision 沿用 prepare。批次包含以下 parent/evidence，范围为 1-based 闭区间；chunk 不写 text，由程序取第 3–4 行原词：

| 成员 ID / kind | 行范围 | parent | evidence |
| --- | --- | --- | --- |
| `example-file` / file | 1–4 | 无 | ``member:`example-chunk` `` |
| `example-section` / section | 2–4 | ``member:`example-file` `` | ``member:`example-chunk` `` |
| `example-chunk` / chunk | 3–4 | ``member:`example-section` `` | 空 |

随包 [skill](../src/basepack/memory/SKILL.md#minimal-batch) 也保留不依赖仓库文件的完整批次例子。文字成员缺起止行字段会报告批次位置、成员 ID 与字段；不存在的 read 目标会明确报出 ID。修正输入后重新运行，失败批次没有部分写入；保留原错误，不继续下游命令。

`memory guide` 与 `memory rank --input <scored.json> --budget <字符数>` 无需项目配置。owner/stop/release/recover-owner 需显式配置定位本项目运行状态，但不需要数据库或密码；知识动作仍连接目标数据库。评分文件或控制文件错误保留原始信息。

## 启动与检索

任务开始执行一次 brief；同任务跨 shell 读写、反馈及维护收尾沿用已获内容，目标或上下文实质变化时按需补取。shell 初始化与任务启动的维护源是 [生成模板](../src/basepack/project/templates/memory-enabled.md)，实际 Python／配置见本项目 `.basepack/instructions.md#startup`。

brief 直接读取已发布 mandatory、已有文件／章节摘要与已知缺口，不做 embedding、任务搜索或原件扫描。mandatory 无条件保留；stale 条目保留为待核义务。已知少量文件直接同批阅读；需要发现项目概况、任务前提、过去要求或跨材料依据时，用统一入口：

```powershell
memory retrieve --question '历史要求如何演变？'
memory retrieve --question '文档中的现行约束是什么？' --scope 'devDoc/' --budget 6000
```

不传 `--scope` 时为 `''`，表示全项目；`scope` 严格表示项目相对路径前缀，支持中文与空格。业务范围写在 `question`。上例 `devDoc/` 是本仓库的实际前缀。默认预算为 6000 字符。入口创建 `tmp/basepack-retrieval/<uuid>/request.json`，返回稳定的 `delivery_id`、request/work/delivery_receipt 路径与派工元数据；同一次问题用 `memory retrieve --request <已返回request>` 接续，不再传 question。未给问题或 request 时只返回所需输入。

CLI 只准备派工。宿主实际按返回的 `task_name`、`model` 和 `reasoning_effort` 创建干净历史 worker，传英文启动句和 `render_command`，并接收其最终结果；`prepared`／`started=false` 不能称为已派工。默认 tier1，显式 `--tier` 可改档；共享可用额度已知时传 `--available-subagents <A>`。同一问题复用自有句柄完成多轮检索；独立并发问题用不同 `--slot`。零容量返回 `executor='main'`，或宿主无派工能力时，由主 agent 执行同一流程并如实说明执行者。检索与维护共享容量，但不取得维护 owner/control；短任务仍可检索。

一次实际委托由同一 worker 完成 search → 必要原文与图关系回读 → 0–100 综合评分 → UTF-8 `scored.json` 落盘 → rank → 可用内容与版本清单。`access_weight` 只是历史使用辅助线索，相关性、适用条件和证据价值为主；低权重关键材料仍可进入。rank 直接按综合分排序、去重与字符预算选择，不做第二次访问调权，也不记交付。worker 实际用宿主文件工具或本机 Python 保存评分文件；保存或 rank 失败时保留原错、已读证据和未完成阶段。

候选、read/knowledge、scored、rank 与最终清单一路保留实际观察的 `id`／`knowledge_revision`，原证的 `source_version`／`revision`、范围或图片 locator 另记。`record_type:'node'|'semantic'` 的独立知识节点／语义关系可无路径和行号，保留实际 basis、endpoint_versions；不能伪造来源来套成员格式。关系与条件用于判断本次适用性，区分用户要求、助手假设、代码事实和实验观察；旧要求热度不使其恢复现行身份，仍有效的旧实验可继续影响当前回答。完整评分形状与宿主步骤见 [随包 skill](../src/basepack/memory/SKILL.md#retrieve-in-one-delegation)。

宿主确认最终内容已经实际收到后，将最终实交付项写入返回的 delivery_receipt 路径，再执行：

```json
{"delivery_id":"<request中的稳定ID>","items":[{"id":"<实交付ID>","knowledge_revision":"<实见版本>"}]}
```

```powershell
memory delivery --input '<delivery_receipt路径>'
```

可选 `context` 为 JSON。程序原子记录最终交付，重试保留相同 delivery_id，空 items 不推进事件；search/read/rank、内部日志及错误均不算交付。只强化实见版本，不向父级、依据、邻居或新版传播；无交付事件时闲置不变。即使上游阶段失败，实际收到且可定位的最终部分材料仍可据实登记；未收到最终内容时不登记。程序不要求使用者逐条调权。

需要继续核实时使用以下接口；`--knowledge-revision` 省略时读当前知识，指定时读已保留版本，`history` 如实列可用历史。原证的版本与位置独立指定，图片实际打开 `original.image_path`；存量未保存的前像或来源定位保留缺口。

```powershell
memory knowledge '<id>' --knowledge-revision '<实见版本>'
memory history '<id>'
memory neighbors '<id>' --knowledge-revision '<实见版本>'
memory read '<basis.member>' --knowledge-revision '<该成员实见版本>' --source-version '<basis.source_version>' --start-line <basis.start_line> --end-line <basis.end_line>
memory access-hints --input '<items.json>'
```

neighbors 的 `unpinned_children`／`unpinned_edges` 是存量端点版本未知的线索，按 basis 回源核实并保留缺口，不能当作精确历史链接。access-hints 输入为 `[{"id":"<id>","knowledge_revision":"<实见版本>"}]`。Python 对应 `Memory.knowledge/history/read/neighbors/access_hints/record_delivery`；复用返回的 canonical ID 和版本值，不在交付时回查当前记录补旧版身份。无表名前缀的 ID 是原始字符串 key；字符串 `123` 与数字 canonical `member:123` 不同，前者的完整形式为 ``member:`123` ``。

```powershell
memory search --text '主题'
memory search --text 'A-17' --mode hybrid --literal
memory search --text 'memory-example.md' --mode hybrid --literal
```

底层 search 默认按项目 `memory.search_mode`，可显式覆盖 `--mode vector|hybrid`；编号、文件名和完整短语用 `hybrid --literal`，直接子串命中带 lexical_rank，仍须核实语义补充；`vector --literal` 明确失败。CLI search 与 Python `Memory.vector_search/hybrid_search` 均返回 `{matches, vector_coverage}`，兼容索引缺失与无命中分别可见，模型错误原样保留。旧 text 配置升级见 [版本升级](setup-project.md#版本升级)。

brief、search、knowledge 和 read 只读已发布知识及所存依据；来源已登记不等于知识已更新。`changes --scope` 显式发现原件变化，维护负责后续接受；查询不会等待维护或默认审计。预算外材料保留补读入口，实际问题用 [反馈](#使用反馈与手动审计) 留待单一维护 owner 处理。

## 备份与恢复

basePack 客户端自动读凭据；原生 SurrealDB CLI 使用自己的 SURREAL_USER/PASS。下面只为该次原生导出临时设置它们，不把这段加入新 shell 的记忆入口：

```powershell
$ErrorActionPreference = 'Stop'
$json = & $python -X utf8 -m basepack --config $config config show
if ($LASTEXITCODE -ne 0) { throw "config show failed ($LASTEXITCODE)" }
$settings = $json | ConvertFrom-Json
$env:SURREAL_USER = $settings.memory.username
$env:SURREAL_PASS = [IO.File]::ReadAllText($settings.memory_password_file)
try {
    & $surreal export --endpoint $settings.memory.endpoint --namespace $settings.memory.namespace --database $settings.memory.database '<backup.surql>'
    if ($LASTEXITCODE -ne 0) { throw "Surreal export failed ($LASTEXITCODE)" }
} finally {
    Remove-Item Env:SURREAL_USER, Env:SURREAL_PASS
}
```

恢复时先为新的物理目录/端口启动认证服务，保留原 project_id；从该目标配置读取用户名及同一密码文件，再以原生 `import` 替换上述 `export`。缺失凭据先恢复正确文件，不给已有库重新生成密码。恢复后核快照、图关系和检索。

恢复集合包括 export、配置、原凭据、业务原件、受管 Codex 导出、codex-attachments 原件与定位回执、`memory.data_dir` 下的 assets 图片快照。数据库内的知识版本、演变关系、依据、更正、旧快照、已阅/延期细化处置、反馈、访问状态及 delivery_id 去重记录随 export 恢复；旧版备份不会凭空补齐后来新增的状态或缺失历史。新目录保留 project_id，使用独立目录/端口，再验证原文定位、知识版本、关系、检索、反馈及同 delivery_id 重试。兼容向量可随 export 恢复，或从接受表示与原图重新 embed；访问记账不要求重建向量。运行中的库使用原生 export；复制物理目录先停写、停止服务。长期备份由明确恢复需求决定目的地与保留周期，不默认叠加完整备份。凭据不随源码发行；清理前核原件/旧依据引用及活跃控制/未明发布。
