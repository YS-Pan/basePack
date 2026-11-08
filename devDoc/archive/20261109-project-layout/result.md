# 实验路线布局迁移结果

2026-11-09（北京时间）。已按 [计划](plan.md) 完成目录与入口迁移。源码和新 wheel 回归通过，共享部署继续原位使用。

## 已调整

- 当前唯一 active 路线为 [20261106-basepack](../../../experiments/20261106-basepack/README.md)，包含构建声明、源码、测试、产品文档、示例、resources skill 和交付包；包名、公开接口及模块结构保持。
- 根保留统一开发文档和两项通用技能；根 README/AGENTS 导航到实验。现行配置与部署合同归 [system/deployment.md](../../system/deployment.md)，原三个任务继续承担 R9、记忆 P0–P5 和 P7/P8。
- `.agents/skills/resources` 改指实验内维护源；构建与测试入口、忽略规则、相关文档路径和命令一起修正。测试不使用持久缓存，临时环境、构建缓存及 basetemp 统一在根 tmp。
- 选留原证归根 artifacts/runs，各批次内部结构和原文保持；旧 wheel 随路线 dist 保留，新构建另存 dist/layout-20261109，避免覆盖旧包。

## 证据与旧路径

本次映射为 `artifacts/runs/20261109-project-layout/moves.json`，记录 23 项源→目标（含本任务归档）和 990 份原证/旧 wheel 的路径、大小及 SHA-256。迁移前清单为同目录 baseline.json。

历史回执保留当时的绝对路径。先按本次 moves 中最长匹配的 source 前缀换成 destination；此前三个外部验收项目及临时材料，再按 `artifacts/runs/tmp-reorganization-20261108/moves.json` 的 moves/retained_evidence 回查，所得旧 artifacts 前缀再应用本次映射。126 份选留副本随原批次保留，长期复核使用这些副本，tmp 验收实例允许清除。

## 外部边界

正常用户权限下实查进程、服务、计划任务、启动项与环境变量，未发现活动旧源码依赖。系统仍使用原普通 wheel 0.4.0/site-packages；五份机器及 Condor 配置哈希保持，没有切换共享安装、服务、模型或容量。

实际 skills/list 在项目根与实验子目录均发现三项已启用 repo 技能，resources 返回新维护源；项目外未发现三项，发现错误为空。受限 CIM 和 Codex 状态库权限错误保留在原记录，正常用户权限复核成功。

## 验证与接续

源码和新 wheel 的现有回归各 **92 passed**，无 skip；分别确认从新实验 src 和隔离普通安装的 site-packages 加载。回归使用直接系统解释器并分别显式指定这两个导入根，wheel 回归的工作目录、测试及配套样例位于源码外。

隔离 venv 的 `-I` 源码外烟测通过：模块/console CLI、中文空格项目及深层配置初始化、config show、doctor core、四份模板、许可和轻量命令未加载 torch。初始化生成的 AGENTS 指针实际指向新实例 instructions。

新 wheel 为 `experiments/20261106-basepack/dist/layout-20261109/basepack-0.4.0-py3-none-any.whl`，42998 字节，SHA-256 `8137f04af3b441ba15857d0253c1a2c447cc671d642815b0603c4986179e4575`。包内 30 份源码/模板/许可与实验维护源一致；原四版 wheel 保持哈希。源码、测试和样例共 44 份文件与搬迁前字节一致，实际实现未修改。

两项实际验证条件留痕：本机 pytest 9.2 对含父目录段的 cache_dir 抛越界错误，因此路线配置改为 `-p no:cacheprovider`；Windows venv 重定向器的 Popen.pid 与内层 Python PID 不同，既有所有权测试在 venv 下先出现 91 passed/1 failed，改用原直接 Python 条件后两轮完整通过。保留原失败日志与实际导入身份，未为此修改产品或测试合同。

受影响的文档链接/锚点、UTF-8、围栏、Git 差异与忽略边界已检查；模板中的 `.basepack/instructions.md` 是初始化后生成的实例链接，另由安装烟测验证。一次性构建树和生成的 egg-info 已移至根 tmp；交付包、映射和选留回执独立保留。

完整验收回执为 `artifacts/runs/20261109-project-layout/verification.json`，实际技能发现与外部核验分别为同目录 skills-discovery.json、external-preflight.json，烟测为 wheel-smoke/receipt.json。相关日志、实际生成配置及脚本快照按 selected-evidence.json 的源→长期副本与哈希复核。

本轮按外部核验、代码验证、系统/产品文档和任务文档分工，主 agent 整合；宿主未提供完整上下文、团队 token 或精确总耗时计量，记为 unknown。memsys 技术选型和功能实现继续由后续任务决定；需要替代路线时按本次路线边界短期比较并收敛，保持根目录单套现行开发文档。
