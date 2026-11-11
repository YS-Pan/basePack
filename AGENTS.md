# Agent 工作约定

## 项目与入口

- 本项目重建 basePack：项目局部记忆、计算资源协调、分层 agent 协作与文件结构建议。记忆工具先完成可用闭环，独立工具按其工作计划交付。
- 当前唯一 active 路线为 [20261106-basepack](experiments/20261106-basepack/README.md)，源码、依赖、测试和产品文档在实验目录；根 devDoc 统一维护现行说明与任务。安装、构建和测试按路线入口执行。
- 用户的新指令优先；项目战略以项目纲领为准。执行计划中的接口、目录和数字预算是工程建议。
- 涉及目标与取舍时读 [项目纲领](devDoc/project-charter.md)；纲领仅记录用户明确表达的意图，修改正文前须获得用户同意。[原始快照](devDoc/tasks/20261106-rebuild/research/user-plan.original.md) 保留原文。
- 了解系统实现时读 [实现概览](devDoc/system/overview.md)；跨工具建设顺序与公共交付见 [重建总览](devDoc/tasks/20261106-rebuild/plan.md) 和 [总进度](devDoc/tasks/20261106-rebuild/progress.md)。
- 实施记忆系统时读 [计划](devDoc/tasks/20261106-memory-system/plan.md) 与 [进度](devDoc/tasks/20261106-memory-system/progress.md)；修改资源工具时读 [当前实现](devDoc/system/modules/resources.md) 与 [部署合同](devDoc/system/deployment.md)，历史交付见 [R9 结果](devDoc/archive/20261107-resource-coordination/r9-result.md)。
- 核实旧项目或共享设施时按主题读 [调研依据](devDoc/tasks/20261106-rebuild/research/sources.md) 和 [近期历史](devDoc/tasks/20261106-rebuild/legacy-history.md)，按需深入原证。
- 目标仓库为 [YS-Pan/basePack](https://github.com/YS-Pan/basePack)；发布前按产品状态编写面向使用者的 README 和使用文档。
- basePack 仍在开发，实际使用同时作为测试样本。发现使用问题时，在所属任务进度记录现象、版本、必要复现条件与处理状态，修复后补验证；无所属任务的问题先记入 [总进度](devDoc/tasks/20261106-rebuild/progress.md)。外部项目沿使用者已有记录约定，并按 [反馈格式](experiments/20261106-basepack/docs/setup-project.md#问题记录与反馈) 形成 Issue 草稿，由用户提交或明确授权 agent 提交。
- 新建、调整或归档开发文档时读 [文档维护约定](devDoc/documentation.md)。
- 推荐、设计或整理项目文件结构时使用 [file-structure](skills/file-structure/SKILL.md)。
- 每项任务开始或接续时应用 [agent-team](skills/agent-team/SKILL.md) 的组织判断；当前上下文已有有效规则时直接复用。

## 实施

- 保持实现、文档和 prompt 简短。先跑通最短实际流程，再优化。
- 避免防御式编程，采用 `let it crash`：内部按明确契约调用，非预期错误直接抛出并保留原始信息；只捕获有明确处理办法的异常，不用默认值、静默回退、盲目重试或层层校验审阅掩盖失败。
- 设计接口、错误处理、兼容范围或使用流程时，应用 [engineering-judgment](skills/engineering-judgment/SKILL.md) 判断契约、职责、证据与必要负担；效果通过长期真实使用反馈维护。
- 按职责划分模块，接口、规则和状态各有单一维护源。优先复用已有能力、修正根因；抽象、兼容、重试和额外状态只为当前需求或真实故障引入，清理本次改动涉及的失用分支和重复逻辑。
- 编写或修改供 agent 阅读的文档、prompt、skills 和 AGENTS.md 时，默认使用 `writing-for-agents`；当前上下文已有且有效的规则直接复用。
- 理解、建图和评分通过宿主可用的订阅 agent 完成，不假设已有 LLM API。小任务直接完成，团队规模随实际需要调整。
- 项目知识、来源、状态与数据库保留在对应项目。通用依赖和模型优先复用已有机器设施；公共代码通过配置定位共享资源，不写死本机路径。
- 旧项目仅作参考，不自动继承其数据库、任务状态、业务授权和验收结论。
- 搜索优先用 `rg`，只读当前任务需要的材料。
- 一次性测试和临时材料优先放项目根 `tmp/`，按任务结束后随时可清除处理；长期保留材料的归属见 [文档维护约定](devDoc/documentation.md)。

## 验证与 Git

- 按改动运行必要检查；修复真实缺陷时保留对应回归。文档与 Git 配置改动只做相关检查，不搭建测试框架。
- 完成时简要说明结果、实际检查和余项；工具返回成功、扫描量或节点数不能代替功能验收。
- 每完成一项完整修改并通过相应检查，及时在 `main` 上 commit；相关代码、文档和 `change_log` 一同提交。特别小的修改可省略 `change_log`。
- 由主 agent 统一检查差异并提交，仅纳入本次相关内容，保留用户已有改动。使用清晰的提交说明。
- Git 保存源码、skills、短文档和小样例；模型、虚拟环境、项目数据库、缓存、密钥及大型运行产物留在仓库外或忽略目录中。

<!-- basepack:start -->
## basePack

- 开始或接续任务时，按本机 Python/配置运行 `memory brief`；保留 mandatory，待核内容按业务需要回源：[启动](.basepack/instructions.md#startup)。
- 宿主支持可取消子任务与任务生命周期时，默认异步启动全项目 `memory maintain`，由程序原子取得本项目维护所有权；已有 owner 时继续业务：[自动维护](.basepack/instructions.md#maintenance)。
- 仅持有维护且 `needs_semantic=true` 时，按 `worker` 返回的模型/推理强度实际派协调者，持续接批：[派工](.basepack/instructions.md#dispatch)。
- 业务结束时 stop 自有 control，取消自有协调者及后代，确认发布阶段结束后释放所有权；未明状态保留待处理：[收尾](.basepack/instructions.md#stop)。
- 用户明确要求维护时，将授权范围内的处置、实际阻塞和余项纳入交付：[显式维护](.basepack/instructions.md#explicit-maintenance)。
- 检索 worker 或调用 agent 使用中发现问题时，轻量报告疑点和观察版本，交维护处理：[使用反馈](.basepack/instructions.md#feedback)。
- 建立与普通维护在作者生成及程序提交后结束；仅用户明确要求记忆系统审计时按其范围审计：[手动审计](.basepack/instructions.md#audit)。

- 分配 AI、检索或调用资源工具时，按本项目配置解析档位与设施入口：[AI 与资源](.basepack/instructions.md#ai-resources)。
- 新检出缺少本机入口时，先完成 [安装与项目接入](https://github.com/YS-Pan/basePack/blob/main/experiments/20261106-basepack/docs/setup-project.md)；本机配置、凭据和记忆通过接入或备份恢复，不随源码分发。
<!-- basepack:end -->
