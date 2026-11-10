# 隔离退役记忆的失效传播与历史版本

覆盖扩充的同材料归一中，旧成员已退役且已移出当前摘要依据，现行祖先仍在后续apply中反复待核。最小复现确认0.6.2安装版与修复前0.6.4源码行为一致：原文检测和包含闭包仍遍历退役记录，未变兄弟重绑定还会改写退役记录的source_revision/source_version。

[store.py](../../../experiments/20261106-basepack/src/basepack/memory/store.py)只在当前失效检测、活跃父级传播及自动重绑定排除退役成员。活跃但stale的表示仍传播真实变化；全量历史读取、prepare、expected并发检查、显式复活及更正保持原合同。没有清理正式库旧记录或增加兼容/重试分支。

[维护回归](../../../experiments/20261106-basepack/tests/test_memory_maintenance.py)新增四个原生场景，覆盖重接受祖先后的新增关系、退役桥与活跃待核依赖对照、历史版本不可自动改写，以及复活的旧expected拒绝和previous保留。同一新增回归在冻结0.6.2客户端为3失败/1通过；修复源码的maintenance/store/record_ids/cli/content检查为94通过/1跳过，跳过项需显式共享embedding设施。实际加载源码，使用独立SurrealDB 4内存测试库，18091测试服务已停止；未改评估库或正式库。

这是待发布的main源码修复，没有构建wheel或替换运行客户端。已发布0.6.4与本项目稳定0.6.2均未包含此补丁，本轮评估继续使用字节冻结的0.6.2；不能将源码回归当作普通安装已修复。后续版本按受影响范围构建、安装并验证。

选留的最小复现、原生前后证据、旧版失败与修复后JUnit结果保留在本地 `artifacts/runs/20261110-project-memory-coverage/retired-invalidation/`；本轮覆盖与后续验证见[进度](../../tasks/20261106-memory-system/progress.md)。UTF-8、相关链接及Git差异已核对，未运行无关资源矩阵。
