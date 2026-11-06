# 开发文档布局

适合开发者与 agent 共同维护、需要区分长期依据、现行说明、活动工作和历史的项目。它按维护方式组织文档；源码、使用者操作文档和实验工程仍有自己的职责。

## 最小结构与职责

```text
项目/
  AGENTS.md                  简短约定和按任务直达的入口
  README.md                  项目介绍和入门入口，沿用已有安排
  devDoc/
    project-charter.md        项目目标与长期要求
    documentation.md          本项目文档维护约定，有需要再独立
    terminology.md            有歧义的项目特有概念，按需
    current/
      overview.md             实际已有内容与相关入口
      architecture.md         已实现结构、数据流、边界与不变量
      environment.md          有日期的环境核验与未核范围
      modules/                实现后按模块维护契约，按需
    work/
      YYYYMMDD-short-topic/
        plan.md               目标、范围、决定与完成条件
        progress.md           阶段、完成事项、阻碍与下一步
        result.md             交付、实际检查、证据、限制，按需
        research/             调研材料和证据索引，按需
    archive/                  已结束工作的完整目录，按需
    change_log/
      major/                  逐次重要变化
      minor/                  逐次有意义的局部变化，按需
```

示例不是待创建的空骨架。`devDoc` 可沿用项目已有的开发文档目录名。README 与 AGENTS 的分工按既有读者和入口安排确定；简短计划可承载进度和结案，无需为每个标题拆文件。

- 长期依据跨工作阶段维护；现行说明随实际实现更新，待实施方案留在工作材料中。
- 按一次独立工作或一个大阶段建工作目录，内部步骤可留在同一计划。结束时将仍有效的结论落实到现行说明，交接余项，再整体归档并修复引用。
- 来源、方法、条件、结果和限制应能从简短总结进入。较大材料按主题成组，原始快照保留原文；大型运行产物用小样例、说明与位置引用衔接。
- 本方案的变更记录按 `YYYYMMDD_HHMMSS_short-description.md` 逐次保存，写日期、变化、原因、影响、实际检查和依据。沿用目标项目已有的时区、分级与变更记录惯例，特别小的修改可省略。

## 低往返的阅读入口

入口列出常见任务直接需要的路径，表达相关性与选择条件。不要把目录层级解释成必须逐文件执行的工具调用顺序。

| 任务 | 首批材料 | 补读条件 |
| --- | --- | --- |
| 了解现状 | 概览与任务相关的架构部分 | 需要模块约束或词义时 |
| 继续某项工作 | 进度与相关计划章节；阶段明确时同批取齐 | 阶段或证据尚不明确时 |
| 排查环境 | 环境核验与相关任务段落 | 需要具体配置或历史条件时 |
| 修改文档 | 维护约定与目标文件 | 受影响引用或边界需要核实时 |
| 验证结论 | 来源索引及已知相关报告 | 需要原始证据时 |

常驻必须保留的目标、权限和关键约束；其余材料按任务批量读取。目录角色是检索线索，`current` 可能过期，`archive` 仍可提供有效依据，工作计划不等于已经实现。

## 迁移与验收

按用途确定文件归属，保留一个维护位置，避免把现行结论复制到多份状态文件。检查迁移涉及的入口、相对路径、标题锚点、原始快照、Git 属性和实验引用。验收时让维护者从入口找到某项现行能力、一个活动任务及其直接依据，核对内容身份和必要信息，而不只统计文件数。

## 依据与适用范围

这是对实践的组合，来源并未规定上面的完整目录树：

- [Diátaxis](https://diataxis.fr/start-here/) 区分文档满足的读者需要，可用于 `current` 内部；[应用指南](https://diataxis.fr/how-to-use-diataxis/) 支持从实际内容渐进改进。
- [PARA](https://fortelabs.com/blog/para/) 提供活动工作和历史材料的组织思路，不规定软件包边界。
- [Cornell 文件管理](https://data.research.cornell.edu/data-management/storing-and-managing/file-management/) 强调明确约定与可脱离目录理解的描述。
- [GitHub README 指南](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes) 支持简短入口和仓库内相对链接。
