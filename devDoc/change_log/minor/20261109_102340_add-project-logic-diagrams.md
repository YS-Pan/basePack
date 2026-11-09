# 增加项目文件与运行逻辑框图

参考用户指定 chat，按当前 0.5.0 源码、普通安装及部署合同，在 [system/diagrams.md](../../system/diagrams.md) 增加六幅 Mermaid 图：源码与发行、项目绑定、普通作业、embedding 进程、代码职责、文档与 skills。图中明确源码仓库、两处安装、业务项目、机器共享设施和 Condor 的文件及所有权边界。

尚未实施的记忆数据关系和阶段依赖另存 [任务方案图](../../tasks/20261106-memory-system/diagrams.md)，并从系统概览、架构和记忆计划补充入口。Mermaid 源码随 Markdown 维护；渲染及核对临时材料在根 tmp/logic-diagrams，不作为运行依赖。

检查：八图均以 Mermaid 11.4.1 / 无界面 Edge 渲染并检查布局；对照关键源码、实际安装与配置核箭头及路径，修正传输模式的 scratch/cwd 与回传关系；本次链接、标题锚点、UTF-8 和 Git 差异检查通过。无产品代码或服务变更。
