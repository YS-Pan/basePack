# 交付公共包与项目接入

实现 basepack 包、唯一配置解析、随包模板及 init/config show/按设施 doctor，提供 README 与项目接入说明。项目绑定系统 Python 与机器配置，数据按项目根解析，不依赖当前工作目录或源码副本。

系统 Python 的 editable 安装已观察到临时代码修改被新进程加载；普通 wheel 安装后从源码外初始化两个项目，验证模板、子目录配置及目录分离。3 项配置回归通过，证据位于 `artifacts/r0/`。普通用户 pip 的 user-site 回落经管理员系统安装解决；Condor/embedding 完整交付继续按资源任务推进。
