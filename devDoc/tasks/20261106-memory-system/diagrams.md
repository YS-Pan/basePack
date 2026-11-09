# 记忆系统方案逻辑框图

这是 2026 年 11 月 9 日[实施计划](plan.md)的图解。**P0 待执行，P1–P5 未实现/验收**；底座及具体存储布局尚未选定，实际状态只在[进度](progress.md)维护。已交付的接入、embedding 和 jobs 见[当前系统图](../../system/diagrams.md)。

## 1. 项目局部知识、原件与共享能力

```mermaid
flowchart TB
  subgraph project["单个业务项目 P：以下记忆数据与流程待实施"]
    original["业务原件与版本系统<br/>文档、图片/PDF、聊天定位"]
    entry["P/AGENTS.md → .basepack/instructions.md<br/>已有读取入口，记忆内容交付待实现"]
    work["工作 agent<br/>接收启动信息 / 一次检索委托"]
    reader["宿主实际派发的订阅 worker<br/>读原文、理解、识图、建关系、评分"]
    store["项目局部唯一持久知识源<br/>来源ID/版本/范围、必要旧依据<br/>节点、独立边、更正、识读结果"]
    index["可重建全文 / 向量索引<br/>向量绑定来源版本 + embedding_identity"]
    backend["待选底座的原生能力<br/>查询、事务、备份与恢复"]
    rank["脚本排序与预算截取"]
    deliver["工作 agent 实收<br/>正文、来源定位、缺口与补读入口"]
    backup["一致性备份集合<br/>持久知识 + 必要配置/依据/索引重建信息"]
    entry -->|宿主实际读取 / 执行 brief| work
    work -->|目标、范围、预算| reader
    reader -->|通过原生查询找候选 / 邻域| backend
    backend -->|查询知识与索引| store
    backend -->|查询派生索引| index
    reader -->|按稳定定位读取新旧原文| original
    reader -->|核来源版本后，经原生事务应用变更| store
    store -->|受影响范围派生 / 重建| index
    reader -->|对实读内容给分| rank
    rank -->|交付选定内容| deliver
    store -->|原生一致性备份 / 导出| backup
  end
  embedding["已交付：机器级 embedding<br/>HTTP / EmbeddingClient<br/>共用模型，不保存项目知识库"]
  original -.->|P2：文字与原图/页编码| embedding
  embedding -.->|向量与语义身份| index
```

建议知识与索引收在 `P/.basepack/memory/` 的少量存储文件，具体格式由 P0 实测决定；通用底座程序可以共用，库文件仍分别留在各项目。业务原件不自动整库复制，原件备份沿业务责任；旧依据须能由版本系统回查或保留必要片段。

启动时，必须保留的信息直接交付，相关与探索线索才参加预算选择；入口存在不等于内容已经到达。变化维护沿“检测 → 共读 → 核版本 → 原生事务 → 更新索引”进行，知识已提交而索引失败时报告待更新范围。embedding 只编码，语义判断由实际订阅 agent 完成。行为与数据合同见[计划](plan.md#最小行为与数据合同)。

## 2. 阶段怎样依赖与验收

```mermaid
flowchart TB
  p0["P0：原生小样例与底座决定<br/>中文 / 独立边 / 并发 / 一致性恢复<br/>外部向量先用预计算值"]
  p1["P1：文字最小闭环<br/>启动实收、一次检索评分委托<br/>显式增量、两项目隔离、新路径恢复"]
  subgraph p2["P2：两分支均通过才结案"]
    semantic["图分支<br/>真实 agent 共读、独立边与图遍历<br/>更正 / 删除 / 合并 / 恢复"]
    vector["图文向量分支<br/>原图向量召回并打开原图/页<br/>语义身份兼容、恢复或重建"]
  end
  p3["P3：主动探索与任务内维护<br/>未点名线索、低成本变化检查<br/>自动小批 + 手动深维护接续"]
  p4["P4：独立评估与真实 HDD<br/>三组对照、实际信息使用<br/>质量 / 主动性 / 全周期成本"]
  p5["P5：正式安装与发布准备<br/>源码外完整闭环<br/>移动、隔离、恢复与使用文档"]
  resources["已有资源 0.5.0<br/>共享 HTTP embedding"]
  p0 --> p1
  p1 --> semantic
  p1 --> vector
  p1 -->|文字流程可先推进| p3
  semantic -->|图维护验收所需| p3
  resources -.->|复用公开接口| vector
  p1 -.->|从此持续积累样例与回归| p4
  semantic --> p4
  vector --> p4
  p3 --> p4
  p4 --> p5
```

P0/P1 无需 embedding 或 Condor；P3 不等待图片向量分支。R9 的资源验收不证明记忆、图遍历或多模态检索已可用。各阶段以实际用户行为和成本证据结案，真实机械盘未测时不能声明满足完整交付要求。详细动作及完成条件只在[阶段计划](plan.md#阶段与完成条件)维护。
