# 项目接入

机器管理员先按 [管理员说明](administrator.md) 普通安装 wheel、准备机器配置及 Condor 节点，并通过 Shawl 托管所需的 Windows embedding 服务。项目共用模型和服务，仅安装客户端；只运行普通任务时无需启动 embedding。随包机器模板可这样读取：

```powershell
python -c "from basepack.project.init import template; print(template('machine.toml'))"
```

每个新项目执行一次：

```powershell
python -m basepack init --project-root '<project>' --machine-config '<absolute-machine-config>'
python -m basepack --config '<absolute-project>/.basepack/config.toml' config show
python -m basepack --config '<absolute-project>/.basepack/config.toml' doctor --facility core
```

init 从安装包生成 `.basepack/config.toml` 和 `.basepack/instructions.md`，写入当前 Python 路径；根 AGENTS 只合并指向详细入口的短指针，原业务指令保留，Git 忽略整个 `.basepack/`。配置或入口已存在时直接报错。自定义配置可传 `--config-name .basepack/config/local.toml`，必须在 `.basepack/` 内；入口记录实际文件，project.root 按深度生成。调用显式传配置路径，不向父目录搜索。

项目配置使用 schema 2，机器配置保持 schema 1。最小项目绑定为：

```toml
schema_version = 2

[runtime]
python = 'C:\Program Files\Python313\python.exe'
machine_config = 'D:\AgentTools\basepack.toml'

[project]
root = '..'

[jobs]
jobs_dir = '.basepack/jobs'
```

runtime 的两个路径必须是绝对路径。project.root 相对项目配置文件；`[jobs].jobs_dir` 与可选 `[memory].data_dir` 相对项目根，并位于 `.basepack/` 内。机器相对路径以机器文件所在目录为基准。各功能只读取自身必需节：只用 embedding 无需 memory 或 Condor 配置，只用 jobs 无需模型配置。init 不预建数据库或作业目录。

`config show` 返回两份配置位置、Python、包版本/安装模式/包根及已配置路径，仅用于诊断。`doctor --facility core|embedding|condor|all` 只读检查设施；首次接入或设施变化时使用，实际推理与作业结果另行验收。

Python 入口为 `basepack.project.config.load_project_config`、`load_machine_config`、ProjectConfig 和 MachineConfig。embedding 使用 `EmbeddingClient(project.machine)`，普通作业使用 `CondorClient(project)`，具体调用见 [资源使用](resources.md)。共享机器管理不需要项目配置：

```powershell
python -m basepack embedding --machine-config '<absolute-machine-config>' status
```

## 版本升级

0.4.0 项目继续使用原 schema 2 配置和 `.basepack/` 数据；按 [升级步骤](administrator.md#升级与回滚) 停止旧共享服务、更新机器配置及客户端，再启用 0.5.0 服务。项目不再保存服务登记或运行代码。Python embedding 调用改用 `client.embed(inputs, timeout=...)`，超时只结束调用方等待。

0.5.0 不再提供旧项目 `migrate` 命令。项目配置仍是 schema 1 时，先在保留的 0.4.0 安装中执行其 `python -m basepack migrate --from-config '<absolute-old-config>'`，检查 `.basepack/migration/` 备份和映射、数据位置及宿主入口，完成 schema 2 迁移后再升级。历史 ClassAd 中的绝对路径保持原含义，项目移动后按旧备份与映射回查。

## 移动与重新检出

移动项目后用新配置绝对路径调用，Python 和机器配置绑定仍须有效；已保存作业材料中的绝对路径也需按新位置修复，Condor 历史 ClassAd 不会随目录移动。新检出通过 init 重建被忽略的配置和 instructions，AGENTS 与业务源码可正常提交；不复制其它项目的知识或任务状态。

本路线开发安装使用 `python -m pip install -e '<repo>/experiments/20261106-basepack'`，源码位置须稳定且可供执行账户读取。普通部署构建 wheel 后安装到解释器管理的 site-packages，项目不保存包目录或 PYTHONPATH。依赖或安装元数据变化时重新安装，受影响的运行进程须按管理员流程重启。具体开发、构建和根 tmp 验证命令见 [路线 README](../README.md)。
