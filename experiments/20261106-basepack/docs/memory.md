# 项目记忆

记忆在本项目的 SurrealDB 中保存文件摘要、章节摘要、原文块、图片描述与定位，并保留层级、原文范围、语义关系和修改依据；图片原字节快照保存在项目记忆目录的 assets 中。宿主订阅 agent 负责智能分块、摘要、识图、建图和评分；已有共享服务编码图文，数据库执行存储、事务与混合查询。小文件不必虚造章节。

## 启用

按 [项目接入](setup-project.md#启用记忆) 先选独立目录、endpoint 和 UUID，再按 [项目 SurrealDB](administrator.md#项目-surrealdb) 启动并在独立调用核 ready/init/brief。同项目多聊天复用服务，另一个项目使用自己的物理目录、端口及 UUID；通用 exe 和模型可共用。服务在查询期间保持运行。前台排错可在普通用户终端直接执行同一个 serve.ps1，其 cwd 与 endpoint 仍来自目标配置。

普通 init 只生成配置和入口；memory init 才安装 schema 并绑定 UUID、增加记忆启动指令。误连其它 UUID 的库会失败。每个调用进程加载 password_env 指定的凭据，使用项目 instructions 中的 Python 与显式配置。已有旧配置启用记忆时补齐当前 memory 字段；只用资源工具无需记忆数据库。

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
memory embed
memory changes --scope '资料目录'
```

prepare 时包括本批所用依据与关系两端的材料；它提供新旧编号原文、已有与关联成员、节点、关系及 expected 知识版本，图片返回可打开的原图路径。关联记录的来源原文仍需 read 或扩充 prepare 范围核实。将材料交给订阅 agent，在同次阅读中选择最终块边界并生成摘要、节点和图边；结构备读单元只用于定位。批次 JSON 合同与操作流程在 `memory guide` 返回的已安装 skill 中，源码维护源为 [SKILL.md](../src/basepack/memory/SKILL.md)。

apply 核对来源版本，以及本批改写、退休、更正目标、实际使用的既有依据成员和关系两端的 expected 版本，再原子写入；无关 expected 不阻塞并行，缺 expected 仅允许本批新建记录。原文块由程序按范围取原词，摘要、边界、依据、历史与更正持久保存。旧草稿冲突时重新 prepare、共读后再提交。来源变化使相关块、祖先摘要及依赖关系待更新，失效也刷新知识版本；未变兄弟与兼容向量可复用，文件追加的新内容必须重核完整摘要。部分摘要显式保存 coverage_gaps。接受删除保留旧依据，相关主张按剩余证据重核。再次共读、apply、embed 并查询新结果后，才算完成增量维护；深检查使用 `changes --scope <文件或目录> --deep`。

embed 复用 [共享 embedding](resources.md)，不另外加载模型。文件/章节使用已接受摘要，块使用原文，图片使用原始图片；兼容且输入未变的向量复用。超限保留原错误，交回原阅读 agent 调整分块或摘要，不能静默截断。仅文字试用可暂不编码，并显式使用 search 的 text 模式。

图片先由视觉 agent 实际打开，描述与 OCR 单独标明，程序按 hash 保留必要原字节快照。必要 PDF 页可由宿主读取/渲染为项目内图片，locator 记录原文件、版本、页与区域；原 PDF 变化时重新核相关页面，不声称自动解析所有 PDF。

## 最小闭环示例

在已完成 init/brief、凭据已加载的干净试用项目执行 [memory_minimal.py](../examples/memory_minimal.py)。它新建四行 UTF-8 的 `memory-example.md`，拒绝覆盖同名文件，并依次 prepare → 生成完整批次 → apply → search/read/neighbors；每个子命令使用 `subprocess.run(check=True)`，apply 失败后即停止。默认文字查询独立于模型服务；首次运行加 `--with-vectors` 则在 apply 后先 embed，再做默认混合查询。

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

随包 [skill](../src/basepack/memory/SKILL.md#minimal-text-batch) 也保留不依赖仓库文件的完整批次例子。文字成员缺起止行字段会报告批次位置、成员 ID 与字段；不存在的 read 目标会明确报出 ID。修正输入后重新运行，失败批次没有部分写入；保留原错误，不继续下游命令。

## 启动与检索

```powershell
memory brief --task '当前任务'
memory search --text '主题'
memory search --text 'A-17' --mode text --literal
memory neighbors 'member:<id>'
memory read 'member:<id>'
```

brief 直接提供必须保留的信息、相关线索、来源与覆盖缺口。mandatory 不参加相关性筛选；其中 stale 条目是待核义务，不能当当前事实。search 默认融合跨层全文与向量，`--mode text` / `--mode vector` 可单独查询。当前范围有知识却没有兼容索引时，明确提示先 embed 或选择 text；模型失败保留原错。中文全文按词典分词，短词不保证子串召回，编号命中也不等于精确匹配；literal 是显式包含查询。

启动快检默认只覆盖已登记原件；在 `[memory]` 配置 `source_scope = ['资料目录', 'README.md']` 后，也检查这些显式范围中的新增文件。brief 报告 changes/pending 时，由当前宿主 agent 在任务预算内维护相关小批，也可与检索合并委托；程序不另起后台 agent。未改原件只查元数据，深查才做完整 hash。任务词未命中时，短项目地图仍提供前提线索。

brief 的状态明细有上限并返回总数，必保留信息不因此省略；vector_pending 报告尚未编码或输入已变的当前成员，模型身份兼容性在实际向量查询时核对。`memory sources` 列完整来源元数据，供手动深维护抽样；抽到的材料与旧图要实际共读，未发现新关系也如实记录。已待核知识不会每次启动重复写相同失效日志。启动由项目指令驱动宿主实际运行 brief，维护由宿主派发订阅 agent，程序没有后台语义工作进程。

read 只接受 member ID；语义 node/edge 经 neighbors 查看依据，再读对应成员。neighbors 默认展开当前关系，历史复核显式加 `--include-stale`。图像 read 将描述与 `original.image_path` 分开；实际打开快照，并报告 original_missing。业务原图缺失时仍可读保留快照；原图已变化或快照缺失时直接报错。

当前 ID 合同支持字符串与整数 key。无表名前缀时是原始字符串 key；带 `member:`、`node:` 等前缀时是数据库 canonical ID，可直接沿用返回值。字符串 key `123` 与 canonical `member:123` 的数字 key 不同；字符串形式为 ``member:`123` ``。含冒号的 key 使用完整 canonical ID。

任务已知少量文件时，启动 brief 后可以直接批量读取；需要发现位置、未点名前提或跨材料依据时，再用记忆检索。父级摘要用于补背景或条件，选证据时避免重复已选原文块。

工作 agent 可只委托一次，让 worker 完成检索、父子/语义展开、原文核实和评分，再用 `rank --input <scored.json> --budget <文字字符数>` 排序交付实际内容。词法分数与 agent 分数不同。超预算证据保留补读入口，不静默截掉条件；工作 agent 仍可自由补读。

## 备份与恢复

使用原生 export 写文件：

```powershell
& $surreal export --endpoint '<endpoint>' --username '<username>' --namespace '<namespace>' --database '<database>' '<backup.surql>'
if ($LASTEXITCODE -ne 0) { throw "Surreal export failed ($LASTEXITCODE)" }
& $surreal import --endpoint '<新目录服务的 endpoint>' --username '<username>' --namespace '<namespace>' --database '<database>' '<backup.surql>'
if ($LASTEXITCODE -ne 0) { throw "Surreal import failed ($LASTEXITCODE)" }
```

原生 CLI 使用 SURREAL_PASS 等环境变量；basepack 使用配置中的 password_env。备份集合包括 export、项目配置、业务原件及 `memory.data_dir` 下的 assets 图片快照（默认 `.basepack/memory/assets/`）；数据库内的摘要、边界、依据、更正和旧文字快照随 export 恢复。新目录保留 project_id，使用自己的数据目录与端口，再核原文定位、图关系和检索。向量可随 export 恢复，也可从保留表示和原图重新 embed，无需重新总结；重编码仍要求业务原件存在且版本一致。运行中的库使用原生 export；复制物理目录须先停写并停止服务。长期备份目的地与保留周期由业务项目确定。
