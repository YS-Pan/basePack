# 项目记忆

记忆将文件摘要、章节摘要和原文块保存在本项目的 SurrealDB 中，并保留层级、原文范围、语义关系和修改依据。宿主订阅 agent 负责智能分块、摘要、建图和评分；数据库执行存储、事务与查询。小文件不必虚造章节。

## 启用

先按 [项目接入](setup-project.md) 初始化项目。安装官方 SurrealDB，在项目根启动自己的本地服务；以下使用原始发行 exe 的命令，若使用新版 launcher 则按其帮助加 `db` 层级：

```powershell
$surreal = '<已安装的 SurrealDB exe>'
$env:BASEPACK_MEMORY_PASSWORD = '<本地数据库密码>'
& $surreal start --bind 127.0.0.1:18080 --user root --pass $env:BASEPACK_MEMORY_PASSWORD 'surrealkv://.basepack/memory/db'
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
python -m basepack --config '<config>' memory changes --scope '资料目录'
```

prepare 提供新旧编号原文、已有成员及关系。将这些材料交给订阅 agent，在同次阅读中选择最终块边界并生成摘要、节点和图边；结构备读单元不算智能分块。批次 JSON 合同与操作流程在 `memory guide` 返回的已安装 skill 中，源码维护源为 [SKILL.md](../src/basepack/memory/SKILL.md)。

apply 核对来源版本和本批被修改知识的 expected 版本，再原子写入。原文块保持原词；摘要、边界、依据、历史与更正持久保存。旧草稿不能覆盖较新的知识更正。变化检测会使受影响知识待更新；再次共读、apply 并查询新结果后，才算完成增量维护。深检查使用 `changes --deep`。

## 启动与检索

```powershell
python -m basepack --config '<config>' memory brief --task '当前任务'
python -m basepack --config '<config>' memory search --text '主题'
python -m basepack --config '<config>' memory search --text 'A-17' --literal
python -m basepack --config '<config>' memory neighbors 'member:<id>'
python -m basepack --config '<config>' memory read 'member:<id>'
```

brief 直接提供必须保留的信息、相关线索、来源与覆盖缺口。stale 信息只作待核，不当当前事实。中文全文按词典分词，短词不保证子串召回，编号命中也不等于精确匹配；literal 是显式包含查询。

工作 agent 可只委托一次，让 worker 完成检索、父子/语义展开、原文核实和评分，再用 `rank --input <scored.json> --budget <文字字符数>` 排序交付实际内容。词法分数与 agent 分数不同。超预算证据保留补读入口，不静默截掉条件；工作 agent 仍可自由补读。

## 备份与恢复

使用原生 export 写文件：

```powershell
& $surreal export --endpoint '<endpoint>' --username '<username>' --namespace '<namespace>' --database '<database>' '<backup.surql>'
& $surreal import --endpoint '<新目录服务的 endpoint>' --username '<username>' --namespace '<namespace>' --database '<database>' '<backup.surql>'
```

凭据按原生 CLI 的环境变量配置。备份还应包含项目配置、原件和必要派生图片；数据库内显式保存的摘要、边界、依据与历史随 export 恢复。新目录保留 project_id，使用自己的服务端口，再验证原文定位与检索。运行中的数据库不能仅靠复制一个库文件备份。
