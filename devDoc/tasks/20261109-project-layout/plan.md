# 当前项目文件结构调整计划

2026-11-09（北京时间）。状态：计划已制定，尚未执行目录迁移。依据用户指定的[讨论](codex://threads/01a1bbb1-7c26-7193-9ac6-9900b51fb856)、[file-structure](../../../skills/file-structure/SKILL.md) 与[文档维护约定](../../documentation.md)。

## 目标与现状

在现有结构上落实根目录单套 devDoc、活动工作与历史分工、tmp 优先及统一运行证据位置。按用途和维护寿命分类，持续维护的源码、配置和回归夹具保留在版本管理中，运行快照和输出按复核需要选留。

此前整理已将三个外部验收目录收进 `tmp/acceptance/`，并保存必要原证和迁移映射，见[记录](../../change_log/major/20261108_232211_separate-tmp-and-retained-artifacts.md)。本轮不重复搬迁这些临时实例，也不清空 tmp。

三个现有任务都仍开放：重建任务有 P7/P8，记忆任务有 P0–P5，资源任务有 R9。因此保留三个完整任务目录，`devDoc/archive/.gitkeep` 继续保存空归档入口；任务结束并交接未完事项后再整体归档。源码中的 project、embedding、jobs 是协作模块，不是候选实验路线，继续在 `src/basepack/` 维护。

## 目标结构

```text
AGENTS.md                         开发入口与按任务读取条件
README.md                         产品介绍与使用入口
src/basepack/                     唯一产品源码与随包模板
tests/                            长期回归与维护用夹具
docs/                             使用者与管理员操作说明
examples/                         可复用小样例和配置
skills/                           唯一技能源码；发现联接保留
devDoc/
  project-charter.md               用户目标，正文保持
  documentation.md                文档维护规则
  terminology.md                  项目概念
  system/
    overview.md
    architecture.md
    environment.md
    deployment.md                 现行包、项目配置与部署合同
    modules/
  tasks/                          三个现有开放任务及本次整理任务
  archive/.gitkeep                 始终存在，允许为空
  change_log/
tmp/                              一次性工作区，内容默认可清除
artifacts/runs/<原批次名>/          选留的运行、评测及整理原证
dist/                             当前交付包和必要回滚包，继续保留
```

当前不建立 `experiments/` 或 `evaluation/`：尚无需要独立维护的候选路线或共享评测工程。记忆 P0 的一次性小试优先使用 tmp；以后确有独立依赖或执行边界时，再按技能增加相应内容，现行开发文档仍只维护一套。

## 路径映射

| 当前路径 | 目标路径与处理 |
| --- | --- |
| `devDoc/tasks/20261107-resource-coordination/deployment-layout-plan.md` | `devDoc/system/deployment.md`；迁移现行合同，R8 实施过程链接回原任务，R9 提案仍由任务计划维护；当前仍支持的升级合同保留 |
| `artifacts/{condor,native-condor,r0,r5,r8,resource-acceptance,standard-submit}/` | 各自迁到 `artifacts/runs/<原名>/`，保留批次名及内部结构 |
| `artifacts/{agent-team-smoke,file-structure-rename,project-layouts-eval,project-layouts-scope,skills-english}/` | 各自迁到 `artifacts/runs/<原名>/`，保留技能检查原证 |
| `artifacts/tmp-reorganization-20261108/` | `artifacts/runs/tmp-reorganization-20261108/`，包括原 `moves.json` 和 126 份选留原证 |
| `artifacts/validate-agent-team.py` | `artifacts/runs/agent-team-smoke/validate-agent-team.py`，作为当时检查脚本快照原样保留；其中已有过时路径，不作为现行检查入口 |
| `tmp/`、`dist/`、源码、测试、产品文档和技能发现联接 | 保留位置；只修复本次确实受影响的引用 |

原证中的时间、绝对路径、输入、日志和历史配置保持字节不变。隔离夹具内部的 devDoc 是样例原证，随批次保留。新建本次旧路径到新路径的映射，存于 `artifacts/runs/20261109-project-layout/moves.json`；同时记录迁移文件的相对路径、字节数与 SHA-256。旧整理的 `moves.json` 保持原文，通过本次映射连接到新位置，结果文档提供直接阅读方式。

## 实施顺序与完成条件

1. **复核迁移基线。** 重新检查 Git/WIP、源与目标冲突、嵌套仓库或联接、有关进程和引用；记录纲领及原始快照哈希。确认没有新任务正在写待迁目录，保留其它聊天产生的改动。完成条件：逐项映射可执行，需等待的部分有明确原因，其余部分可独立推进。
2. **迁移现行合同。** 将部署合同移入 system，调整现行/历史措辞及相对链接；修复资源、记忆、重建计划与进度以及系统、产品文档中相关引用和锚点。完成条件：当前部署合同只有一个维护位置，R8 历史与 R9 未实施方案可分别追溯。
3. **归并选留原证。** 按映射整批移入 artifacts/runs，不重新拆散现有运行，不删除证据或重跑模型。保留旧映射，生成本次映射与文件清单。完成条件：全部迁移原证哈希一致，从旧回执路径和两轮映射都能找到现存的长期副本。
4. **维护入口与收尾。** 按需更新 AGENTS、documentation、architecture、environment 及任务中的证据入口；在本目录记录实际结果、映射位置、检查及余项，新增变更记录。主 agent 检查差异，在 main 按完整批次提交，只纳入本次内容。

## 验收

- 检查受影响 Markdown 的本地链接、标题锚点、UTF-8、Git 差异和忽略边界；`tmp/.gitkeep`、`devDoc/archive/.gitkeep` 继续跟踪，运行原证和临时材料继续忽略。
- 核迁移文件清单、字节数与 SHA-256，纲领和原始快照哈希不变。历史路径允许留在原证内，维护中的入口必须指向现存位置或明确映射。
- 从 AGENTS 实际找到当前实现、资源 R9 和记忆 P0/P1；从对应结果页找到 R8 运行回执，以及前次整理选留的验收配置、输入输出和作业日志。复核链只依赖长期材料，不能依赖 tmp 副本。
- 本轮只调整文档与选留原证位置，执行相关路径检查即可；不加载模型、不提交 Condor 作业、不重新安装或运行整套功能回归。若实施盘点发现真实执行依赖，先修复该依赖并做对应轻量验证。

计划交付后等待用户安排实施；本次不改项目纲领、不扩展技能、不改变运行服务或清理现有文件。实施完成后将本任务结案并整体移入 archive，保留最终映射和验收结论的入口。
