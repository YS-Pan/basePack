# 拆出阵列整改并比较持续追新方案

2026-11-10，按用户要求将阵列聊天补迁、32×32几何打包和一次隔离恢复从[当前计划](../../archive/20261110-rectification/plan.md)移出，保存到 `D:/project/20261109 array reconstruct/devDoc/tasks/20261110-migration-followup/plan.md`，状态为待执行；该项目入口仅增加计划导航。

当前计划改为basePack范围并重排工作项，新增[持续追新方案比较](../../archive/20261110-rectification/research/continuous-update-options.md)。分析现有版本/事务并查阅LlamaIndex、watchfiles、Qdrant的来源刷新、事件合并和条件更新机制；给出按需、任务内合并、后台监听及不可变版本四种做法，推荐按需入口与同来源合并配合既有乐观接受。

本轮仅拆分/保存计划及分析，没有补迁业务原件、修改算法/打包代码、运行恢复、升级客户端或启动后台追新。检查两项目文档路径、UTF-8、引用和Git差异。
