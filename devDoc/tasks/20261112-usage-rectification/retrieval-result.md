# 检索与任务入口整改结果

2026-11-12；对应计划 A/B、D/I 的检索接线及 G 的相关输入边界。本文记录本分支实现与检查；真实宿主派工、交付记账、业务质量和普通安装验收由主任务整合，不能据模板或排名文件认定已完成。

## 已实现

- 新增统一 `memory retrieve --question '<业务问题>'`：默认全项目、6000 字符，自动生成 UTF-8 request、稳定 delivery_id、工作目录和回执位置。`--request` 复用同一次请求；没有问题时返回所需输入。返回 `prepared`、`started=false`，宿主实际派工并接收 final；零席位返回主 agent 执行，未把渲染称作执行。
- scope 使用共享 `memory/query.py` 的项目相对路径前缀合同，空表示全项目，支持中文与空格，反斜杠归一，绝对／越界路径拒绝。空 scope 渲染时省略 `--scope`、使用 CLI 默认值，避免 Windows PowerShell 原生调用丢弃空参数；prompt 单独显示实际过滤条件。业务限制放 question。
- 模板将每 shell 参数／UTF-8 初始化与每任务一次 brief 分开；同任务读写、反馈、stop/release 复用 brief。brief 无搜索实现由历史／访问分支提供，本分支同步模板、帮助及产品文档。
- 同一检索委托完成多轮搜索、原文与演变依据阅读、0–100 综合评分、实际 UTF-8 保存和 rank；明确宿主文件工具／本机 Python 写入，保存或 rank 失败保留原错与未完成阶段。access_weight 只进入同一次综合评分，rank 不再调权。
- rank 强制实际观察的 knowledge_revision。成员另保留原证版本／范围；图候选明确 `record_type: node|semantic`、原生 kind 和版本，不伪造路径／行号。图按类型／ID／知识版本去重，与成员共用文本预算；成员保留互补范围及不同知识版本。
- CLI 接通 `knowledge`、`history`、read/neighbors 的 `--knowledge-revision`、`access-hints` 与 `delivery --input`。宿主确认最终收到的清单后才交回执；rank/search/read 不记交付。记录实际观察版本，不在交付时回查新版补身份。空清单和幂等由访问分支内核负责。
- 版本展开集成检查发现当前邻居应与已归档邻居共同按端点版本筛选，已交历史分支修复。存量无精确端点的 unpinned 线索保留未知，prompt 要求回源核实。JSON request/rank 误传目录给出明确文件合同错误；prepare 的 BP-T22 既有回归由主任务核实。

## 实际检查

使用 `tmp/basepack-dev/Scripts/python.exe` 的源码开发环境：

- `test_memory_selection.py`、`test_memory_prompts.py`、`test_memory_cli.py`：146 passed。覆盖默认／空输入／稳定请求复用、零席位、真正 PowerShell 原生参数传递（空 scope、中文带空格前缀）、路径边界、知识版本不混用、pathless 图去重／预算、单次综合分及明确目录错误。
- 最后新增的任务一次 brief 断言和 `test_project_entry.py`：18 passed。新 shell 初始化块不含 brief；原业务文字保留、托管块更新及既有入口检查通过。
- 文档分支核对 42 个相对链接，模板入口回归 17 passed（包含上述入口集合）；相关 `git diff --check` 通过。

测试未操作生产数据库、运行维护或执行 Git 提交。新 API 的数据库功能由历史／访问分支测试；本分支用精确参数转发回归验证 CLI 接线。

## 集成与余项

改动位于 `src/basepack/memory/{cli,prompts,query,selection}.py`、`prompts/retrieval.md`、随包 memory skill、项目入口模板、相关测试和 `docs/{memory,setup-project}.md`。agents-snippet 本身只插入 enabled 内容，无需复制新流程。

主任务仍需实际完成中文／空格路径的全项目与限域检索、同委托原文／评分／rank、宿主 final 清单确认与访问回执、真实业务对照和普通安装验收。render_command 使用配置的 runtime.python；开发环境生成命令时须保证该配置也指向待验新客户端，不能渲染到旧安装后据此验收。未新增独立当前理解层或默认语义审计。
