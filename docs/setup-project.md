# 项目接入

机器管理员先按 [管理员说明](administrator.md) 选择共享 Python、普通安装 basePack wheel、配置通用 HTCondor 节点容量，并准备独立 embedding 的机器配置与作业外 broker。复用现有模型和 HTCondor；只运行普通任务时无需启动 embedding。机器模板来自安装包：

```powershell
python -c "from basepack.setup import template; print(template('machine.toml'))"
```

机器相对路径以机器配置所在目录为基准。项目接入不复制机器配置、模型或 Python 环境；已经部署好的机器直接复用。包须对服务与 Condor 执行账户可读，普通用户 pip 的 user-site 安装不能代替该检查。

每个项目执行一次：

```powershell
python -m basepack init --project-root '<project>' --machine-config '<absolute-machine-config>'
python -m basepack --config '<absolute-project>/basepack.toml' config show
python -m basepack --config '<absolute-project>/basepack.toml' doctor --facility core
```

init 从安装包模板生成配置，写入当前 Python 路径，合并 AGENTS 的工具入口与 Git 忽略项。现有配置存在时直接报错。配置放子目录可传 `--config-name config/basepack.toml`。不向父目录寻找配置，调用时显式传实际配置绝对路径。

项目配置的机器绑定只有 runtime.python 与 runtime.machine_config。机器配置定位 Condor 及 embedding；普通作业容量由 Condor 自己维护，项目接入不修改节点策略。project.root 相对项目配置，memory.data_dir 和 resources.jobs_dir 相对项目根解析，当前工作目录不参与数据定位。默认状态和作业材料分别放 `.basepack/memory`、`.basepack/jobs`；资源阶段不建立记忆数据库。

`.basepack/` 和实际配置不进 Git，AGENTS 可提交。`config show` 一次返回两份配置位置、实际 Python、包版本/安装模式/加载位置及解析后路径，供诊断，不另存为有效配置。按 [资源使用](resources.md) 调用 embedding 和重任务。

移动项目后使用新配置绝对路径即可；换机器时更新 Python 与机器配置的两个绑定，保留项目数据。新检出先运行 init；自定义子目录配置须让 AGENTS 指向实际文件。

开发时对同一 Python 执行 `python -m pip install -e <repo>`。源码目录保持稳定，服务和执行账户须可读；已有模块修改由新进程加载，依赖或安装元数据变化时重新安装。稳定部署先构建 `python -m pip wheel --no-deps <repo> -w <wheel-dir>`，再普通安装 wheel。升级前按管理员说明排空并停止旧 broker，安装后重新启动；项目配置在两种模式下相同。

`doctor --facility embedding` 或 `condor` 只读检查对应设施；它们不代替真实推理、作业产物和并行验收。首次接入或设施变化时运行，平常直接执行所需动作。
