# 项目记忆

记忆在本项目的 SurrealDB 中保存文件摘要、章节摘要、原文块、图片描述与定位，并保留知识版本、层级、原文范围、语义演变关系和修改依据；图片原字节快照保存在项目记忆目录的 assets 中。宿主订阅 agent 负责智能分块、摘要、识图、建图和评分，数据库执行存储、事务与查询。搜索使用共享模型服务，支持 `vector` 与 `hybrid`，新项目默认 `vector`。小文件不必虚造章节。

## 启用

按 [项目接入](setup-project.md#启用记忆) 选独立目录、回环 endpoint 和 UUID，再按 [项目 SurrealDB](administrator.md#项目-surrealdb) 准备认证服务与唯一密码文件，在独立调用核 ready/init/brief。同项目多聊天复用服务，另一个项目使用自己的物理目录、端口及 UUID；通用 exe 和模型可共用。服务在查询期间保持运行。前台排错可在普通用户终端直接执行同一个 serve.ps1，其 cwd 与 endpoint 仍来自目标配置。

普通 init 只生成配置和未启用记忆的入口；memory init 才安装 schema 并绑定 UUID、刷新 instructions 与 AGENTS 的记忆指令块。新库写入 schema marker 3；已绑定但缺少该标记的旧库须先离线桥接并 finalize，普通 init 明确拒绝，已合法建立的 J 不重置。共用托管块更新保留块外原字节；重复刷新幂等，损坏标记明确报错。误连其它 UUID 的库会失败。任务启动与 [新 shell 接续](setup-project.md#新-shell-接续) 以生成的 `.basepack/instructions.md#startup` 为准；客户端自动读 password_file（默认 memory_dir/password.txt）。升级或搬迁时先按 [配置维护要点](project-config-maintenance.md) 核实际路径，再运行 memory init 刷新托管块；instructions 块外旧路径另核。只用资源工具无需记忆数据库。

## 首建与维护

可重建的 reading、batch、排名和一次性验证放项目根受忽略的 `tmp/<任务或运行标识>/`；选留原证放根 `artifacts/runs/<运行标识>/`。数据库、凭据、原件/assets、control、仍在使用或恢复必要的回执保持配置指定的稳定位置；反馈在数据库内持久保存。这些受管副本和工作包可含机密内容，保管与公开边界见 [私有资料](#私有资料与分享边界)。控制文件可能早于回执创建，发布未明时不能清除。以下函数使依赖命令非零即停止；JSON 使用 UTF-8，保存成 `.ps1` 时为 Windows PowerShell 5.1 使用 UTF-8 BOM：

```powershell
$python = '<instructions 中的 absolute-python.exe>'
$config = '<absolute-project-config>'
$OutputEncoding = [Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = $OutputEncoding
function memory {
    & $python -X utf8 -m basepack --config $config memory @args
    if ($LASTEXITCODE -ne 0) { throw "memory command failed ($LASTEXITCODE)" }
}
memory maintain --mode manual --holder '<本thread身份>' --control '<memory.data_dir>/maintenance/<全新标识>.control' --retained
# 仅 acquired=true 时继续；已有 owner 时报告持有者。
memory prepare --paths '说明.md' '决定.md' --output '<project-root>/tmp/<run>/reading.json'
# 阅读 prepare 输出，作者显式完成本次 assignment，publisher 保存有序完成稿引用。
memory publish --completed '<completed.json>' --output '<新batch.json>' --control '<同一control>' --result '<result.json>'
memory stop --control '<同一control>'
memory release --control '<同一control>'
memory check-file-changes --scope '资料目录'
```

`prepare --paths` 接受文件而非目录。需要处理目录时先枚举文件，再传项目相对路径，例如：`Get-ChildItem -File 资料目录 | ForEach-Object { Resolve-Path -Relative $_.FullName }`。文字来源的 `snapshot_transport` 提前给出原文字节数、封装字节数、语句数和消息上限；错误保留路径及原始诊断，调用 agent 不承担例行 SQL 大小审核或拆包。

大来源仍以完整 `source.text` 保存，程序在同一事务内分段传输并组装，保留原文字节、hash、来源版本与原子接受，也支持原生导出恢复。当前回归样例覆盖到 8,943,755 原文字节，该数值不是通用上限。缩小语义 chunk 或抬高传输常数不替代整源快照处理。

prepare 时包括本批所用依据与关系两端的材料；它固定实际读到的原件及知识版本，提供新旧编号原文、已有与关联成员、节点、关系及私有标记，图片返回可打开的原图路径。已有 fresh 记录已钉的 basis／parent／endpoint 历史依赖自动按 `(ID, knowledge_revision)` 保全；缺失旧版本明确报错，不替换为 current。当前 expected 并发保护独立保留，private 沿实际版本传播；作者显式选择旧端点仍用下述 `--historical-versions`。长单行提供有界片段及 `locator:{start_col,end_col}`，使用 0-based Unicode 字符偏移、右端不含，行号仍为 1-based 闭区间。关联记录的原文仍需 read 或扩充 prepare 核实。将材料交给订阅 agent，在同次阅读中选择语义边界、摘要、节点和图边；结构备读单元只用于定位。批次合同在 `memory guide` 返回的已安装 skill 中，源码维护源为 [SKILL.md](../src/basepack/memory/SKILL.md)。

作者 draft 以 `prepare:{path,file_sha256}` 引用固定阅读包，选择 `sources:["项目相对路径"]` 并声明内容、位置、依据与处置。程序编译 source revision、expected 依赖闭包、UUID 与 private，作者不用抄写这些机械字段。新成员省略 ID，已有记录使用 prepare 中的 ID；局部成员／节点引用由编译器解析，跨 draft 保留作用域，重复更新报错。需要关联已观察的历史端点时，prepare 加 `--historical-versions <JSON文件>`，内容为 `{id,knowledge_revision}` 数组，固定其历史分类。冻结稿及映射必须保留，重试复用同一文件，已提交的相同批次返回原回执。旧库升级先按 [版本升级](setup-project.md#版本升级) 完成相应离线迁移。详细合同见[批次接口](../src/basepack/memory/SKILL.md#direct-batch-interface)。

`publish` 将核稿、freeze/validate、独占保存 frozen 和原 apply 顺序组合；CLI 与 Python 共用 `basepack.memory.publish` helper。`completed.json` 是有序 JSON 数组，每项为 `{"path":"<draft.json>","file_sha256":"<文件字节SHA256>","assignment":"<具体交付引用>"}`；相对路径按调用进程 cwd 解析。数组顺序即 draft 作用域顺序。一个完成稿可直接发布，多稿合组或拆组由 publisher 判断；各次发布各自原子。作者须针对该 assignment 显式交付，publisher 根据已有自有句柄声明完成；文件出现或整个聊天结束都不能代替它。

Python 可直接传列表：`from basepack.memory import publish; publish(memory, completed=references, output="new-frozen.json", control=control, result="result.json")`。已有 `prepare/read/neighbors`、prompt 渲染和直接 `freeze/apply` 仍可自由调用；已知步骤可在一次宿主 exec 中用普通 Python 顺序或条件组合，需要判断时返回 agent。格式、覆盖、证据和语义分块修订交回原作者，跨 scope 判断共读解决。

直接用 Python 编译提案时，显式传入项目配置以固定私有规则；CLI freeze 和 publish 自动使用当前项目配置：

```python
from basepack.memory.draft import compile_proposals
batch = compile_proposals(drafts, config=memory.config)
```

固定稿接续用 `memory publish --frozen '<原batch.json>' --control '<同一control>' --result '<result.json>'`，Python 对应 `frozen=`，保留原 batch_id 与 UUID。来源或作者稿改变时才经当前 prepare/必要阅读产生新 path/hash 并重新 freeze。数据库 batch receipt 是发布权威；本地 result 仅为详细投影，写失败后也接续同一 frozen，不能为补回执生成新 batch。短返回给各类写入和 invalidated 数量，详细 result 保存原 apply 结果（包括 invalidated IDs）、batch_id、frozen 路径与文件 SHA256；接续时 completed 为 null。`file_sha256`/`frozen_file_sha256` 是文件字节校验，DB `batch_hash` 是 apply 规范化内容身份。未知提交沿原 marker/owner 合同核定，保留 fixed frozen，不自动重投或 release。

0.17 作者提案使用固定 prepare 合同；切换前结清或明确作废旧作者稿，保留恢复原件，再按新客户端 prepare。已保存 frozen 的恢复沿对应版本的原始合同处理，不手工补造其规则或依赖字段。

apply 核对来源版本，以及本批改写、退役、更正目标、实际依据、父引用和关系端点的 expected 版本，再原子写入；无关 expected 不阻塞，缺 expected 仅允许本批新建记录。chunk 按范围取原词，作者通常省略text；显式提供text时，freeze先对固定prepare原文核验行/locator及精确文本，apply保留对冻结输入的核验。摘要、依据、更正和旧快照持久保存。旧草稿冲突重新 prepare、阅读后提交。作者完成必要理解、生成批次并由程序成功发布即完成普通批次，不追加独立语义复核、例行回读/检索抽查。失败或结果未明保持未决。

粗层摘要使用实际已读的精选chunks支持，保留独有事实及已有mandatory。已阅但无新增知识／重复可登记 `sources[].dispositions`；实际已读且有fresh粗层表示覆盖、只是暂不细化时才用 `deferred_refinement`。证据不可取得属于下节的unavailable，不能借细化延期表示该证据已读。字段与定位细则见[批次合同](../src/basepack/memory/SKILL.md#direct-batch-interface)。

新内容由 apply 使用 [共享 embedding](resources.md) 编码；已有内容补建或重建索引时运行 `memory embed`，不另外加载模型。文件/章节使用已接受摘要，块使用原文，图片使用原始图片；兼容且输入未变的向量复用。超限保留原错误，交回原阅读 agent 调整分块或摘要，不能静默截断。模型不可用时停止本批发布或查询，并保留原错误。

图片先由视觉 agent 实际打开，描述与 OCR 单独标明，程序按 hash 保留必要原字节快照。必要 PDF 页可由宿主读取/渲染为项目内图片，locator 记录原文件、版本、页与区域；原 PDF 变化时重新核相关页面，不声称自动解析所有 PDF。

### 证据不可得与细化延期

0.18.2源码新增来源级 `unavailable_gaps`；实际安装与验收以[部署合同](../../../devDoc/system/deployment.md)为准。作者逐项声明当前证据不可得，形状为 `sources:[{path,unavailable_gaps:[{member,knowledge_revision,gap,reason}]}]`。member必须是prepare中同路径／当前原件版本的fresh、非retired成员，本批不改写或退役它；knowledge_revision及gap须精确匹配该成员当前版本和原 `coverage_gaps` 文本，reason写清已核的不可得原因。

这只抑制已匹配coverage_gaps的重复semantic派工；原缺口、可读未覆盖范围、member／知识版本／向量／J保持不变。stale、missing、changed、uncovered及feedback各自继续触发处理，不把“不可得已记录”当作证据已补齐或范围已读完。`deferred_refinement`仍仅表示实际已读粗层覆盖范围的细化延期，两者可独立记录。

同raw／path省略该字段会保留既有记录；显式list替换整个列表，`[]`清空，新raw不继承。公开source只能保存来自已确认public成员版本的记录；private或分类未核成员不能派生到公开source。private→public时若既有非空记录，须显式清理或重判，该源进入语义处理；独立安全来源仍可机械处理。

旧frozen缺少此字段时保持缺省，不手补空数组或改原稿字节，以免改变batch hash；需要新增／清空记录时，从当前prepare产生新提案并重新freeze。

## 自动维护与手动维护

任务开始按生成入口取得一次 brief，同任务接续沿用。直觉预计不超过十分钟时跳过整个自动 maintain，包括预检、采集和取得 owner；明显更长时，在宿主有可取消子任务句柄及开始/完成事件的条件下，与业务并行启动一次全项目维护。范围明显扩大时重新判断，必要时首次启动，不等待计时门槛。子任务遵循委托和渲染提示词，不递归开维护。用户明确要求维护时用 `--mode manual`，不受时长门槛限制；缺少宿主生命周期能力时说明自动维护不可用，采用显式维护任务。

原父用自己的宿主 thread 身份启动。若已知本轮剩余 subagent 容量，传 `--available-subagents <A>`。此数扣除检索等实际占用，程序再从中预留协调者恢复席位：

```powershell
memory maintain-start --mode automatic --holder '<原父 thread 身份>'
```

`prepared` 返回 `attempt_id`、control、`spawn_arguments` 与收尾命令。原父保存这些值，按返回参数实际派一次协调者。遇 `busy` 报告已有 owner。遇 `capacity_unavailable` 保留语义余项，可在授权范围内使用普通 `memory maintain --available-subagents 0` 做机械维护。此时使用原父 holder、新 control 和相应来源选择，沿普通维护收尾。该路径不自动请求采集审批。

绑定 Codex 的项目可传 `--collection <成功回执>` 消费已有采集，或传 `--retained` 使用已保留原件。省略两个选项时，由协调者按 `memory collect-prompt --attempt <id>` 采集新原件。本轮授权允许采集失败后继续使用已有原件时，原父传 `--allow-retained`。受影响的 Windows Codex 在宿主允许 Auto-review 时仅为独立采集命令请求一次审批。采集及等待审批期间，本次尝试不持有维护 owner。协调者随后在普通沙箱中使用原父 holder/control 执行预检。纯文件项目直接进入预检。

已知普通沙箱无法采集且没有合格 Auto-review 路径时，报告采集缺口，常规维护保持非交互。命令启动前拒绝审批时记录宿主结果，启动后失败则保留原错和可取得的回执。显式维护仅在授权范围内改用保留原件，其当前聊天 freshness 保持未知。加载采集回执核项目归属和原件 hash，回执固定逐聊天观察，prepare 固定实际读到的版本。分别报告采集与语义维护结果。

默认面向整个项目的受管来源，不按当前业务任务的文件缩小维护范围。Git 项目枚举项目内已跟踪和未忽略的未跟踪文件，并加入 `memory.source_scope` 显式包含项；非 Git 项目使用声明的 `source_scope`。默认发现还自动加入根 `private/` 独立 Git 的已跟踪及未忽略新文件，尊重内层忽略规则，无需逐项配置 source_scope；它们仍属同一项目 UUID、数据库与维护生命周期。不存在 `private/` 时正常完成默认发现。各范围排除 `.git/`、工具状态、环境与缓存。

默认工作集包含所有已登记来源（含已删除来源）、历史 pending/未接受范围和可归属 Codex 原件。`--scope <文件或目录> ...` 实际限制新增、已登记、缺失、聊天及待处理来源到指定项目相对路径，范围外工作保留待办；不自动追加 private 范围。无需为日常维护递归扫描 `.`；不支持的二进制材料留缺口，读取失败保留原错。

零行文字来源且没有活动知识时，只需登记来源，不创建无效行范围的 member。已有正文被清空时，仍须退役旧成员并处理依赖；完成后不反复派发该空来源，重新出现正文会继续发现。

采集时按 Codex 项目绑定刷新本轮可读的持久化聊天截点。维护随后比较选定来源及旧成员实际接受版本。Git 干净仍可能有尚未接受的原文。`maintain` 负责机械更新与语义交接。[来源检查](#来源检查) · [Codex 绑定](setup-project.md#codex-项目聊天接入)

程序在依据闭合时处理原字节 hash 相同的元数据变化、完整正文仅 CRLF/LF 变化，以及有唯一定位且上下文可确认未变的原文块；相互依赖的机械候选共同发布，无法证明依赖仍有效的范围留给语义共读。完整回执保留机械批次、旧/新行映射、变化片段、受影响成员与关系；换行归一只用于比较，快照仍按真实原字节保存。编码输入及身份未变才复用向量；实际输入变化按现有 apply 合同编码。已有 stale、更正、退役或语义证据不足的范围保留待核，局部文字相同不表示父级摘要或关系均有效。

语义派工前的启动失败，只清理本进程已取得且确认无派工、无在途或未明发布的自有 owner，再抛出原始错误。清理也失败时保留两类错误；状态未明保留 owner 和恢复入口，他人 owner 不受影响。

### 有限任务池与两段式 Terra

本节描述0.18系列的有限任务池维护。实际安装与验收状态见[部署合同](../../../devDoc/system/deployment.md)，接受范围与余项见[进度](../../../devDoc/tasks/20261115-real-use-rectification/progress.md)。旧组织仍须按原固定回执收口，不能把任务池协议套给旧worker。详细设计维护源为[有限任务池合同](../../../devDoc/tasks/20261115-real-use-rectification/maintenance-waves.md)；安装后以 `memory guide` 返回的随包流程和CLI生成的命令、prompt与身份执行。新入口为 `memory wave`：create不传wave-id并返回该标识，其余动作均显式传 `--control <同一control> --run-id <owner run_id> --wave-id <wave_id>`。各动作字段以 `memory wave <action> --help` 为准，reader直接执行生成prompt中的命令。

1. 原父按 `maintain-start` 的派工参数启动 Terra，保留 stop 权限和实际句柄。Terra 首 turn 处理来源和预检，在预检取得 owner 且 `needs_semantic=true` 时初始化 reader 波次。无语义工作、所有权冲突或预检失败时将实际结果交原父。
2. Terra第一turn规划有限、可独立阅读写稿的语义任务，将每项的 `id/goal/paths/write_targets/outputs` 写入tasks JSON数组，用 `memory wave create --receipt <固定receipt> --control <control> --run-id <owner run_id> --tasks <tasks.json> --coordinator <实际非根Terra规范路径> --readers <N>` 建波；长组先发，工作量差异明显的任务分组。依赖前一波新发布知识的任务留下一波。N必须在1至min(任务数,固定reader上限)内，由规划者按工作量选择较小固定池，供多轮领取，不以容量满编为目标。程序预登记worker，保留Terra第二turn恢复名额；余量不再默认补无reader协调者。
3. Terra按create返回的 `workers[].spawn_arguments` 实际启动Luna，逐名运行 `started --worker <name> --handle <实际handle>`，失败则 `worker-failed --worker <name> --error <原错>`；全部登记后运行 `initialized`，交固定初始化回执并结束当前turn。Luna首turn先通过宿主事件等待带wave标识的go。原父任务保留全部实际句柄，确认Terra已空闲且全部成员已启动或明确失败后才运行 `memory wave seal`，并向已启动Luna发送一次go。未封口不得领取或退队，也不得提前产生最后通知；不凭等待时间推测Terra已空闲。
4. Luna循环 `claim`→`task-prompt --task-id <id>`→原文阅读／分块／摘要／关系及普通修稿→`submit --task-id <id> --drafts <固定稿路径...> --coverage <覆盖JSON> --errors <错误JSON>`，再领取下一项；worker动作同时传 `--worker <name>`，失败提交显式加 `--failed`。作者保持稿件及hash不变，修稿另交新引用。普通Luna无任务即原子更新活动状态并正常退队，不主动唤醒Terra。
5. 最后正常退队者核全波任务状态，保存固定执行回执并取得唯一通知资格；运行 `notification-pending` 后实际followup同一非根Terra，传稳定wave标识、回执路径及摘要，再用 `notification-result --accepted --result <实际宿主结果JSON>`（失败则改用 `--failed`） 记录结果。普通早退的完成消息只留在空闲Terra邮箱。程序的待通知状态不等于宿主已受理followup；实际宿主结果另记，重复通知按稳定wave幂等处理。
6. Terra第二turn用 `finish` 核固定引用和执行边界，按汇总覆盖与异常沿现有编译器唯一发布：`memory wave publish --completed <有序固定引用JSON> --frozen <稳定新frozen路径> --result <稳定结果路径>`。该调用固定publication intent，重入沿原frozen／结果接续，固定publication结果后即FINAL；正常成功不逐稿全文重读或加语义审计。followup受理后Terra可能先于通知ack完成，因此Terra不等ack、不做wave close，也不为此增加第三turn。原父任务观察Terra FINAL与最后Luna的通知ack／宿主终态后机械执行 `memory wave close`；pending结果未知时按宿主事实恢复，不重发通知。必要共读及普通修稿交相应作者，形成有限修复波。初始化、执行终态、发布接受及维护完成分别报告，任何一个回执都不代替其余结果。

已确认publisher终态、无提交且owner.publications为空时，原父任务可用 `memory wave publication-failed --error <原错> --publisher-ended --no-commit` 固定错误并终止旧intent，未发稿保留给有限修复波。未知提交仍保留原intent与owner，不能标失败或重发；先沿原固定frozen及数据库回执核结果。

任务的 `paths` 仅列当前stage的remaining.paths内拟处置来源；无stage时限原receipt的 `workset.included`，包含本轮已授权纳入的stable来源。它授权这些来源及其成员的必要修改；`write_targets` 协调共享节点／关系的写归属，空列表不让已授权路径的成员变成只读。可选 `read_paths` 只为额外共读，prepare可读两者，但draft.sources与member.path必须属于paths。图／feedback-only任务可用 `paths=[]`，必要时先检索；新发现来源不自动纳入本波接受；后续wave仍须满足当时的固定授权范围。

回执固定来源候选及采集观察，prepare固定实际阅读版本；冲突由作者重新prepare并正常修稿。共享节点／关系各有一个写owner，程序不代替语义判断。已接受后新改的原件不自动重开旧任务，回执外来源和后续未接受成果保留原件入口与有限后续范围。普通成功不追加例行全文审计，也不以一波结束宣布全授权范围完成。

### 同一轮的阶段接续

0.18的 `memory stage` 用于已关闭的finite-wave-v1边界；需要更换Terra上下文时，可沿原receipt／owner／control建立干净新协调者，维护轮次继续。先完成当前wave的发布及通知处置并close，handoff须含该 `wave_id`，其completed／remaining的paths、relations、feedback完整分割待交接scope；同时固定draft／publication结果引用、errors／jobs，并列出本run所有wave（含历史）中实际启动worker的已结束宿主句柄，以及本阶段publisher的已结束句柄。

宿主实际确认旧句柄结束后，程序核固定引用与交接中的终态声明，保存stage及hash并返回新worker；宿主按其spawn_arguments实际创建干净协调者，下一wave使用返回的stage／hash及remaining范围。stage不创建新owner，也不表示整轮维护完成。当前客户端拒绝旧组织receipt／stage，0.17历史材料只保留旧版收口证据，不能由0.18接续执行。

### 停止与恢复

业务结束时，原父先运行 `memory stop --attempt <attempt_id>`，再取消自己的协调者及实际后代。普通 `maintain` 轮次改用 `memory stop --control <control>`。核实迟到的宿主调用、后代终态和发布状态，并用 `memory owner` 确认本轮取得对应 owner 后，执行 `memory release --control <同一control>`。这些命令只需项目配置。stop 阻止新的预检与发布，已获准的提交仍可继续。失败或结果未明时保留原错与 owner，业务答复报告余项。control 是协作授权凭证，只给持有者及其 worker，每轮用新路径。

异常遗留先独立核旧持有者及后代已结束、事务结果已解决，再显式运行 `memory recover-owner --run-id <id> --owner-ended --publication-resolved`。任务池领取、回调处理和发布均核当前 owner/control/wave 与停止状态。若已在途的宿主调用在停止后唤醒 Terra，其第二 turn 按停止状态退出。未启动或失败的 worker、残留 claimed、全体异常消失和未受理通知保留原错及 owner，由原父据实际宿主终态恢复。

通知者已实际结束且宿主结果已核实时，原父任务可用 `memory wave notification-recover --accepted --evidence <实际宿主证据> --worker-ended --host-verified` 补记结果（失败则用 `--failed`）。该动作不发送或重试followup；仍为eligible、从未尝试的通知只能记failed。未核宿主事实时继续保留pending与owner。

自动小批接续已有积压，任务相关性只影响优先级。显式维护按授权范围交付实际处置、阻塞和余项，不以剩余数量或优先小批自行结案。普通业务结束不承诺清空历史；连续短任务的积压留下一次长任务或显式维护。特殊任务可按授权调整范围，固定名称和本轮容量仍由脚本提供。

## 使用反馈与手动审计

检索 worker 与调用 agent 共用 `memory feedback-report --kind knowledge|retrieval --issue '<疑点>'`。有目标带 `--target <ID> --observed-revision <观察时knowledge_revision>`；search/brief 保留当时版本，不能事后 read 新版冒充。无 ID 漏检提供 `--query '<查询>'` 或 `--source '<预期来源/定位>'`；可加 `--reporter '<身份>'`。轻量记录即可，业务继续，无需另做审计或完整修复方案。

报告无需维护 owner；`memory feedback-list` 默认返回未决（`--all` 含结果）。单一 owner 按当前版本及原件处理，沿 apply/corrections 修复后运行 `feedback-resolve <id> --control <同一control> --outcome fixed|invalid|duplicate|obsolete --result '<说明>'`；有目标需 `--expected-revision <当前版本>`。旧报告冲突不能覆盖新版，失败/未决保持可见。反馈是数据库运行状态，纳入导出恢复，不自摄入为业务知识。

仅用户明确表达记忆系统审计意图时，按该次范围启动手动审计；讨论该词、普通维护、实际问题均不自动触发。只读审计/记录可与维护并行，写入修复仍取得项目 owner。普通建立及修复的完成口径保持作者生成和程序提交。

## 来源检查

- `memory check-codex-capture [--codex-registry <json>] [--thread <id>]` 默认对照本项目的活跃和归档 Codex 聊天与采集记录，返回新增、可能变化、已覆盖和未知。对相关候选及用户点名的项目聊天加 `--thread`，逐段核对正文。跨项目引用通过宿主读取。按各聊天的采集位置报告未采集、已变化、实际补读和未知项。端点和 `updatedAt` 用于筛选候选，正文覆盖以逐段比较为准。返回的预检 pending 是当时的快照。
- `memory check-file-changes --scope <文件或目录> ... [--deep]` 按指定的项目相对路径对照磁盘与项目库登记的来源版本。加 `--deep` 同时校验内容哈希。Codex 状态库受限时，仍可连接项目库单独检查文件。通过维护工作集发现待重核摘要，并分别检查已发布知识的向量覆盖。

Windows Codex 沙箱已知会拦截 Codex 状态库访问，或检查实际遇到此类拦截时，如果宿主支持 Auto Review，agent 主动仅为本次 `memory check-codex-capture` 调用申请一次审批。获准后按原参数执行。审批不可用或被拒时，报告原因和未核对范围。

两条检查均为只读。旧名称 `freshness` 和 `changes` 分别是这两条命令的别名。

## 聊天来源与精确回读

独立 Codex 采集保留真实用户消息与可取得的助手文字，以及 thread/turn/item/part 身份和角色；系统、AGENTS、hook 与工具元数据不冒充用户 prompt。同一线程分页内重复的 turn/item 按身份去重，内容冲突保留错误；人类有意重复发送仍是不同消息。跨线程不按文字去重，完整继承身份尚未证实。每次以已捕获的持久化消息截点分页，当前任务中新增长度下次接续。采集只更新受管原件，不表示已经阅读、总结或发布知识。

受管聊天原文保存在 `memory.data_dir/codex/<thread>.txt`，版本 hash 属于该导出的真实 UTF-8 字节。接受后沿现有 source_version 保存快照；`read` 的 `original.chat_locations` 从所选已核快照返回聊天链接、thread/turn/item/part、UTF-8 字节范围及本次读取的正文交集，生成头与分隔符不当作人类原文。旧已发布版本可在原聊天续写或修订后继续核实。

可读取且格式受支持的 `localImage` 按内容 hash 复制到 `memory.data_dir/codex-attachments/`，作为独立图片原件进入同一维护范围。语义回执的 `codex` 及 reader 提示提供项目 ID、本轮采集回执（如有）和保留聊天/附件目录；worker 按随包 skill 从采集记录或历史 framed 原件核对同项目及同附件的 chat part 身份，实际打开图片，再将原记录身份作为 locator 接受。附件缺失、身份不可核或格式不支持时留 gap；真实聊天附件仍未验，不能据模拟 PNG 回归宣称全部附件可用。

当前宿主列表中的部分项目/父子字段缺失时依项目根与 worktree 证据归属；显式 subagent 引用须以直接 thread/read 返回的父级身份核对且无项目冲突，才递归采集。无法确认的范围明确留 gap。附件不可取时、引用的 subagent 未能列出或读取时也保留缺口，不按不存在退役旧知识。完整分叉/继承身份、附件原件及全部聊天覆盖仍未完成真实验收；采集回执、语义待核与向量覆盖分别检查，`pending=0` 不等于全部聊天已接受。

## 最小闭环示例

在已完成 init/brief 且共享模型服务可用的干净试用项目执行 [memory_minimal.py](../examples/memory_minimal.py)。配置 `memory.search_mode` 为 `vector` 或 `hybrid`。它新建四行 UTF-8 的 `memory-example.md`，拒绝覆盖同名文件，并依次 prepare → 生成草稿 → freeze → apply（含编码）→ 按编号和文件名查询 → read/neighbors；每个子命令使用 `subprocess.run(check=True)`，apply 失败后即停止。该脚本用于检查命令闭环，真实材料的理解与批次制作由宿主 agent 按 skill 完成。

```powershell
$python = '<instructions 中的 absolute-python.exe>'
$config = '<absolute-project-config>'
& $python -X utf8 '<basepack-repo>/experiments/20261106-basepack/examples/memory_minimal.py' --config $config
if ($LASTEXITCODE -ne 0) { throw "memory example failed ($LASTEXITCODE)" }
```

示例在项目根 `tmp/example-<UUID>/` 保存固定 prepare 与作者提案；control 保留在实际 memory 目录的 maintenance 中，并显式取得、停止和释放 owner。示例维护实际限域到新文件，绑定 Codex 时明确用 retained。提案引用 prepare 路径/hash，程序编译 source revision、expected 和身份。批次包含以下 parent/evidence，范围为 1-based 闭区间；chunk 不写 text，由程序取第 3–4 行原词：

| 成员 ID / kind | 行范围 | parent | evidence |
| --- | --- | --- | --- |
| 位置 0 / file | 1–4 | 无 | `{"member":2}` |
| 位置 1 / section | 2–4 | `{"member":0}` | `{"member":2}` |
| 位置 2 / chunk | 3–4 | `{"member":1}` | 空 |

随包 [skill](../src/basepack/memory/SKILL.md#minimal-batch) 也保留不依赖仓库文件的完整批次例子。文字成员缺起止行字段会报告批次位置、成员 ID 与字段；不存在的 read 目标会明确报出 ID。修正输入后重新运行，失败批次没有部分写入；保留原错误，不继续下游命令。

`memory guide` 与 `memory rank --input <scored.json> --budget <字符数>` 无需项目配置。owner/stop/release/recover-owner 需显式配置定位本项目运行状态，但不需要数据库或密码；知识动作仍连接目标数据库。评分文件或控制文件错误保留原始信息。

## 启动与检索

任务开始执行一次 brief；同任务跨 shell 读写、反馈及维护收尾沿用已获内容，目标或上下文实质变化时按需补取。shell 初始化与任务启动的维护源是 [生成模板](../src/basepack/project/templates/memory-enabled.md)，实际 Python／配置见本项目 `.basepack/instructions.md#startup`。

brief 只读已发布 mandatory、概况入口与已知缺口，不做 embedding、任务搜索或原件扫描。mandatory 无条件保留；stale 条目保留为待核义务。概况从跨来源摘要／节点取得有界候选，默认展示 6 条时最多精算 48 条候选、总上限 96；候选按 UTC 日轮换展示采样，无持久状态，也不改变 J/C、hits 或年龄。候选组内按 Gaussian 访问区间上／下界保守排序，跨结构组交错，低权重始终保留检索资格；选中项披露实际模型、游标和区间。它仍须读取现有摘要／投影，并披露未映射来源、未读范围和遗漏，不承诺常数成本或完整语义覆盖，也不建立“当前理解”缓存。已知少量文件直接同批阅读；需要发现项目概况、任务前提、过去要求或跨材料依据时，用统一入口：

```powershell
memory retrieve --question '历史要求如何演变？'
memory retrieve --question '文档中的现行约束是什么？' --scope 'devDoc/' --budget 6000
```

不传 `--scope` 时为 `''`，表示全项目；`scope` 严格表示项目相对路径前缀，支持中文与空格。业务范围写在 `question`。上例 `devDoc/` 是本仓库的实际前缀。默认预算为 6000 字符。入口创建 `tmp/basepack-retrieval/<uuid>/request.json`，返回稳定的 `delivery_id`、request/work/delivery_receipt 路径与派工元数据；同一次问题用 `memory retrieve --request <已返回request>` 接续，不再传 question。未给问题或 request 时只返回所需输入。

CLI 准备派工。宿主按返回的 `task_name`、`model` 和 `reasoning_effort` 实际创建干净历史 worker，传英文启动句和 `render_command`，并接收其最终结果。检索档位初始为 1，可用 `--level 2` 等已配置档位覆盖本次选择。返回的 `level` 为整数。共享可用额度已知时传 `--available-subagents <A>`。同一问题复用自有句柄，独立并发问题用不同 `--slot`。零容量时返回 `executor='main'` 和 `level=null`。零容量或宿主无派工能力时，由主 agent 执行同一流程并说明实际执行者。检索与维护共享容量，检索无需维护 owner/control。短任务仍可检索。

一次实际委托由同一 worker 先运行 `memory retrieval-start --request <request.json>`，固定行为筛选之前的基础锚点、逻辑 ID 份额、基础质量、逐版本观察截点、query/episode、预算与策略，再取得行为候选。后续补充 search → 必要原文与图关系回读 → 一次 0–100 综合评分 → UTF-8 `scored.json` → rank；内部多轮复用同一锚点包。访问区间、行为支持度及模型截点是辅助线索，相关性、适用条件和证据价值为主；低权重关键材料仍可进入，mandatory 独立交付。rank 只按综合分排序、去重和预算选择，不二次调权或记账。保存或 rank 失败时保留原错、已读证据和未完成阶段。

候选、read/knowledge、scored、rank 与最终清单一路保留实际观察的 `id`／`knowledge_revision` 及已有 `private` 标记，原证的 `source_version`／`revision`、范围或图片 locator 另记。`record_type:'node'|'semantic'` 的独立知识节点／语义关系可无路径和行号，保留实际 basis、endpoint_versions；不能伪造来源来套成员格式。关系与条件用于判断本次适用性，区分用户要求、助手假设、代码事实和实验观察；旧要求热度不使其恢复现行身份，仍有效的旧实验可继续影响当前回答。完整评分形状与宿主步骤见 [随包 skill](../src/basepack/memory/SKILL.md#retrieve-in-one-delegation)。

worker 把实际观察的候选版本保存为 `candidates.json` 数组（含基础、行为、补检索和选中项），保留当时返回的 `access_model`、`access_compiled_j`、`access_fact_j` 和 `access_interval`。同版本有不同模型／游标观察时分别保留；不事后查新版覆盖。保存 rank 输出后生成固定 context 的交付回执：

```powershell
memory rank --input '<scored.json>' --budget 6000 --output '<ranked.json>'
memory retrieval-receipt --request '<request.json>' --ranked '<ranked.json>' --candidates '<candidates.json>' --output '<delivery_receipt路径>'
# 宿主确认已实际收到最终内容后，登记该回执。
memory delivery --input '<delivery_receipt路径>'
```

context 必须保留锚点及其 `alpha`／`base_quality`、逐版本 `knowledge_cutoff`、query、episode、实际 candidates、budget、policy 与 model；观察时间不是全库不可变快照。程序把各次实际访问提示存入 `access_observations`，`context.model` 表示行为候选发现时的模型；并发切换后补检索可以带不同模型／游标。每个首次接受的 delivery（含空清单）推进事实 J，只有非空交付推进机会钟 C 并刷新实见精确版本；同 ID 同内容重试均不推进，改内容报错。search/read/rank、内部日志及错误不算交付，奖励不传播到父级、依据、邻居或新版；无真实非空交付时闲置不变。最终部分材料只有在实际收到后才据实减少 items，保留固定 context。程序不要求使用者逐条调权。

需要继续核实时使用以下接口；`--knowledge-revision` 省略时读当前知识，指定时读已保留版本，`history` 如实列可用历史。原证的版本与位置独立指定，图片实际打开 `original.image_path`；存量未保存的前像或来源定位保留缺口。

```powershell
memory knowledge '<id>' --knowledge-revision '<实见版本>'
memory history '<id>'
memory neighbors '<id>' --knowledge-revision '<实见版本>'
memory read '<basis.member>' --knowledge-revision '<该成员实见版本>' --source-version '<basis.source_version>' --start-line <basis.start_line> --end-line <basis.end_line>
memory access-hints --input '<items.json>'
```

neighbors 的 `unpinned_children`／`unpinned_edges` 是存量端点版本未知的线索，按 basis 回源核实并保留缺口，不能当作精确历史链接。access-hints 输入为 `[{"id":"<id>","knowledge_revision":"<实见版本>"}]`。Python 对应 `Memory.knowledge/history/read/neighbors/access_hints/record_delivery`；复用返回的 canonical ID 和版本值，不在交付时回查当前记录补旧版身份。成员 ID 是程序分配的 UUID；直接使用返回的完整身份。

```powershell
memory search --text '主题'
memory search --text 'A-17' --mode hybrid --literal
memory search --text 'memory-example.md' --mode hybrid --literal
```

底层 search 默认按项目 `memory.search_mode`，可显式覆盖 `--mode vector|hybrid`；编号、文件名和完整短语用 `hybrid --literal`，直接子串命中带 lexical_rank，仍须核实语义补充；`vector --literal` 明确失败。CLI search 与 Python `Memory.vector_search/hybrid_search` 均返回 `{matches, vector_coverage}`，兼容索引缺失与无命中分别可见，模型错误原样保留。旧 text 配置升级见 [版本升级](setup-project.md#版本升级)。

brief、search、knowledge 和 read 只读已发布知识及所存依据；来源已登记不等于知识已更新。`changes --scope` 显式发现原件变化，维护负责后续接受；查询不会等待维护或默认审计。预算外材料保留补读入口，实际问题用 [反馈](#使用反馈与手动审计) 留待单一维护 owner 处理。

## 行为模型与访问提示

行为模型只从真实共同交付的稳定逻辑 ID 篮子学习标准 KL-NMF，不读取正文、query、排名或访问分数，不建立用途类别。普通修订和移动保留逻辑 ID；拆分、合并或职责断裂由知识维护建立新 ID。没有可靠共用伙伴或模型时保持 unknown，基础检索继续可用。精确版本仍决定命中、回源与适用性，stale/retired 不因行为邻域恢复现行身份。

训练需要可选 `behavior` extra；仅检索的轻量客户端可不安装训练依赖。依赖实现版本由 [包元数据](../pyproject.toml) 与锁文件固定，当前 scikit-learn 为 1.9.1：

```powershell
memory behavior-train --rank 8 --epsilon 0.001 --beta 0.2 --strength 8
memory behavior-compile
```

这些是本次工程初值，不是效果最优参数；训练参数随模型冻结。训练用频率忠实的 `n_b/d_b` 共交付矩阵，模型文件在 `memory.data_dir/behavior/<sha>.json`。重训在新坐标中全史重放原始事实后切换，不能直接换算旧权重。`behavior-compile` 是显式增量追账，brief/search/read/access-hints 均保持只读。

Gaussian 对各独立锚点逐项计算核后按原份额平均；unknown 份额不重归一，产生访问区间。程序增量维护稀疏 H、未知质量 R 和每精确版本标量基准，首次接受固定事实头而不增加 hits；迁移中无法证明的旧接受时间保留未知，并显式标记新规则的观察起点。一次命中刷新整份精确版本的访问状态，无日历衰减。长期不用可降至很低权重，仍保留正文、版本、图、索引与训练 ID，并可由基础检索找回、再实际交付刷新；低权重不触发删除、退出或 GC。

## 私有资料与分享边界

`private` 表示按项目约定限制分发，涵盖隐私、机密及版权/许可受限资料；公开可获取的论文原文也可归入，不要求含个人隐私。它不记录具体限制理由，也不自动判断再分发许可；公开书目、链接和自主分析沿项目公开口径处理。

程序为新写的 source、source_version、member、node 和 semantic 关系计算布尔字段 `private`。根 `private/` 始终私有；已有原文需要保留原位时，在项目 `[memory]` 下声明额外私有文件／目录：

```toml
private_scope = ['研究/客户资料', '业务说明.md']
```

默认 `private_scope=[]`，`['.']` 表示全项目私有。路径按规范化项目相对路径与文件／目录边界匹配，不使用 glob；`研究/客户` 不匹配 `研究/客户甲`。分类不扩大 discovery，原件仍须位于既有发现范围或 source_scope 中。Git 忽略、来源发现与私有分类各自生效。

freeze 固定私有规则及其 revision，apply 核对当前规则；冻结后规则变化明确冲突。正文未变而分类改变也形成可区分的来源版本，旧快照及其分类保持可回读。成员结合自身来源版本和固定 basis，节点依 basis，关系同时依 basis 与固定版本端点；任一私有依据使整条知识为 true，公私混合亦然。编码身份及实际输入未变的向量继续复用，分类改变不要求全库重编码。

检索、brief、回读及交接保留所见版本的 `private`；scored、rank 和最终清单继续携带。`read.original.private` 表示所读来源快照，可与带跨来源私有依据的 member.private 不同。旧记录缺标表示未确认，不能视为已核公开。标记不提供 ACL、全文隐私或版权分类，也不净化内容；公开写入按项目公开口径提炼可公开结论，受限原件和受限的人工分析、摘录留在项目已声明的私有边界内。受管记忆和工作包仍在既有受忽略的 `.basepack/`、`tmp/` 等位置，作为本机私有运行材料保管。

旧记录补标或原位来源迁移另按已确认映射和固定版本依据限定范围，保留原件、历史路径和恢复材料；不以当前规则悄悄覆写历史分类。未覆盖或无法确认的旧记录保留缺口。配置分类不代替全文隐私判断，升级不默认补标、迁移来源或进行全库语义审计。升级边界见 [配置维护](project-config-maintenance.md#按变化边界准备恢复集合)。

现有原生导出和普通备份保留全部公私内容；数据库导出本身不包含全部外部文件。需要公开时另建筛选后的分享副本，公开导出工具尚未提供。除当前知识外，来源快照、图片 assets、旧知识版本、change.previous、聊天/反馈/交付 context 和行为模型也可能受限；数字、逻辑 ID 或坐标本身不构成公开许可。

## 备份与恢复

Windows 用户任务使用受管导出。客户端读取原密码文件，并在整个导出期间保留该次运行实例。动态端口随实例变化，项目配置继续保留 `:0`。

```powershell
& $python -I -m basepack --config $config runtime export memory '<backup.surql>'
```

Windows 恢复时，另建独立的恢复配置、任务和空 store，保留原 `memory.project_id`，恢复原密码文件。原任务若使用同一 UUID，先按原配置收尾、停止并注销；恢复任务使用独立目录和自己的实际地址。注册时使用 `--create-store`，启动后先导入，再运行 `memory init` 验证身份并生成入口。

```powershell
& $restorePython -I -m basepack --config $restoreConfig runtime import memory '<backup.surql>'
```

导入要求注册动态端口或空闲停机的空库。失败时保留退出信息和部分目标，用新的空目标重新恢复。随后核实原文、快照、图关系和检索。固定端口常驻或手动服务可继续按以下原生流程恢复。原生 SurrealDB CLI 使用自己的 SURREAL_USER/PASS，本例仅为这次调用临时设置：

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

恢复集合包括 export、配置、原凭据、公私业务原件、private 独立 Git 及其忽略但仍需保留的附件、受管 Codex 导出、codex-attachments 原件与定位回执，以及 `memory.data_dir` 下的 assets 图片快照和数据库引用的 `behavior/<sha>.json` 模型文件。知识版本、关系、依据、private、更正、旧快照、来源处置（含unavailable_gaps）、反馈、原始交付事实、访问投影及 delivery_id 去重随 export 恢复；旧备份不能补齐后来状态或缺失历史。新目录保留 project_id，使用独立目录/端口，再验证原文、精确版本、关系、检索、反馈、模型 hash 和交付重试。兼容向量随 export 恢复，或从接受表示与原图重新 embed；访问记账不要求重建向量。运行库使用原生 export；复制物理目录先停写、停止服务。长期备份按明确恢复需求决定目的地与保留周期，不默认叠加完整备份；完整恢复材料按私有边界保管。凭据不随源码发行；清理前核原件／旧依据引用及活跃控制／未明发布。
