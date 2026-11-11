# 项目记忆

记忆在本项目的 SurrealDB 中保存文件摘要、章节摘要、原文块、图片描述与定位，并保留层级、原文范围、语义关系和修改依据；图片原字节快照保存在项目记忆目录的 assets 中。宿主订阅 agent 负责智能分块、摘要、识图、建图和评分，数据库执行存储、事务与查询。记忆使用共享模型服务，支持 `vector` 与 `hybrid`，新项目默认 `vector`。小文件不必虚造章节。

## 启用

按 [项目接入](setup-project.md#启用记忆) 选独立目录、回环 endpoint 和 UUID，再按 [项目 SurrealDB](administrator.md#项目-surrealdb) 准备认证服务与唯一密码文件，在独立调用核 ready/init/brief。同项目多聊天复用服务，另一个项目使用自己的物理目录、端口及 UUID；通用 exe 和模型可共用。服务在查询期间保持运行。前台排错可在普通用户终端直接执行同一个 serve.ps1，其 cwd 与 endpoint 仍来自目标配置。

普通 init 只生成配置和未启用记忆的入口；memory init 才安装 schema 并绑定 UUID、刷新 instructions 与 AGENTS 的记忆指令块。共用托管块更新保留块外原字节；重复刷新幂等，损坏标记明确报错。误连其它 UUID 的库会失败。每个新进程按 [新 shell 接续](setup-project.md#新-shell-接续) 使用本机 Python 与显式配置运行 brief；客户端自动读 password_file（默认 memory_dir/password.txt）。升级或搬迁后重新 memory init 刷新定位；只用资源工具无需记忆数据库。

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
memory maintain --holder '<本thread身份>' --control '<memory.data_dir>/maintenance/<全新标识>.control'
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

宿主有可取消子任务句柄及任务开始/完成事件时，分配稳定且全新的 control，与业务并行运行预检。程序预检前原子取得项目所有权；每个 thread 仍可 brief、报告问题及正常业务：

```powershell
memory maintain --holder '<本thread身份>' --control '<memory.data_dir>/maintenance/<全新标识>.control' --output '<project-root>/tmp/<run>/summary.json'
```

默认面向整个项目的受管来源，不按当前业务任务的文件缩小维护范围。Git 项目枚举项目内已跟踪和未忽略的未跟踪文件，并加入 `memory.source_scope` 显式包含项，排除工具状态、环境与缓存；非 Git 项目使用声明的 `source_scope`。所有已登记来源、历史 pending/未接受范围和可归属 Codex 原件持续参与维护。`--scope <文件或目录> ...` 只覆盖本轮新文件发现，不把历史来源限制到该范围。无需为日常维护递归扫描 `.`；不支持的二进制材料留缺口，读取失败保留原错。

零行文字来源且没有活动知识时，只需登记来源，不创建无效行范围的 member。已有正文被清空时，仍须退役旧成员并处理依赖；完成后不反复派发该空来源，重新出现正文会继续发现。

预检先按 [Codex 绑定](setup-project.md#codex-项目聊天接入) 取得本次可读的持久化聊天截点，再比较来源及旧成员实际接受版本。Git 干净仍可能有尚未接受的原文。发现清单、聊天采集、语义接受和向量覆盖分别检查，不能据其中一项声称全部项目材料已接受。`changes` 提供显式变化查看，`maintain` 才负责机械更新与语义交接；查询不调用两者。

程序在依据闭合时处理原字节 hash 相同的元数据变化、完整正文仅 CRLF/LF 变化，以及有唯一定位且上下文可确认未变的原文块；相互依赖的机械候选共同发布，无法证明依赖仍有效的范围留给语义共读。完整回执保留机械批次、旧/新行映射、变化片段、受影响成员与关系；换行归一只用于比较，快照仍按真实原字节保存。编码输入及身份未变才复用向量；实际输入变化按现有 apply 合同编码。已有 stale、更正、退役或语义证据不足的范围保留待核，局部文字相同不表示父级摘要或关系均有效。

`acquired=false` 时返回已有 owner 的 holder/run_id/执行状态，跳过自身维护并继续业务；显式维护请求需报告该阻塞。`acquired=true` 时返回机械计数、`needs_semantic`、`receipt`、`control`、来源/采集边界及必要的 `worker`。未决反馈也触发语义维护，原件未变或 pending 为零并不关闭它。`needs_semantic=false` 时不创建语义 agent；为 true 时，宿主实际设置 `worker.model` 和 `worker.reasoning_effort`，干净历史派协调者，只传：

```text
Run the following command and follow the `prompt` field in its JSON output:
<worker.render_command>
```

子 agent 自己执行该命令并遵循返回的 `prompt`。默认命令为 `memory prompt --receipt <receipt> --control <control>`；它返回 `prompt`、`role`、`tier`、`model`、`reasoning_effort` 和 `render_command`。协调者与 reader 的英文提示词随 wheel 分发，详细分工只在模板维护。reader 使用 `--role reader --paths <项目文件...>`。角色与档位独立：协调者默认 tier2，reader 默认 tier1；显式 `--tier <tier>` 仍保留所选角色，按项目映射解析模型。提示词渲染只读配置、模板与回执，不读密码、不连数据库或模型，也不改控制文件或状态。

协调者按来源分批，安排 reader，首次生成跨来源关系时共读两端并统一发布；持续接批直到业务停止、固定候选耗尽或实际阻碍。每批 prepare/expected/apply 发布，不追加日常发布后的审计。采用固定候选与聊天截点；prepare 读各批当时的原件，不声称任务开始时全项目原子冻结。回执外新增材料留后续；处置、粗层和待细化分别报告。

采集与发布沿用自有 control。业务完成时，以本项目配置 `memory stop --control <control>`，取消协调者及后代；通过 `memory owner` 核发布状态，再 `memory release --control <同一control>`。stop 不撤销已获准提交，release 要求已停止且无未完成/未明发布。control 是协作授权凭证，只给持有者及其 worker，不能复用或按清理习惯删除。失败保留原错与 owner，业务答复报告余项。异常遗留先独立核旧持有者/后代已结束及事务结果已解决，再显式 `memory recover-owner --run-id <id> --owner-ended --publication-resolved`；不按文件年龄抢占。此机制用于协作互斥，不隔离有文件系统访问权的对手。

自动小批接续已有积压，任务相关性只影响优先级。显式维护按授权范围交付实际处置、阻塞和余项，不以剩余数量或优先小批自行结案。普通业务结束不承诺清空历史。特殊任务可调整组织/范围或使用临时英文提示词，说明原因与覆盖。

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

```powershell
memory brief --task '当前任务'
memory search --text '主题'
memory search --text 'A-17' --mode hybrid --literal
memory search --text 'memory-example.md' --mode hybrid --literal
memory neighbors 'member:<id>'
memory read 'member:<id>'
```

brief 直接提供必须保留的信息、相关线索、来源与覆盖缺口。mandatory 不参加相关性筛选；其中 stale 条目是待核义务，不能当当前事实。search 未传 `--mode` 时读取项目 `[memory].search_mode`；新项目为 `vector`。显式 `--mode vector|hybrid` 覆盖本次查询；hybrid 融合跨层全文与兼容图文向量。当前知识缺少兼容索引会明确报错，模型失败保留原错。

编号、文件名和需保留完整字符的短语使用 `--mode hybrid --literal`：在路径、标题和正文中做大小写无关的子串匹配，直接命中排在语义补充结果前，并带 `lexical_rank`。它按完整字符段匹配，区别于分词全文查询；结果仍可包含语义补充，引用前须 read 核实。`vector --literal` 会报错，需显式选择 hybrid。

CLI `memory search` 与 Python `Memory.vector_search`、`Memory.hybrid_search` 统一返回 `{matches, vector_coverage}`；调用方从 `matches` 读取候选，两项 Python 方法不再接收 `include_coverage`。brief 保留知识 pending、`coverage_gaps`、`change_check` 与 `vector_coverage`，删除恒空 `changes/change_count` 和重复 `vector_pending/vector_pending_count`。

brief、search 和 read 只读已发布知识及对应原文快照，不扫描原件或等待维护。`changes --scope` 显式发现已登记来源及指定范围中的变化；未改原件只查元数据，深查才做完整 hash。独立 `maintain` 的默认发现与持续维护边界见 [自动维护](#自动维护与手动维护)。任务词未命中时，短项目地图仍提供前提线索。

向量查询和 brief 的相关通道报告当前已发布范围的 identity、总数、兼容数和待建范围；缺少兼容向量与真实无命中分别可见。升级旧 `search_mode = 'text'` 项目时，先用原客户端按需运行 `memory embed`，再以 `memory search --mode vector --text '<代表主题>'` 核已发布覆盖的 `total = compatible` 且 `pending = 0`；然后将配置改为 `vector` 或 `hybrid` 并升级客户端。若已安装新客户端，仍可先运行 `embed` 和显式 `search --mode vector` 检查覆盖，再切换配置。旧值与 `--mode text` 均不再支持。`memory sources` 列完整来源元数据，供手动深维护抽样；抽到的材料与旧图要实际共读，未发现新关系也如实记录。

read 只接受 member ID；语义 node/edge 经 neighbors 查看 `basis`，按每项的 `member`、`source_version` 和具体位置核实依据。文字使用：

```powershell
memory read '<basis.member>' --source-version '<basis.source_version>' --start-line <basis.start_line> --end-line <basis.end_line>
```

图片传同一 `source_version` 及存在的 `--locator '<basis.locator 的 JSON>'`，实际打开 `original.image_path`。引用的是 read 返回的 `original`；同时返回的 `member` 是当前记录，stable ID 更新后的当前摘要或行范围不能替代关系保存的旧依据。同一 source 的已发布旧版本继续可读；成员跨 source 移动后，须有成员历史证明它曾属该来源，不要求逐版本的成员接受记录。新快照的 `original.path` 使用保存的出处；旧快照缺路径时优先使用请求版本的历史路径，否则须有唯一可核的同来源成员路径，不保证恢复未记录的精确历史路径。neighbors 默认展开当前关系，历史复核显式加 `--include-stale`。原件变化或缺失时仍读已发布版本的快照；快照缺失、损坏或路径歧义时返回错误。

当前 ID 合同支持字符串与整数 key。无表名前缀时是原始字符串 key；带 `member:`、`node:` 等前缀时是数据库 canonical ID，可直接沿用返回值。字符串 key `123` 与 canonical `member:123` 的数字 key 不同；字符串形式为 ``member:`123` ``。含冒号的 key 使用完整 canonical ID。

任务已知少量文件时，启动 brief 后可以直接批量读取；需要发现位置、未点名前提或跨材料依据时，再用记忆检索。父级摘要用于补背景或条件，选证据时避免重复已选原文块。

工作 agent 可只委托一次，使用 [项目配置](setup-project.md#agent-模型等级) 的检索等级（默认 tier1），让 worker 完成多轮检索、父子/语义展开、原文核实和评分，再用 `rank --input <scored.json> --budget <文字字符数>` 排序交付实际内容。rank 按依据版本、读取位置及实际表示去重，区分同一成员的历史版本/范围、摘要或标题更正及图片不同区域。词法分数与 agent 分数不同。超预算证据保留补读入口，不静默截掉条件；工作 agent 仍可自由补读。

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

恢复集合包括 export、配置、原凭据、业务原件、受管 Codex 导出、codex-attachments 原件与定位回执、`memory.data_dir` 下的 assets 图片快照。数据库内的摘要、依据、更正、旧快照、已阅/延期细化处置及反馈记录随 export 恢复；恢复旧版七表备份不会凭空出现后来报告，原生导出须保留新增反馈表和未决记录。新目录保留 project_id，使用独立目录/端口，再验证原文定位、关系、检索和反馈。兼容向量可随 export 恢复，或从接受表示与原图重新 embed。运行中的库使用原生 export；复制物理目录先停写、停止服务。长期备份由明确恢复需求决定目的地与保留周期，不默认叠加完整备份。凭据不随源码发行；清理前核原件/旧依据引用及活跃控制/未明发布。
