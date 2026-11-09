# 汇入 yadof 的 Windows Condor 使用经验

按用户要求，三名 subagent 分查旧 yadof 的管理员资料、开发历史和实现/测试；主 agent 复读 HFSS 控制矩阵、解释器与传输修订、native 重试归档和真实超时事故，另核官方作业环境及 submit 参考。结论与原证入口记在 [资源任务调研](../../archive/20261107-resource-coordination/research/yadof-condor.md)，没有复制旧运行树。

为 [资源计划 R0/R2](../../archive/20261107-resource-coordination/plan.md) 补实际线程环境、字段引用/空格路径、资源单位、slot、输入输出回传和超时/回收语义。保留当前独立 embedding 与 Condor 两链设计，不继承 yadof 的多机账户政策、HFSS 专用排除项或重试状态机；进度同步记录调研已完成、运行验证仍待实施。

只读旧项目并修改本项目开发文档，未运行测试、模型、HFSS、Condor 或配置工具，未改旧项目和机器配置。检查新增原证链接及行号、本地链接/标题锚点、UTF-8、Git 差异，以及纲领和原始快照字节保持不变；这些检查不替代真实作业验收。
