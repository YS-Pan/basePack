# Codex 用量统计启动器整改进度

2026-11-15。**调查与计划已形成，整改未实施。** 用户已澄清主要针对原 `.cmd`，通用 GUI/report 目录规则保留。需求、证据、执行步骤与验收统一见 [plan.md](plan.md)。

## 本次使用反馈与核查

- 观察版本：本地源码 main `edda407`；系统 Python 3.13 的 `codex-usage-plot` 0.2.0。源码／安装副本的 paths、gui、__main__、charts、query、query_cli、environment 七模块 SHA256 一致。
- 复现条件：用户在 `D:/project/trifles/20260829 codex usage` 双击 `启动用量统计.cmd`。用户观察到 GUI 正常出现而 cmd 留着，报告写入 AgentTools。主任务未再次打开 GUI 或统计；已通过启动器、Tk 主循环及本机保存配置确认两项行为的实现依据。
- 原因：迁移后同步调用 GUI；报告路径保存为 `D:/AgentTools/state/codex-usage/reports`。旧备份明确使用 pythonw／Popen 分离启动，GUI 报告位于原项目 `codex_usage_report/`。
- 推荐处置：仅在原启动器内覆盖报告环境变量并分离启动，同步使用说明和定点回归；不迁回设置／缓存、不重装包。状态为待实施、待实际 Windows 验收。

本轮只读外部项目与安装副本，未改其源码、配置、媒体、缓存、系统安装或远端。外部 `git status` 返回 `fatal: this operation must be run in a work tree`，因此未确认工作树状态；本地远程跟踪引用也不作为当前远端事实。

实现核查者复核计划，未发现须扩大范围的问题；已从无关 TEMP 目录实际执行系统安装包的 `gui --help`，退出 0，在创建 Tk 窗口前结束。现有 `worker_python()` 会为统计子进程选择 pythonw 同目录的 console Python，子进程已有 `CREATE_NO_WINDOW`。这支持轻量预检及启动方案，不代替待实施的真实窗口验收。

## 记忆与组织

主任务完成一次 memory brief，保留 mandatory；历史检索和当前实现核查分别委托，主任务整合计划。自动维护尝试返回 `acquired=false`，已有持有者 `codex-01a1da5e-runtime-implementation`；本轮未取得维护所有权，未派维护协调者，也未停止或释放他人任务。

历史检索实际完成搜索、回源、评分与 rank，5 项／3081 字符全部接收，并已按 `retrieval-872a80859f6b4aaba9781e323ab6bfc5` 确认 delivery。主迁移及实施对话各读到可见最新 10 turns、`hasMore=false`；后续 GitHub 同步对话读最新 10 turns、`hasMore=true`，未继续读更早页。三个分线程 freshness 均因 Codex App Server 无法打开 `state_5.sqlite`（SQLite code 14）失败；直接读对话及迁移原证补足本次依据，不声称新鲜度检查通过或已覆盖更晚发布。

原对话定位：主迁移 `01a1d2db-9ca7-7891-b59e-c948688b69ab`（追加用量工具、独立安装和保留原 project）；实施 `01a1d2ea-8f4f-7e92-b715-d731120f36e4`；后续同步 `01a1d7dc-69f2-7791-b709-a04cf43aa63e`。补读范围为迁移 plan/progress/result、用量启动器与 environment 备份、usage-result／usage-machine-result、路径收据及 11 月 14 日收尾计划的相关段落。未扩查其他工具推理或全库业务资料。

本轮文档按 UTF-8 读取，新增／改动的本地链接与锚点检查通过，相关 Git 差异无空白错误；未运行产品测试或真实统计。分支为一名历史检索者、一名实现核查者，后者定点复核计划；模型按本项目日常／检索配置派发，用量与费用未知。

## 下一步

按 [计划](plan.md#实施顺序)在用量统计原项目执行，核工作树后修改启动器和相关说明，完成分离启动、路径隔离及合成更新检查，再补实际结果。当前不属于已修复或已发布状态。
