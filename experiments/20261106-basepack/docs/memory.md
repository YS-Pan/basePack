# 项目记忆

记忆在本项目的 SurrealDB 中保存文件摘要、章节摘要、原文块、图片描述与定位，并保留层级、原文范围、语义关系和修改依据；图片原字节快照保存在项目记忆目录的 assets 中。宿主订阅 agent 负责智能分块、摘要、识图、建图和评分，数据库执行存储、事务与查询。记忆使用共享模型服务，支持 `vector` 与 `hybrid`，新项目默认 `vector`。小文件不必虚造章节。

## 启用

本文描述 0.8.0 候选，是否采用免认证边界仍待最终决定。按 [项目接入](setup-project.md#启用记忆) 先选独立目录、显式回环 endpoint 和 UUID，再按 [项目 SurrealDB](administrator.md#项目-surrealdb) 核风险后启动，在独立调用核 ready/init/brief。该候选允许本机客户端及可触达回环端点的恶意网页写库，CORS 不阻止简单 POST；UUID 只防误连。同项目多聊天复用服务，另一个项目使用自己的物理目录、端口及 UUID；通用 exe 和模型可共用。服务在查询期间保持运行。前台排错可在普通用户终端直接执行同一个 serve.ps1，其 cwd 与 endpoint 仍来自目标配置。

普通 init 只生成配置和入口；memory init 才安装 schema 并绑定 UUID、增加记忆启动指令。误连其它 UUID 的库会失败。每个新进程按 [新 shell 接续](setup-project.md#新-shell-接续) 直接使用 instructions 中的 Python 与显式配置运行 brief，无需密码环境变量或密码文件，不依赖上一次部署 shell。已有配置升级时补齐当前 memory 字段并重新 memory init 刷新记忆入口；只用资源工具无需记忆数据库。

## 首建与维护

将本轮输出写到项目 `.basepack/memory/`，并为并发批次选择不同文件名。以下 PowerShell 函数使每个依赖命令非零即停止；`--output` 由程序写 UTF-8 JSON，避免使用 shell 默认编码保存取证。若把 PowerShell 示例保存成 `.ps1`，Windows PowerShell 5.1 使用带 BOM 的 UTF-8；JSON 与原件仍由程序写普通 UTF-8：

```powershell
$python = '<instructions 中的 absolute-python.exe>'
$config = '<absolute-project-config>'
$OutputEncoding = [Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = $OutputEncoding
function memory {
    & $python -X utf8 -m basepack --config $config memory @args
    if ($LASTEXITCODE -ne 0) { throw "memory command failed ($LASTEXITCODE)" }
}
memory prepare --paths '说明.md' '决定.md' --output '<reading.json>'
# 阅读 prepare 输出，写出 agent-batch.json 后继续。
memory apply --batch '<agent-batch.json>'
memory changes --scope '资料目录'
```

`prepare --paths` 接受文件而非目录。需要处理目录时先枚举文件，再传项目相对路径，例如：`Get-ChildItem -File 资料目录 | ForEach-Object { Resolve-Path -Relative $_.FullName }`，按实际范围选择文件。数据库返回 HTTP 413 时，错误包含实际 SQL 请求字节数；服务容量未知。按来源手动拆成小批，每批保留 prepare 的 expected 和事务原子性，关系两端依据仍需共读。

prepare 时包括本批所用依据与关系两端的材料；它提供新旧编号原文、已有与关联成员、节点、关系及 expected 知识版本，图片返回可打开的原图路径。关联记录的来源原文仍需 read 或扩充 prepare 范围核实。将材料交给订阅 agent，在同次阅读中选择最终块边界并生成摘要、节点和图边；结构备读单元只用于定位。批次 JSON 合同与操作流程在 `memory guide` 返回的已安装 skill 中，源码维护源为 [SKILL.md](../src/basepack/memory/SKILL.md)。

apply 核对来源版本，以及本批改写、退休、更正目标、实际使用的既有依据成员和关系两端的 expected 版本，再原子写入；无关 expected 不阻塞并行，缺 expected 仅允许本批新建记录。原文块由程序按范围取原词，摘要、边界、依据、历史与更正持久保存。旧草稿冲突时重新 prepare、共读后再提交。原件变化作为待维护信息，已发布知识及其依据快照仍可查询；受影响内容须在维护时共读，未变输入与兼容向量可复用，文件追加的新内容必须重核完整摘要。部分摘要显式保存 coverage_gaps。接受删除保留旧依据，相关主张按剩余证据重核；仅登记更正而未同批替换的错误内容标待核并排除查询。再次共读、apply 并查询新结果后，才算完成增量维护。向量模式在 apply 事务前准备候选编码，内容与匹配向量一起发布。深检查使用 `changes --scope <文件或目录> --deep`。

新内容由 apply 使用 [共享 embedding](resources.md) 编码；已有内容补建或重建索引时运行 `memory embed`，不另外加载模型。文件/章节使用已接受摘要，块使用原文，图片使用原始图片；兼容且输入未变的向量复用。超限保留原错误，交回原阅读 agent 调整分块或摘要，不能静默截断。模型不可用时停止本批发布或查询，并保留原错误。

图片先由视觉 agent 实际打开，描述与 OCR 单独标明，程序按 hash 保留必要原字节快照。必要 PDF 页可由宿主读取/渲染为项目内图片，locator 记录原文件、版本、页与区域；原 PDF 变化时重新核相关页面，不声称自动解析所有 PDF。

## 自动维护与手动维护

宿主有独立工具任务、可取消子任务句柄及任务开始/完成事件时，业务开始后并行运行确定性预检，业务无需等待：

```powershell
memory maintain --control '<本任务唯一control>' --output '<maintenance-summary.json>'
```

默认使用项目 `source_scope`，`--scope <文件或目录> ...` 可覆盖本轮范围。预检先按 [Codex 绑定](setup-project.md#codex-项目聊天接入) 采集本次可取得的持久化聊天截点，再比较登记来源、声明范围及旧成员实际接受版本。Git 干净仍可能有尚未接受的原文。`changes` 提供显式变化查看，`maintain` 才负责机械更新与语义交接；查询不调用两者。

程序直接处理原字节 hash 相同的元数据变化、完整正文仅 CRLF/LF 变化，以及有唯一定位且上下文可确认未变的原文块。完整回执保留机械批次、旧/新行映射、变化片段、受影响成员与关系；换行归一只用于比较，快照仍按真实原字节保存。编码输入及身份未变才复用向量；实际输入变化按现有 apply 合同编码。已有 stale、更正、退役或语义证据不足的范围保留待核，局部文字相同不表示父级摘要或关系均有效。

预检简报返回 `mechanical_batches`、`reused_chunks`、`semantic_sources`、`pending_relations`、`needs_semantic`、本地 `receipt` 路径和 `codex` 采集状态。`needs_semantic=false` 时不创建语义维护 worker；为 true 时只把必要变化、受影响摘要/关系及回读入口一次交给订阅 worker，按来源接续小批。worker 按需展开新旧原文，通过 prepare/expected/apply 原子发布。部分机械批次已经完成，其余未接受范围仍跨任务可发现。

采集与语义发布使用同一任务 control。worker 的 `memory apply --batch <batch.json> --control <control>` 沿用该控制文件；业务完成时宿主运行无需配置的 `memory stop --control <control>`，再取消该任务 worker，不等待编码或已进入提交的短事务。stop 先于提交仲裁时，候选不会发布；已采集原文和已发布批次保留，下次继续未接受范围。stop 失败保留原错并仍取消 worker，不能据此声称阻止发布。宿主缺少生命周期能力时说明自动维护不可用。

自动小批可接续既有积压，任务相关性只影响优先级。积压较多时可提醒用户另行发起手动深维护，不设置停用自动维护的数量阈值，也不承诺任务结束前清完历史。手动深维护由用户发起，沿同一流程更全面共读旧材料与关系。检索 worker 和维护 worker 各自执行。

## 聊天来源与精确回读

Codex 维护采集真实用户消息与可取得的助手文字，保留 thread/turn/item/part 身份和角色；系统、AGENTS、hook 与工具元数据不冒充用户 prompt。同一线程分页内重复的 turn/item 按身份去重，内容冲突保留错误；人类有意重复发送仍是不同消息。跨线程不按文字去重，完整继承身份尚未证实。每次以已捕获的持久化消息截点分页，当前任务中新增长度下次接续。采集只更新受管原件，不表示已经阅读、总结或发布知识。

受管聊天原文保存在 `memory.data_dir/codex/<thread>.txt`，版本 hash 属于该导出的真实 UTF-8 字节。接受后沿现有 source_version 保存快照；`read` 的 `original.chat_locations` 从所选已核快照返回聊天链接、thread/turn/item/part、UTF-8 字节范围及本次读取的正文交集，生成头与分隔符不当作人类原文。旧已发布版本可在原聊天续写或修订后继续核实。

可读取且格式受支持的 `localImage` 按内容 hash 复制到 `memory.data_dir/codex-attachments/`，作为独立图片原件进入同一维护范围；采集回执保留 chat part 身份，语义 worker 实际打开图片，并将该身份作为 locator 接受。缺失或不支持的附件留 gap；真实聊天附件仍未验，不能据模拟 PNG 回归宣称全部附件可用。

当前宿主列表中的部分项目/父子字段缺失时依项目根与 worktree 证据归属；显式 subagent 引用须以直接 thread/read 返回的父级身份核对且无项目冲突，才递归采集。无法确认的范围明确留 gap。附件不可取时、引用的 subagent 未能列出或读取时也保留缺口，不按不存在退役旧知识。完整分叉/继承身份、附件原件及全部聊天覆盖仍未完成真实验收；采集回执、语义待核与向量覆盖分别检查，`pending=0` 不等于全部聊天已接受。

## 最小闭环示例

在已完成 init/brief 且共享模型服务可用的干净试用项目执行 [memory_minimal.py](../examples/memory_minimal.py)。配置 `memory.search_mode` 为 `vector` 或 `hybrid`。它新建四行 UTF-8 的 `memory-example.md`，拒绝覆盖同名文件，并依次 prepare → 生成完整批次 → apply（含编码）→ 按编号和文件名查询 → read/neighbors；每个子命令使用 `subprocess.run(check=True)`，apply 失败后即停止。该脚本用于检查命令闭环，真实材料的理解与批次制作由宿主 agent 按 skill 完成。

```powershell
$python = '<instructions 中的 absolute-python.exe>'
$config = '<absolute-project-config>'
& $python -X utf8 '<basepack-repo>/experiments/20261106-basepack/examples/memory_minimal.py' --config $config
if ($LASTEXITCODE -ne 0) { throw "memory example failed ($LASTEXITCODE)" }
```

示例的批次和编号原文保存在项目 memory 目录下本次独有的 `example-<UUID>/`；`expected` 原样取自 prepare，source 的 path/revision 也直接沿用。批次包含以下真实 parent/evidence，所有文字成员都有 1-based 闭区间；chunk 不写 text，由程序取第 3–4 行原词：

| 成员 ID / kind | 行范围 | parent | evidence |
| --- | --- | --- | --- |
| `example-file` / file | 1–4 | 无 | ``member:`example-chunk` `` |
| `example-section` / section | 2–4 | ``member:`example-file` `` | ``member:`example-chunk` `` |
| `example-chunk` / chunk | 3–4 | ``member:`example-section` `` | 空 |

随包 [skill](../src/basepack/memory/SKILL.md#minimal-batch) 也保留不依赖仓库文件的完整批次例子。文字成员缺起止行字段会报告批次位置、成员 ID 与字段；不存在的 read 目标会明确报出 ID。修正输入后重新运行，失败批次没有部分写入；保留原错误，不继续下游命令。

`memory guide`、`memory rank --input <scored.json> --budget <字符数>` 和 `memory stop --control <control>` 只处理自身输入，无需项目配置；其余记忆动作仍须显式 `--config`。评分文件或控制文件错误保留原始信息。

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

`search` 的 CLI 与 Python 接口统一返回 `{matches, vector_coverage}`；Python 调用方从 `matches` 读取候选，不再接收裸列表或使用 `include_coverage`。brief 保留知识 pending、`coverage_gaps`、`change_check` 与 `vector_coverage`，删除恒空 `changes/change_count` 和重复 `vector_pending/vector_pending_count`。

brief、search 和 read 只读已发布知识及对应原文快照，不扫描原件或等待维护。`changes --scope` 显式发现已登记来源及指定范围中的变化；未改原件只查元数据，深查才做完整 hash。独立 `maintain` 默认使用配置的 `source_scope` 发现新文件，并接续已有来源及未接受范围。任务词未命中时，短项目地图仍提供前提线索。

向量查询和 brief 的相关通道报告当前已发布范围的 identity、总数、兼容数和待建范围；缺少兼容向量与真实无命中分别可见。升级旧 `search_mode = 'text'` 项目时，先用原客户端按需运行 `memory embed`，再以 `memory search --mode vector --text '<代表主题>'` 核已发布覆盖的 `total = compatible` 且 `pending = 0`；然后将配置改为 `vector` 或 `hybrid` 并升级客户端。若已安装新客户端，仍可先运行 `embed` 和显式 `search --mode vector` 检查覆盖，再切换配置。旧值与 `--mode text` 均不再支持。`memory sources` 列完整来源元数据，供手动深维护抽样；抽到的材料与旧图要实际共读，未发现新关系也如实记录。

read 只接受 member ID；语义 node/edge 经 neighbors 查看 `basis`，按每项的 `member`、`source_version` 和具体位置核实依据。文字使用：

```powershell
memory read '<basis.member>' --source-version '<basis.source_version>' --start-line <basis.start_line> --end-line <basis.end_line>
```

图片传同一 `source_version` 及存在的 `--locator '<basis.locator 的 JSON>'`，实际打开 `original.image_path`。引用的是 read 返回的 `original`；同时返回的 `member` 是当前记录，stable ID 更新后的当前摘要或行范围不能替代关系保存的旧依据。neighbors 默认展开当前关系，历史复核显式加 `--include-stale`。原件变化或缺失时仍读已发布版本的快照；快照缺失或损坏时返回错误。

当前 ID 合同支持字符串与整数 key。无表名前缀时是原始字符串 key；带 `member:`、`node:` 等前缀时是数据库 canonical ID，可直接沿用返回值。字符串 key `123` 与 canonical `member:123` 的数字 key 不同；字符串形式为 ``member:`123` ``。含冒号的 key 使用完整 canonical ID。

任务已知少量文件时，启动 brief 后可以直接批量读取；需要发现位置、未点名前提或跨材料依据时，再用记忆检索。父级摘要用于补背景或条件，选证据时避免重复已选原文块。

工作 agent 可只委托一次，使用 [项目配置](setup-project.md#agent-模型等级) 的检索等级（默认 tier1），让 worker 完成多轮检索、父子/语义展开、原文核实和评分，再用 `rank --input <scored.json> --budget <文字字符数>` 排序交付实际内容。词法分数与 agent 分数不同。超预算证据保留补读入口，不静默截掉条件；工作 agent 仍可自由补读。

## 备份与恢复

使用原生 export 写文件：

```powershell
& $surreal export --endpoint '<endpoint>' --namespace '<namespace>' --database '<database>' '<backup.surql>'
if ($LASTEXITCODE -ne 0) { throw "Surreal export failed ($LASTEXITCODE)" }
& $surreal import --endpoint '<新目录服务的 endpoint>' --namespace '<namespace>' --database '<database>' '<backup.surql>'
if ($LASTEXITCODE -ne 0) { throw "Surreal import failed ($LASTEXITCODE)" }
```

以下命令用于候选免认证库，无需 username 或密码环境变量。既有认证库的迁移前导出沿原版本配置执行，保留回退凭据，不混用新旧客户端。备份集合包括 export、项目配置、业务原件、受管 Codex 导出、codex-attachments 原件与定位回执及 `memory.data_dir` 下的 assets 图片快照（默认 `.basepack/memory/assets/`）；数据库内的摘要、边界、依据、更正和旧文字快照随 export 恢复。新目录保留 project_id，使用自己的数据目录与端口，再核原文定位、图关系和检索。向量可随 export 恢复，也可从保留表示和原图重新 embed，无需重新总结；重编码使用已接受表示与保留的图片快照。运行中的库使用原生 export；复制物理目录须先停写并停止服务。长期备份目的地与保留周期由业务项目确定。
