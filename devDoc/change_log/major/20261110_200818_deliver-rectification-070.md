# 交付 0.7.0 查询发布与 CPU 向量整改

按[整改计划](../../tasks/20261110-rectification/plan.md)将查询与维护分离：读取已发布知识及其依据快照，独立候选内容和匹配向量原子发布，自动维护由宿主任务停止与可取消 worker 管理。保留旧知识可用性，明确退役和已知错误继续排除。

CPU/CUDA 使用相同模型、前处理和 FP16，共用语义身份；新增 CPU/CUDA 安装 extra，新项目默认 vector，brief/search 交付覆盖信息。轻客户端解除 Python 3.14 上限。prepare/413 与 Condor 观测、准入职责同步修正，用户和管理员文档按实际操作重写。

最终普通 wheel 在 Python 3.14.10 源码外全套255项通过、无跳过；实际 CPU 图文、跨设备索引复用、旧快照/更新发布、宿主停止以及 Condor 小作业已核。共用客户端与逐项目核验见[安装结果](../../tasks/20261110-rectification/installation-result.md)，完整证据和范围见[整改结果](../../tasks/20261110-rectification/result.md)。

engineering-judgment 已另行提交并保留，没有技能测试；效果在长期真实使用中观察。项目纲领不改，远端推送和 Release 留待独立授权。
