# 项目接入

机器管理员先按 [管理员说明](administrator.md) 普通安装 wheel、准备机器配置及 Condor 节点，并在作业树外启动所需的 embedding 服务。项目复用既有 Python、模型和 Condor；只运行普通任务时无需启动 embedding。随包机器模板可这样读取：

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

## 从 0.3.0 项目迁移

先按 [升级步骤](administrator.md#升级与回滚) 核实际调用方、排空旧作业并用旧安装停止服务。普通安装 0.4.0 后，对每份实际接入配置显式执行：

```powershell
python -m basepack migrate --from-config '<absolute-old-config>'
```

目标默认是原解析项目根下的 `.basepack/config.toml`；可用 `--config-name .basepack/config/local.toml` 选择深层位置。迁移将项目 schema 1 和 `[resources]` 改为 schema 2 和 `[jobs]`，按原项目根重算路径并更新入口。原配置、已有 AGENTS/忽略文件/详细入口及改写前 JSON 保存在 `.basepack/migration/<id>/files/`，mapping.json 保存路径映射；成功后移除旧有效配置。新解析器直接拒绝旧项目格式。

原 `.basepack/` 内 memory/jobs 数据保持物理位置；旧自定义数据目录只能在原项目内且非项目根，按映射迁入 `.basepack/memory` 或 `jobs`，目标冲突直接报错。只修复已知生成 JSON 的路径字段，不改业务 arguments。迁移仅处理明确指定的 basePack 配置，不接管旧项目 app 副本、runtime.json、模型缓存、知识或业务授权。完成历史 ClassAd 仍指原绝对路径，数据移动后的历史 status 不保证可用，可从备份和映射回查。

## 移动与重新检出

移动项目后用新配置绝对路径调用，Python 和机器配置绑定仍须有效；已保存作业材料中的绝对路径也需按新位置修复，Condor 历史 ClassAd 不会随目录移动。新检出通过 init 重建被忽略的配置和 instructions，AGENTS 与业务源码可正常提交；不复制其它项目的知识或任务状态。

开发使用同一 Python 的 `python -m pip install -e <repo>`，源码位置须稳定且可供执行账户读取。普通部署构建 wheel 后安装到解释器管理的 site-packages，项目不保存包目录或 PYTHONPATH。依赖或安装元数据变化时重新安装，受影响的运行进程须按管理员流程重启。
