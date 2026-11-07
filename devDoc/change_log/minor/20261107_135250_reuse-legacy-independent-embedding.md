# 复用旧实现并修正 GPU 并行方案

用户要求先读旧项目 Codex threads、再读相关代码，并明确 embedding 与其他 GPU 任务独立且可以并行。新增 [专项核对](../../work/20261106-rebuild/research/resource-coordination.md)，区分已实现 runtime/批处理/项目局部热复用/进程清理与跨项目公共服务、统一入口和并行验收缺口。

重写 [资源协调计划](../../work/20261106-rebuild/resource-coordination-plan.md)：提取已有代码，独立 embedding 服务固定预留峰值显存，Condor 普通重任务使用剩余预算；取消旧计划中的模型进程入 Condor、默认整卡轮流和占卡任务不得调用 embedding。同步简短计划、AI 执行计划、进度和调研索引，项目纲领保留用户现有内容。

本次只做阅读和文档修订，未改旧源码、运行测试/模型或操作服务。检查本次文档的 UTF-8、相对链接/锚点、源码和回执链接、Git 差异与纲领原有内容哈希；已有实测均标明历史适用范围。
