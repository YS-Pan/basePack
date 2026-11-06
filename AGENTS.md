# Agent 工作约定

## 项目与入口

- 本项目重建 basePack：项目局部记忆、计算资源协调、分层 agent 协作。先完成可用的记忆闭环，再逐步扩展。
- 用户的新指令优先；项目战略以项目纲领为准。执行计划中的接口、目录和数字预算是工程建议。
- 涉及目标与取舍时读 [项目纲领](devDoc/project-charter.md)；纲领仅记录用户明确表达的意图，修改正文前须获得用户同意。[原始快照](devDoc/work/20261106-rebuild/research/user-plan.original.md) 保留原文。
- 了解现行实现时读 [实现概览](devDoc/current/overview.md)；继续重建时读 [工作进度](devDoc/work/20261106-rebuild/progress.md)。
- 确定建设顺序时读 [简短计划](devDoc/work/20261106-rebuild/plan.md)；执行任务时按需读 [AI 执行计划](devDoc/work/20261106-rebuild/agent-plan.md) 的对应步骤。
- 核实旧项目或共享设施时按主题读 [调研依据](devDoc/work/20261106-rebuild/research/sources.md) 和 [近期历史](devDoc/work/20261106-rebuild/legacy-history.md)，按需深入原证。
- 目标仓库为 [YS-Pan/basePack](https://github.com/YS-Pan/basePack)；发布前按产品状态编写面向使用者的 README 和使用文档。
- 新建、调整或归档开发文档时读 [文档维护约定](devDoc/documentation.md)。

## 实施

- 保持实现、文档和 prompt 简短。先跑通最短实际流程，再优化；错误直接报告，不用静默回退或多层审阅掩盖问题。
- 编写或修改供 agent 阅读的文档、prompt、skills 和 AGENTS.md 时，默认使用 `writing-for-agents`；当前上下文已有且有效的规则直接复用。
- 理解、建图和评分通过宿主可用的订阅 agent 完成，不假设已有 LLM API。小任务直接完成，团队规模随实际需要调整。
- 项目知识、来源、状态与数据库保留在对应项目。通用依赖和模型优先复用已有机器设施；公共代码通过配置定位共享资源，不写死本机路径。
- 旧项目仅作参考，不自动继承其数据库、任务状态、业务授权和验收结论。
- 搜索优先用 `rg`，只读当前任务需要的材料。新增机制应对应具体需求或已出现的问题。

## 验证与 Git

- 按改动运行必要检查；修复真实缺陷时保留对应回归。文档与 Git 配置改动只做相关检查，不搭建测试框架。
- 完成时简要说明结果、实际检查和余项；工具返回成功、扫描量或节点数不能代替功能验收。
- 每完成一项完整修改并通过相应检查，及时在 `main` 上 commit；相关代码、文档和 `change_log` 一同提交。特别小的修改可省略 `change_log`。
- 由主 agent 统一检查差异并提交，仅纳入本次相关内容，保留用户已有改动。使用清晰的提交说明。
- Git 保存源码、skills、短文档和小样例；模型、虚拟环境、项目数据库、缓存、密钥及大型运行产物留在仓库外或忽略目录中。
