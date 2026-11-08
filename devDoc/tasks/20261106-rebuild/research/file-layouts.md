# 文件结构 skill 调研与初版验证

路径追溯（2026-11-09）：下文保留当时的运行路径；选留原证现归根 `artifacts/runs/<原批次>/`，位置映射见[布局迁移结果](../../../archive/20261109-project-layout/result.md)。

2026-11-07。范围包括本项目 devDoc、旧项目最终实验分包要求和一手公开资料。研究目标是提炼独立 skill，不在旧项目实施重组，也不复验旧实验效果。

## 旧项目的原要求与未完成状态

| 事实及身份 | 直接依据 |
| --- | --- |
| 每种独立尝试有日期目录、Git、依赖声明、数据索引、测试与说明；需要独立运行，复用明确引用或固定版本 | [旧 AGENTS.md](<D:/project/20261024 doc system/AGENTS.md:12>) |
| 实验自身保存状态、运行与结果，根项目维护共同方向 | [旧 AGENTS.md](<D:/project/20261024 doc system/AGENTS.md:20>) |
| 每实验有源码、依赖锁、配置及数据状态；Git 保存必要声明和恢复信息，大资产可外置 | [研究历史](<D:/project/20261024 doc system/docs/research-history.md:748>) |
| 后续允许系统 Python、固定模型和缓存显式共用，知识与业务状态仍局部 | [研究历史](<D:/project/20261024 doc system/docs/research-history.md:752>) |
| 运行明细归实验，协调层只留结论与证据；实验入口含假设、状态、依赖、复现、缺口和下一步 | [研究历史](<D:/project/20261024 doc system/docs/research-history.md:1309>) |
| 用户要求恢复此前讨论的结构任务，后续计划将 Atlas、Lightgraph、trial、Context 四个登记实验移到 experiments，保留名字、Git、WIP、依赖与资产 | [恢复要求](codex://threads/01a1ae6f-ce9c-7e32-b8d8-7825aafa0655)、[综合计划](<D:/project/20261024 doc system/docs/plans/20261105-project-consolidation.md:97>) |
| 最后调查仍为 no_moves / pending_safe_window，准备材料不构成搬迁回执 | [任务台账](<D:/project/20261024 doc system/20261102 context/state/tasks.json:1614>)、[迁移准备](<D:/project/20261024 doc system/20261102 context/evidence/project-consolidation/root-structure-preparation-001/PREPARATION.md:3>) |

四个现有实验各有 pyproject，但入口和安装方式不同。未发现用户要求每次 run 或所有实验必须成为可 pip 安装、可发布的软件包。初版将“实验分包”定义为独立实验工程单元，语言、Git 与环境边界按任务和已有约定适配；已有独立仓库与 WIP 应保留。

## 公开调研与采用方式

以下是综合后的选择依据，各来源未共同规定一套通用目录：

| 一手资料 | 对本工具有用的内容与边界 |
| --- | --- |
| [Diátaxis 入门](https://diataxis.fr/start-here/) 与 [应用方法](https://diataxis.fr/how-to-use-diataxis/) | 文档可按读者需要分类，结构从实际内容渐进形成；这是内容类型轴，不直接规定工作归档或包边界 |
| [PARA 原文](https://fortelabs.com/blog/para/) | 同一活动项目材料集中，区分长期责任与归档；属于知识管理思路，不是软件打包标准 |
| [Cornell 文件管理](https://data.research.cornell.edu/data-management/storing-and-managing/file-management/) 与 [README](https://data.research.cornell.edu/data-management/sharing/readme/) | 约定应明确且适配团队；关键含义不能仅靠目录，逻辑相关的一簇材料可以共用说明 |
| [GitHub README](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes) | 简短项目入口和相对链接适合仓库内导航；不能推出每条链接都需要一个模型往返 |
| [Nx 文件结构](https://nx.dev/docs/kb/folder-structure) | 单仓库可采用平铺包或 apps/libs，随领域和复用需求分组；不是所有项目必须采用的名字 |
| [Research compendium 原论文](https://faculty.washington.edu/bmarwick/PDFs/Marwick-Boettiger-Mullen-2018-TAS-research-compendia.pdf) | 数据、方法、输出分开并解释关系，记录环境；复杂程度不同，可以不采用正式软件包 |
| [PyPA src 与 flat 布局](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/) | 安装与导入边界会影响布局；src 通常增加安装步骤，小脚本不必套完整包 |
| [PyPA 脚本元数据](https://packaging.python.org/en/latest/specifications/inline-script-metadata/) | 单文件脚本也可声明依赖；不等于运行已经验证或默认需要某个执行器 |
| [uv workspaces](https://docs.astral.sh/uv/concepts/projects/workspaces/) | 关联多包可共享锁文件；依赖冲突或独立环境需求不宜强行共用，声明仍需核实 |
| [Cookiecutter Data Science](https://cookiecutter-data-science.drivendata.org/#directory-structure) | 源码、原始/中间/处理后数据与报告各有职责，完整模板按需取用 |
| [Snakemake 工作流组织](https://snakemake.readthedocs.io/en/stable/snakefiles/deployment.html) | 区分 workflow、config、results、resources，明确执行入口；不将其专用工具链变成通用要求 |

## 初版细化

- 开发文档采用维护/生命周期轴，实验工程采用主题与运行边界轴；两者可以组合，未来参考也可按真实需求扩展。
- 实验工程承载方法的独立演进，一次 run 记录某一配置与输入的执行。共享代码保持一个维护源，共享资产通过配置和版本定位。
- 入口给任务所需的直接材料；已知文件或章节同批读取，只有选择依赖才补读。目录角色是线索，事实、提案和过期状态仍以内容及版本判断。
- 迁移核对 Git/WIP、活动运行、命令、导入、配置和引用。归档与删除分开处理，重跑昂贵实验不是整理的默认动作。

## 验证范围

标准 skill 验证器以 Python UTF-8 模式执行通过，元数据与未完成占位符检查有效。另由不带本次讨论历史的独立 agent 使用实际 skill 完成三种请求：

| 案例 | 观察到的行为与检查 |
| --- | --- |
| 只建议的混合项目：design 加 labs；Alpha 只改种子，Beta 依赖冲突且原路径有活动运行 | 保留现有命名和运行路径，将开发材料与实验工程组合；未按每个 run 拆包、复制大数据或强制统一环境。根 agent 复核夹具全部文件未变 |
| 已授权的开发文档整理：原 status 混有工作日志，另有计划、报告和原始记录 | 实际建成系统说明与任务目录、更新根入口；相关链接可达，计划、已有报告和原始记录的 SHA-256 与迁移前相同，原工作日志仍保留 |
| 论文资料：正文、参考文献、分析脚本和图，没有软件发布需求 | 提出保留四个现有目录，只补总入口和按需数据定位；说明图到脚本和数据、论断到文献的证据链，未强套 devDoc 或软件包模板 |

前两类使用 `artifacts/project-layouts-eval/` 中的隔离夹具，第三类使用自包含任务描述；夹具留在忽略目录，不进入分发。每类仅做一次独立行为测试，覆盖初版选择与文档整理，不证明任意大项目中的运行兼容、广泛泛化或成本收益。未迁移旧项目，未重跑其模型或实验。
