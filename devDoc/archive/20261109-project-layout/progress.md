# 实验路线布局迁移进度

2026-11-09（北京时间）。按 [计划](plan.md) 执行，主 agent 负责路径搬迁、最终集成与提交。

## 已完成

源码、声明、测试、产品文档、样例、资源 skill 和 dist 已成组迁入 experiments/20261106-basepack；现行部署合同已归 system，原证已归 artifacts/runs。990 份原证及旧 wheel 哈希一致，纲领与原始快照字节不变。

源码和新 wheel 各 92 项回归、隔离安装及源码外烟测通过，实际导入来源正确；缓存与 Windows venv PID 的验证条件见 [结果](result.md)。共享普通 wheel 和五份机器/Condor 配置保持；resources 联接已重定向，根和实验目录实际技能发现通过。

映射、原证和验收回执已选留到 artifacts/runs/20261109-project-layout。任务结案并整体归档，后续从 [重建进度](../../tasks/20261106-rebuild/progress.md) 接续 R9、记忆 P0–P5 和 P7/P8；本次没有实施这些功能。
