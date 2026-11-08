# 当前项目实验路线布局迁移计划

2026-11-09（北京时间）。状态：按用户补充要求修订，尚未实施。采用 [experiment-packages](../../../skills/file-structure/references/experiment-packages.md) 的路线工程边界，结合[根开发文档布局](../../../skills/file-structure/references/dev-docs.md)与[维护约定](../../documentation.md)。此前[讨论](codex://threads/01a1bbb1-7c26-7193-9ac6-9900b51fb856)中的单套 devDoc、active 路线收敛和材料生命周期继续适用。

## 目标与范围

把当前 basepack 实现组织为一个完整实验工程，为 memsys 等后续架构改动提供代码、依赖、配置、测试和使用入口的边界。当前路线命名为 `20261106-basepack`，首次迁移后为唯一 active；稳定 ID 不随包版本或普通功能迭代改名。

本次实施范围包括实际搬迁、代码与构建配置修正、全项目文档和命令更新，以及受影响的外部安装、技能发现、服务或作业入口。发现仍在使用的旧路径须一并修复并验证；仅整理目录或链接不能作为完成。R9 库替换和记忆 P0–P5 的功能建设仍由原任务推进，布局迁移先为后续大改提供可运行基线。

当前 project、embedding、jobs 仍是同一路线内的模块，整体迁入实验工程。根目录保留项目目标、统一开发文档和可独立使用的 file-structure、agent-team；resources skill 与本路线接口一起维护。保留单一 Git 仓库，源码和技能各有唯一维护源。

## 目标结构

```text
AGENTS.md                            项目规则及路线、任务读取入口
README.md                            项目目标、active 路线和实验索引
skills/
  file-structure/
  agent-team/
devDoc/                              根目录唯一开发文档树
  project-charter.md
  documentation.md
  terminology.md
  system/                            当前 active 路线的实际实现
    deployment.md                    当前布局、配置及部署合同
    modules/
  tasks/                             活动计划、调查、进度和结果
  archive/.gitkeep                    始终存在，允许为空
  change_log/
experiments/
  20261106-basepack/                  当前唯一 active 路线
    README.md                        产品入口、路线身份、命令及根文档链接
    pyproject.toml                   本路线唯一构建和依赖声明
    src/basepack/                    代码、模板及许可
    tests/                           维护用回归与夹具
    docs/                            本路线用户和管理员说明
    examples/                        小样例及 Condor 配置维护源
    skills/resources/
    dist/                            交付包及必要回滚包，Git 忽略
tmp/<task>/                          全项目一次性工作区，内容可清除
artifacts/runs/<run-id>/              选留的运行、评测和迁移原证
```

`configs/`、`data/` 在路线确有独立配置、稳定输入或恢复引用时创建。根 `evaluation/` 在出现持续复用的跨路线评测输入、协议和程序时创建，答案与评分材料按被测可见范围隔离；评测输出仍选留到 artifacts/runs。实验内不另建 devDoc 或独立计划、进度、结果正文。

## 迁移映射

下表中 `E` 仅为 `experiments/20261106-basepack/` 的书写简记，命令与配置使用实际路径。

| 当前位置 | 目标位置与处理 |
| --- | --- |
| `pyproject.toml`、`src/`、`tests/` | 分别迁到 `E/pyproject.toml`、`E/src/`、`E/tests/`，保留包名 basepack、模块结构及公开入口 |
| `docs/`、`examples/` | 分别迁到 `E/docs/`、`E/examples/`；用户流程、维护样例与路线代码同属一个工程 |
| `skills/resources/` | `E/skills/resources/`，同步发现联接和所有维护源指针 |
| 根 `README.md` 的产品安装与使用内容 | 归入 `E/README.md`，作为包元数据 readme；根 README 改为项目与路线导航，各自内容只维护一处 |
| `dist/` | `E/dist/`，原 wheel 和校验文件按字节保留；新构建显式输出至该位置 |
| `devDoc/tasks/20261107-resource-coordination/deployment-layout-plan.md` | `devDoc/system/deployment.md`；维护实际合同，R8 实施历史与 R9 未实施方案仍链接原任务 |
| `artifacts/{condor,native-condor,r0,r5,r8,resource-acceptance,standard-submit}/` | 各自迁到 `artifacts/runs/<原名>/`，保留批次与内部结构 |
| `artifacts/{agent-team-smoke,file-structure-rename,project-layouts-eval,project-layouts-scope,skills-english,tmp-reorganization-20261108}/` | 各自迁到 `artifacts/runs/<原名>/`，包括原迁移映射和选留证据 |
| `artifacts/validate-agent-team.py` | `artifacts/runs/agent-team-smoke/validate-agent-team.py`，作为历史检查快照保存 |
| `AGENTS.md`、`devDoc/`、两项通用 skill、`tmp/` | 保留根位置，修复实际受影响的内容与引用 |

原有三个任务都仍开放：重建有 P7/P8，记忆有 P0–P5，资源有 R9；保留完整任务目录，分别指向新路线入口。根 system 和计划只描述当前工作，退出路线的必要结论和切换理由再进入根历史。纲领、原始快照、历史回执、日志和配置快照保持原文；历史路径通过本次映射回查，不机械替换原证中的字符串。隔离夹具里的 devDoc 属于样例原证。

此前已将三个外部验收目录收进根 `tmp/acceptance/`，见[记录](../../change_log/major/20261108_232211_separate-tmp-and-retained-artifacts.md)。本轮保留这些临时实例，只有确实要继续使用的入口才修复，不把全部历史脚本恢复成活动调用方。新增迁移映射和必要原证放 `artifacts/runs/20261109-project-layout/`，结果页说明如何结合旧 moves.json 找到长期副本，复核不依赖 tmp。

## 路径与依赖修正

| 边界 | 实施时必须处理 |
| --- | --- |
| 构建、安装与测试 | 开发安装目标从仓库根改为实验根；构建、pytest 配置、示例工作目录和发行路径全部明确。根不保留第二份 pyproject 或源码转发入口。包内 `src`、templates 和许可的相对结构保持，核 package-data 与 readme 实际包含 |
| 根临时区与 Git 边界 | 将实验 pyproject 的 pytest 缓存指向根 tmp，例如 `../../tmp/pytest-cache/20261106-basepack`；basetemp、构建 TEMP/TMP、一次性环境均入根 tmp。补实验内 build/dist、环境、缓存和本机配置的忽略规则，保留版本化夹具及稳定配置 |
| 源码与测试的路径假设 | 扫查 `__file__`、`parents[]`、cwd、PYTHONPATH、命令字符串和模板中的根假设，只修复真实依赖。`tests/test_condor_policy.py` 与 `examples/condor` 同迁，保留其父目录关系；其它代码不可通过旧根源码继续导入 |
| 文档与维护入口 | 更新根 AGENTS/README、devDoc 的系统/环境/模块、任务计划/进度、用户文档、示例与技能中的相对链接、锚点、安装及运行命令。变更记录保留原意，涉及的阅读入口仍须可追溯 |
| 技能发现与宿主配置 | `.agents/skills/resources` 从旧维护源重定向到 `E/skills/resources`，两项通用技能的联接保持；核项目根与实验子目录的实际发现和新检出重建方法。检查已知宿主/编辑器/任务入口是否绑定旧源码路径，修复有效调用方 |
| 外部 Python 依赖与安装 | 盘点解释器、editable/.pth、安装来源及实际导入位置。有效 editable 必须重新绑定实验根；普通 wheel 安装按其实际来源处理。依赖声明随路线迁移，复用兼容环境和权重；依赖冲突时隔离环境并记录可恢复的版本与来源，本轮不顺带升级库 |
| 外部启动与作业路径 | 核已知机器配置、服务/计划任务的动作和工作目录、启动脚本、环境变量及 Condor include/命令引用；从入口追踪实际调用方，修改仍使用旧路径的配置或脚本。在途进程/作业先安全结束再切换，按影响验证实际启动与回收 |
| 数据与共享设施 | 模型、机器共享环境和状态、Condor 设施保留原物理归属，通过显式配置引用；外部配置若确有旧路径则同步修复。业务项目的 `.basepack/` 与知识留在各自项目，路线切换不自动复制真实数据库或继承其它项目状态 |

2026-11-09 的只读盘点确认：系统 Python 是普通安装的 basepack 0.4.0，实际包在 site-packages，无 basepack editable .pth；安装来源元数据记录旧根 dist wheel，是历史来源记录，不是运行源码依赖。已知 `D:/AgentTools/basepack.toml` 与 Condor 主配置/local/60/70 未发现仓库路径，模型及共享状态不需因本次布局移动。保持安装元数据原义，不手工改写 direct_url.json；需要重新部署时通过正常安装完成。

活跃进程命令查询曾返回“无法从客户端中访问 CIM 资源”，计划任务、服务动作和其它用户环境尚未核全。实施时继续用可用入口查清，不能把历史 PID、状态文件或上述局部检查当作已排除所有外部依赖。按实际依赖安排切换窗口；纯源码位置变化不预设全机重装或停服。

## 实施批次

1. **基线与影响清单。** 复核 Git/WIP、目标冲突、嵌套仓库与联接、外部调用链及在途工作；记录源码、交付包和选留原证清单，纲领和原始快照哈希。明确根、实验根、解释器和运行数据根。完成条件：每个活动旧路径有处理方法，当前受阻检查与影响范围明确；保留其它聊天已有改动。
2. **建立完整路线工程。** 成组迁移源码、声明、测试、产品材料与资源 skill，拆分根/实验 README，修正构建、测试、命令、忽略规则与内部路径。完成条件：实验根可以独立安装、构建和运行已有回归，实际导入来自迁移后的源码，根目录只承担项目入口。
3. **接通外部入口。** 按影响清单修复有效 editable、技能联接、宿主入口和外部路径依赖；有部署改动时保留可恢复配置与 wheel，安排在途工作结束后切换。完成条件：已知实际调用方都使用有效目标，未受影响的共享设施继续可用；受阻项不能宣称完成。
4. **对齐文档与证据。** 迁移现行部署合同，修复全项目路径和维护源说明，归并 artifacts/runs，保留 wheel 和原证哈希及旧→新映射。完成条件：从根入口能找到 active 实现、开放任务、安装方法和直接证据，清除 tmp 后必要结论和恢复材料仍可用。
5. **验收与提交。** 按下节验证源码及安装包，记录真实结果、外部变更和余项；主 agent 统一检查差异，在 main 按可运行的完整批次提交。完成后本任务结案并整体归档，修复最终入口。

## 验收

- **源码行为：** 先确认 `basepack.__file__` 指向新实验的 src，再使用实验 pyproject 运行现有回归；核模板、配置、迁移、子进程导入和 Condor 策略样例。缺少设施或权限的检查明确记录，测试收集成功不能代替回归通过。
- **可独立安装：** 从新实验根构建 wheel，核 readme、模板、许可及入口；在根 tmp 的隔离验证环境普通安装，从源码外运行 CLI、init/config show、模板读取与适当的现有回归。确认导入来自本次新 wheel，移除源码导入路径仍可用。当前系统已装旧包，直接跑测试不足以证明新布局有效。
- **活动外部入口：** 核重定向后的资源 skill 实际发现、有效开发安装和改过的启动入口。若改动共享服务或作业运行路径，完成最短实际请求/作业、结果、日志及进程回收验证；按影响复用既有额度证据，纯布局不重复整套 GPU 标定。
- **路径与保留：** 检查受影响链接、锚点、UTF-8、差异及 Git 忽略规则；原证、旧 wheel、纲领与原始快照按清单/哈希核对。残留旧路径区分历史原文和活动错误，不以全库零匹配为目标。
- **导航与复核：** 从根 AGENTS/README 找到唯一 active 实验、构建/使用方法、资源 R9 和记忆 P0/P1；从结果页找到 R8 回执和前次整理的长期日志副本，复核链不依赖 tmp 或旧源码根。

## 后续 memsys 等大改

实际开工时，若 memsys 形成架构替换路线，再建 `experiments/YYYYMMDD-memsys/`，包含自己的入口、依赖、代码、配置与维护用测试；普通功能演进仍在当前路线完成。一次性底座小试优先用根 tmp，持续复用的小资料集按用途进入路线 data/tests 或根 evaluation。

短期允许少数路线比较，选定后更新根 README、system、活动计划和发现入口，停止旧路线的同步开发，保留其代码及历史入口。根 devDoc 始终只有一套现行维护源；确需长期独立演进时拆为多个 project。

新路线复用资源能力时使用有明确版本/哈希和恢复来源的普通发行包或公开服务接口；共同代码需要抽取时只保留一个维护源并声明依赖。避免 sibling sys.path、跨路线 editable 或复制后双向修改。如果两条路线仍使用同一包名，分别验证安装，不在同一环境同时安装两份。兼容环境、模型和缓存可共享，路线依赖不得靠另一条路线的可变源码或数据库隐式成立。

本次修订只交付计划与变更记录，实际迁移、安装和运行验收尚未执行；memsys 技术选型和实现由后续任务决定。
