# 当前basePack总体逻辑

以下两张流程图记录0.16.0历史基线；当前0.18系列合同见[实现概览](overview.md)与[记忆模块](modules/memory.md)。实际安装版本、wheel及验收状态以[部署合同](deployment.md)为唯一维护源，维护范围与余项沿[进度](../tasks/20261115-real-use-rectification/progress.md)，推广历史见[迁移结果](../tasks/20261115-real-use-rectification/migration-result.md)。当前实现与验收不改写旧图的历史含义。

2026-11-17的[修改前/修改后完整系统图](../tasks/20261115-real-use-rectification/forgetting-options.md#修改前后的完整系统)是方案图，图源及生成说明在[任务图目录](../tasks/20261115-real-use-rectification/diagrams/README.md)；它们不证明0.17已安装、迁移或完成长期效果验收。本页不重绘该批SVG/PNG。0.16验收见[整改结果](../tasks/20261115-real-use-rectification/result.md)和[完整维护观察](../tasks/20261115-real-use-rectification/maintenance-20261116-result.md)，实际路径与服务入口见[部署合同](deployment.md)及[环境记录](environment.md)。

## 0.16总体流程

```mermaid
flowchart TD
  S[项目文件 private 与已绑定聊天] --> M[maintain 采集与发现变化]
  M --> C[阶段协调者组织来源组]
  C --> A[作者阅读 分块 摘要 识图 建关系]
  A --> P[唯一发布者运行 freeze 与 apply]
  P --> K[项目 SurrealDB 原证 知识版本与语义图]
  E[共享本地图文 embedding] --> P
  K --> B[brief 必保留与已有摘要线索]
  B --> U[业务主 agent]
  U --> Q[检索 worker 多轮词法 向量与图检索]
  K --> Q
  Q --> R[LLM 一次综合评分 程序排序与预算]
  R --> U
  U --> D[宿主确认实际交付的精确版本]
  D --> G[交付事件与全局访问权重]
  G --> R
  T[agent-team 等 skills] -.-> C
  H[HTCondor 重任务资源与进程树] -.-> U
```

brief不按当前问题搜索；mandatory独立保留。检索worker回源、展开图并给综合分，rank仅按分数排序、去重与预算，不第二次乘访问权重。交付必须由宿主确认实际收到的知识版本；search/read/rank不是交付。

图示0.16访问偏好只按真实非空交付事件计算，没有日历衰减；全项目G意味着持续做A仍可能改变B的访问提示。该历史基线当时没有行为向量、自动视角或局部钟。行为重要性不控制语义有效性，也不删除冷材料。

## 0.16维护与生命周期

```mermaid
flowchart LR
  O[唯一 owner 与 control] --> X{请求新聊天采集}
  X -->|是| C[collector]
  X -->|明确跳过| F[既有原件与文件维护]
  C -->|成功| F
  C -->|失败| Z[保留原错 核自有启动清理]
  F --> W[固定候选中的有界来源组]
  W --> A[语义作者及唯一发布者]
  A --> V[原子接受 实际版本与缺口]
  V --> N[适用长任务实际干净接续]
  N --> W
  V --> S[父任务 stop 结束自有团队]
  S --> R[发布终态明确后 release]
```

0.16的`--skip-codex-collection`只跳过本轮新聊天采集，`--scope`未对所有已登记来源和历史pending真实限域。0.17已替代这两项合同，具体见[记忆模块](modules/memory.md)。0.16阶段接续保持同轮receipt/owner/control，已实际验证；全队成本与组内机械往返仍有局限。普通维护在作者处置和程序接受后结束，审计只在用户明确要求时执行。

## 代码、项目数据与共享设施

| 层次 | 当前归属与职责 |
| --- | --- |
| 公共源码与产品文档 | 唯一active工程`experiments/20261106-basepack/`；普通wheel安装后运行，不依赖另一项目工作区 |
| 通用指导 | 根`skills/`的file-structure、agent-team、engineering-judgment由宿主读取；发现联接不复制维护源 |
| 项目实例 | 每项目`.basepack/config.toml`定位身份、凭据、数据库及资源入口；项目知识不跨项目共享 |
| 项目记忆 | SurrealDB保存来源/知识版本、依据、语义图、反馈及交付；assets、control和恢复材料沿其实际配置保留 |
| 限制分发资料 | 根`private/`独立本机Git；另可配置原位private_scope；覆盖隐私、机密和版权/许可边界 |
| 共享embedding | 本地模型与HTTP服务按机器设施复用，向量身份独立于部署及等待；服务不在普通Condor作业树内 |
| 其他重任务 | HTCondor负责容量、准入、排队、时限与作业进程树；调用者声明实际并行和资源，不增加第二套共享锁 |
| 临时与选留原证 | 根`tmp/`可清除；必要原证选留`artifacts/runs/`，不把活跃控制、数据库或唯一原件放临时区 |

公开安装、构建、测试与运行不依赖private原件；原生数据库导出仍可能包含受限内容。完整合同分别见[记忆模块](modules/memory.md)、[资源模块](modules/resources.md)、[本机数据布局](project-data-layout.md)与[文档约定](../documentation.md)。
