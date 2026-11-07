# 规划系统安装与项目路径入口

按用户要求，制定 [安装与路径布局计划](../../work/20261106-rebuild/deployment-layout-plan.md)：basePack 代码统一安装到系统 Python，模型和共享服务状态放 AgentTools，HTCondor 独立安装，项目配置与数据库各归项目。项目 basepack.toml 提供 Python 和机器配置入口，公共路径与预算由机器文件维护一份。

明确 AGENTS 短指针、相对路径基准、config show/doctor、初始化模板及未来 GitHub 的 docs/setup-project.md 接入步骤；这些命令与运行配置尚待实现。将先前未落地的 .memory 目录建议收敛为 .basepack/memory，补项目重任务的 .basepack/jobs，同步资源专项、AI 执行计划与进度。旧安装源码和当前只读检查表明：依赖已共享于 site-packages，但旧产品源码仍为项目副本，不能冒称旧实现已经完成统一 package 安装。

本次只修改开发文档，不移动文件、安装包或改外部配置。检查相关链接/锚点、UTF-8、TOML 示例解析、Git 差异和用户纲领原有内容哈希；运行接入与 GPU 验收仍按后续实施执行。
