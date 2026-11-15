# Codex 用量统计目录与运行行为整改进度

2026-11-15 修订。**当前为计划阶段，外部项目尚未整理或修改。** 用户新方向及 CLI 三个候选统一见 [plan.md](plan.md)。CLI 推荐 A，等待用户选择；此前“原项目启动器只把报告写回开发目录”的建议已退出。

## 当前已定与待定

已定：原项目作为开发目录；版本化可复制启动器维护源放在 scripts；用户放在 AgentTools 的运行副本按自身位置保存 reports、cache 和 GUI 设置；系统 Python 仍运行安装包；原始 .codex 日志不动。CLI 默认尚未选择，不把推荐当作用户已选，也未改全局路径配置。

本轮实际完成只读目录／Git 跟踪／媒体字节盘点及官方惯例查询，并据此重写计划和接续入口。使用同一实现核查者，主任务负责默认行为比较与整合；沿用 agent-team、file-structure、engineering-judgment、writing-for-agents。模型按项目配置派发；团队用量与费用未知。

## 只读发现与处置范围

- 原源码根存在约 1.42 GB 的旧缓存及 invalid 备份、约 224 MB 的 .task-tmp 和约 207 MB 的真实报告；可再生成缓存／临时物列清理候选，未执行删除。
- 原报告目录有四个 Git 跟踪媒体。HEAD 与 index 一致；工作区两 PNG 与 MP4 较提交版本有变化。规划以 HEAD 原 blob 迁至 docs/assets，当前完整报告另留运行区，不把受保护 PNG 更新或已有 MP4 改动混入提交。
- scripts 当前仅有旧预览脚本 pyc；requirements.txt 仅转接 .[test]，CI 仍在使用；五份现有测试使用 .task-tmp。保留有效依赖／文档／测试分工，避免为改名增加无用迁移。
- 用户复制的 D:/AgentTools/state/codex-usage/启动用量统计.cmd 已实际存在，与原同步启动脚本一致。本轮只读该文件，尚未设置相对脚本根的两个环境变量。
- CLI 惯例按 coverage.py（报告目录）、uv（用户缓存）、pytest（项目缓存）和 PyPA（布局）官方说明比较，来源链接在计划；推荐为设计推论，不把参考项目当作本项目既定要求。

原项目早前 git status 返回 work tree 错误；本轮用 ls-tree、ls-files --stage 及二进制 blob 哈希确认媒体跟踪与变化，仍不声称原工作树整体干净。未 fetch 或判断当前远端发布状态。

## 前轮调查与历史依据

观察版本为本地 main edda407、系统 Python 3.13 安装的 codex-usage-plot 0.2.0。前轮对 paths、gui、__main__、charts、query、query_cli、environment 七模块核得源码与安装副本 SHA256 一致；未把这一观察外推为之后源码修改会自动更新安装。

原反馈的实现根因已核：迁移后 .cmd 同步运行 GUI，报告目录配置为 AgentTools reports；旧启动器经 environment --launch 用 pythonw／Popen 分离启动。实际从无关 TEMP 目录运行系统安装包 gui --help 退出 0，未创建 Tk 窗口。当前方案继续沿用这些实现证据。

前轮历史检索完成搜索、回源、评分与 rank，5 项／3081 字符全部接收并以 retrieval-872a80859f6b4aaba9781e323ab6bfc5 确认 delivery。主迁移对话 01a1d2db-9ca7-7891-b59e-c948688b69ab 及实施对话 01a1d2ea-8f4f-7e92-b715-d731120f36e4 各读最新 10 turns、hasMore=false；后续同步对话 01a1d7dc-69f2-7791-b709-a04cf43aa63e 读最新 10 turns、hasMore=true，未继续读更早页。freshness 的 state_5.sqlite 访问失败保留为未核；已直接读对话和迁移原证补足本次依据。没有扩查其他工具推理或全库业务资料。

原计划提交为 1d63cb3；本轮直接改写现行计划，原文通过 Git 追溯，不维持两个相互竞争的执行入口。

## 自动维护与检查

前轮启动维护时由其他任务持有，返回 acquired=false，未停止或释放他人任务。本轮刷新完整项目注册清单并重新启动，取得自有 run bdb9fb30c5a24c5d88f015ee14416519 后，在 Codex App Server 访问 state_5.sqlite 时失败（SQLite code 14、arg0 目录访问被拒）。未得到语义派工回执、未派维护协调者；已独立 stop，核 publications=[] 后 release 成功。未把此轮维护记为完成。

本轮仅做相关 Markdown 的 UTF-8、本地链接／锚点与 Git 差异检查；未运行产品回归、GUI 更新、真实日志统计或目录清理。执行检查结果随提交记录；实际整改及新版安装验收仍待后续实施。

实现核查者已定点复核新版计划，补清 A／B 对应的具体配置键迁移、demo／CI 默认路径，以及独立 query 不继承 cmd 临时环境的边界。修订后检查通过；本轮只提交五份计划及接续文档。

## 下一步

用户选择 CLI 方案后，按[实施顺序](plan.md#实施顺序与验收)整合开发目录整理、可复制启动器与统一 CLI 默认，再用合成数据和真实 Windows 入口验收。正式记录实际删除／移动清单及未完范围，不能以计划提交代替功能修复。
