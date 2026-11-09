# 项目记忆

记忆将文件摘要、章节摘要、原文块和图片保存在本项目的 SurrealDB 中，并保留层级、原文范围、语义关系和修改依据。宿主订阅 agent 负责智能分块、摘要、识图、建图和评分；已有共享服务编码图文，数据库执行存储、事务与混合查询。小文件不必虚造章节。

## 启用

先按 [项目接入](setup-project.md) 初始化项目，安装官方 SurrealDB 4。管理员可按 [部署说明](administrator.md#项目-surrealdb) 托管项目数据库；临时前台运行使用发行 exe 的原生命令：

```powershell
$surreal = '<已安装的 SurrealDB exe>'
$env:BASEPACK_MEMORY_PASSWORD = '<本地数据库密码>'
$env:SURREAL_USER = 'root'
$env:SURREAL_PASS = $env:BASEPACK_MEMORY_PASSWORD
& $surreal start --bind 127.0.0.1:18080 'surrealkv://.basepack/memory/store'
```

同项目的多个聊天复用这个服务。另一个项目使用不同物理目录和端口；通用 exe 可以共用。服务需要在查询期间运行，停止一个聊天不应停止其他聊天正在使用的服务。

核对 `.basepack/config.toml` 的 `[memory]`：endpoint、namespace、database、username 和 password_env；project_id 由 init 生成，随项目移动和备份保留。每个调用进程提供 password_env 指定的凭据。使用项目 instructions 中的 Python 与配置：

```powershell
python -m basepack --config '<项目>/.basepack/config.toml' memory init
```

成功后，项目 `.basepack/instructions.md` 会增加记忆启动入口，保留原有业务说明。误连其它 project_id 的库会报错。已有旧配置要启用记忆时，显式补齐上述字段；仅使用资源工具无需配置记忆数据库。

## 首建与维护

将本轮输出写到项目 `.basepack/memory/`，并为并发批次选择不同文件名：

```powershell
python -m basepack --config '<config>' memory prepare --paths '说明.md' '决定.md' --output '<reading.json>'
python -m basepack --config '<config>' memory apply --batch '<agent-batch.json>'
python -m basepack --config '<config>' memory embed
python -m basepack --config '<config>' memory changes --scope '资料目录'
```

prepare 提供新旧编号原文、已有成员、相关关系及 expected 知识版本；图片返回可打开的原图路径。将材料交给订阅 agent，在同次阅读中选择最终块边界并生成摘要、节点和图边；结构备读单元只用于定位。批次 JSON 合同与操作流程在 `memory guide` 返回的已安装 skill 中，源码维护源为 [SKILL.md](../src/basepack/memory/SKILL.md)。

apply 核对来源版本和本批被修改知识的 expected 版本，再原子写入；缺 expected 仅允许新建。原文块由程序按范围取原词，摘要、边界、依据、历史与更正持久保存。旧草稿冲突时重新 prepare、共读后再提交。来源变化使相关块、祖先摘要及依赖关系待更新，未变兄弟与兼容向量可复用；文件追加的新内容也必须重核完整摘要。部分摘要显式保存 coverage_gaps。接受删除保留旧依据，相关主张按剩余证据重核。再次共读、apply、embed 并查询新结果后，才算完成增量维护；深检查使用 `changes --deep`。

embed 复用 [共享 embedding](resources.md)，不另外加载模型。文件/章节使用已接受摘要，块使用原文，图片使用原始图片；兼容且输入未变的向量复用。超限保留原错误，交回原阅读 agent 调整分块或摘要，不能静默截断。仅文字试用可暂不编码，并显式使用 search 的 text 模式。

图片先由视觉 agent 实际打开，描述与 OCR 单独标明，程序按 hash 保留必要原字节快照。必要 PDF 页可由宿主读取/渲染为项目内图片，locator 记录原文件、版本、页与区域；原 PDF 变化时重新核相关页面，不声称自动解析所有 PDF。

## 启动与检索

```powershell
python -m basepack --config '<config>' memory brief --task '当前任务'
python -m basepack --config '<config>' memory search --text '主题'
python -m basepack --config '<config>' memory search --text 'A-17' --mode text --literal
python -m basepack --config '<config>' memory neighbors 'member:<id>'
python -m basepack --config '<config>' memory read 'member:<id>'
```

brief 直接提供必须保留的信息、相关线索、来源与覆盖缺口。mandatory 不参加相关性筛选；其中 stale 条目是待核义务，不能当当前事实。search 默认融合跨层全文与向量，`--mode text` / `--mode vector` 可单独查询。当前范围有知识却没有兼容索引时，明确提示先 embed 或选择 text；模型失败保留原错。中文全文按词典分词，短词不保证子串召回，编号命中也不等于精确匹配；literal 是显式包含查询。

启动快检默认只覆盖已登记原件；在 `[memory]` 配置 `source_scope = ['资料目录', 'README.md']` 后，也检查这些显式范围中的新增文件。brief 报告 changes/pending 时，由当前宿主 agent 在任务预算内维护相关小批，也可与检索合并委托；程序不另起后台 agent。未改原件只查元数据，深查才做完整 hash。任务词未命中时，短项目地图仍提供前提线索。

brief 的状态明细有上限并返回总数，必保留信息不因此省略；vector_pending 报告尚未编码或输入已变的当前成员，模型身份兼容性在实际向量查询时核对。`memory sources` 列完整来源元数据，供手动深维护抽样；抽到的材料与旧图要实际共读，未发现新关系也如实记录。已待核知识不会每次启动重复写相同失效日志。启动由项目指令驱动宿主实际运行 brief，维护由宿主派发订阅 agent，程序没有后台语义工作进程。

read 只接受 member ID；语义 node/edge 经 neighbors 查看依据，再读对应成员。neighbors 默认展开当前关系，历史复核显式加 `--include-stale`。图像 read 将描述与 `original.image_path` 分开；实际打开快照，并报告 original_missing。

任务已知少量文件时，启动 brief 后可以直接批量读取；需要发现位置、未点名前提或跨材料依据时，再用记忆检索。父级摘要用于补背景或条件，选证据时避免重复已选原文块。

工作 agent 可只委托一次，让 worker 完成检索、父子/语义展开、原文核实和评分，再用 `rank --input <scored.json> --budget <文字字符数>` 排序交付实际内容。词法分数与 agent 分数不同。超预算证据保留补读入口，不静默截掉条件；工作 agent 仍可自由补读。

## 备份与恢复

使用原生 export 写文件：

```powershell
& $surreal export --endpoint '<endpoint>' --username '<username>' --namespace '<namespace>' --database '<database>' '<backup.surql>'
& $surreal import --endpoint '<新目录服务的 endpoint>' --username '<username>' --namespace '<namespace>' --database '<database>' '<backup.surql>'
```

原生 CLI 使用 SURREAL_PASS 等环境变量；basepack 使用配置中的 password_env。备份集合包括 export、项目配置、业务原件及 `.basepack/memory/assets/` 必要图片快照；数据库内的摘要、边界、依据、更正和旧文字快照随 export 恢复。新目录保留 project_id，使用自己的数据目录与端口，再核原文定位、图关系和检索。向量可随 export 恢复，也可从保留文字和原图重新 embed，无需重新总结。运行中的库使用原生 export；复制物理目录须先停写并停止服务。长期备份目的地与保留周期由业务项目确定。
