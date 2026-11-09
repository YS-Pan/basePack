# basePack

basePack 建设项目局部记忆、共享计算资源协调，以及可独立使用的 agent 协作和文件结构技能。

当前唯一 active 路线为 [20261106-basepack](experiments/20261106-basepack/README.md)。0.6.0 提供 SurrealDB 上的项目局部多层记忆、共享图文 embedding 与 HTCondor 作业入口；本机客户端已普通安装，共享资源服务继续复用。实际验收和性能边界见 [记忆进度](devDoc/tasks/20261106-memory-system/progress.md)。

| 入口 | 用途 |
| --- | --- |
| [当前路线](experiments/20261106-basepack/README.md) | 安装、使用、构建、测试及路线内产品文档 |
| [实现概览](devDoc/system/overview.md) | 当前实现与模块入口 |
| [重建进度](devDoc/tasks/20261106-rebuild/progress.md) | 活动任务、依赖与后续交付 |
| [file-structure](skills/file-structure/SKILL.md)、[agent-team](skills/agent-team/SKILL.md) | 可独立使用的通用技能 |
| [AGENTS.md](AGENTS.md) | 开发规则与按任务阅读入口 |

每条路线在 `experiments/` 内维护自己的代码、依赖、配置和使用入口，项目根只维护一套 `devDoc/`。临时工作统一进入根 `tmp/`，选留运行证据进入根 `artifacts/runs/`。
