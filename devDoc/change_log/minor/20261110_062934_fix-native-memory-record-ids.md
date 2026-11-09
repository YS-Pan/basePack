# 修复原生记录 ID 往返与接入错误定位

从已提交旧源码在真实隔离库重现特殊 ID 的 `Member changed while embedding`，修复共享 `_record` 的规范 ID 解码及数字类型，使 prepare/apply/read/neighbors/向量回写和 Python 的 expected/依据集合指向同一记录；原始字符串自身的引号与转义保持。保留有限的字符串/整数合同及原生 type::record 构造，未引入额外数据库规范化往返；实际编码期间的变化仍拒绝写入。

文字成员缺起止行时在写入前报告批次位置、成员和字段；不存在的 read 目标明确报错。接入文档与随包 skill 补独立端口、配置同值启动、跨宿主调用存续判据和失败即停，新增可执行三层最小示例。版本与锁定项目元数据更新为 0.6.1，运行依赖不变；一并进入后续普通包的还有 `618749d` 已完成、尚未安装交付的并发与初始化修复。

实际检查：专项 37 项通过，包含真实共享服务特殊 ID 编码与复用；源码全套 157 passed、0 skipped（57.37 s），四项实际向量检查逐名核对。最初完整检查的 8 项失败来自测试环境缺少锁定 sentence-transformers 发行元数据，补齐 6.2.0 的轻量测试依赖后全套通过，共享模型环境未改。17 段 PowerShell、示例 Python、UTF-8、相对链接与 Git 差异检查通过。隔离库已清理；原证选留在 `artifacts/runs/20261110-memory-061/code/` 和 `validation/`。

本提交交付源码修复与文档；普通 wheel、稳定客户端升级和原 PPT 业务实测仍按 [维护计划](../../tasks/20261106-memory-system/real-project-maintenance-plan.md) 继续，实际状态只在 [进度](../../tasks/20261106-memory-system/progress.md) 维护。
