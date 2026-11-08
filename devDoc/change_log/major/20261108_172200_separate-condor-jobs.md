# 整理 Condor 作业入口

R8.3 将 resources/ResourceClient 切为 jobs/CondorClient，项目配置升级 schema 2/[jobs]，机器继续 schema 1。submit 集中 JobSpec、字段编码与材料，_processes 集中本机进程观察；worker 只从单份 spec 读取应用参数。

公开 wait 只观察，run 管理交互时限；原生时限、标准 GPU 字段、Condor 权威、提交不确定时只查询及原错误均保留。CLI 自行决定结果/退出码，根入口只组合输出。同步模板、示例、使用说明及 resources skill。

源码全套 71 passed，jobs 37 项回归覆盖参数、失败、提交与生命周期。稳定安装仍为 0.3.0，显式迁移及真实 wheel 验收留待 R8.4。
