# 项目接入源码与实例目录归组

R8.1 将配置解析、初始化、诊断和模板集中到 `basepack.project`，同步所有导入与 package-data。公共配置仅解析绑定，memory/jobs 按需读取，机器路径从 MachineConfig.path 派生。

新实例在 `.basepack/` 保存配置与 instructions，根 AGENTS 只合并短入口，原业务指令保留。支持深层配置、中文/空格路径和任意 cwd；包根与模板诊断已修正。源码全套 34 passed，普通 wheel 构建内容核验通过，尚未安装；项目 schema/[resources] 将在 R8.3 切换。
