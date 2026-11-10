# 项目接入

在选定 Python 环境普通安装 basepack 0.6.2 客户端；可使用稳定的独立环境，无需写入系统 Python。按 [部署说明](administrator.md) 只准备所需设施：多项目共用 embedding，普通重任务使用 Condor，记忆使用每项目独立的 SurrealDB 数据目录与进程。文字记忆可以独立使用。随包机器模板可这样读取：

```powershell
python -c "from basepack.project.init import template; print(template('machine.toml'))"
```

每个新项目执行一次。下面的 `bp` 在原生命令失败时立即停止当前脚本；本页后续命令沿用同一 PowerShell 中的函数。`-X utf8` 保证 Python 取证输出为 UTF-8：

```powershell
$python = '<absolute-python.exe>'
$OutputEncoding = [Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = $OutputEncoding
function bp {
    & $python -X utf8 -m basepack @args
    if ($LASTEXITCODE -ne 0) { throw "basepack failed ($LASTEXITCODE)" }
}
bp init --project-root '<absolute-project>' --machine-config '<absolute-machine-config>'
bp --config '<absolute-project>/.basepack/config.toml' config show
bp --config '<absolute-project>/.basepack/config.toml' doctor --facility core
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

`config show` 返回两份配置位置、Python、包版本/安装模式/包根、已配置路径及 agent 模型等级映射。`doctor --facility core|embedding|condor|all` 只读检查设施；首次接入或设施变化时使用，实际推理与作业结果另行验收。

Python 入口为 `basepack.project.config.load_project_config`、`load_machine_config`、ProjectConfig 和 MachineConfig。embedding 使用 `EmbeddingClient(project.machine)`，普通作业使用 `CondorClient(project)`，具体调用见 [资源使用](resources.md)。共享机器管理不需要项目配置：

```powershell
python -m basepack embedding --machine-config '<absolute-machine-config>' status
```

## Agent 模型等级

项目配置 `[ai]` 中 `default_tier` 默认 `tier3`，`retrieval_tier` 默认 `tier1`；`[ai.tiers.tier1]` 至 `[ai.tiers.tier4]` 分别维护 `model` 和 `reasoning_effort`。初始值以 [项目模板](../src/basepack/project/templates/project.toml) 为准，可按宿主可用模型调整。已有项目配置升级时，从模板补入 `[ai]` 和各等级。

```powershell
bp --config '<absolute-project>/.basepack/config.toml' config show
bp --config '<absolute-project>/.basepack/config.toml' config ai
bp --config '<absolute-project>/.basepack/config.toml' config ai --purpose retrieval
bp --config '<absolute-project>/.basepack/config.toml' config ai --tier tier2
```

`config ai` 默认查询日常用途（等同 `--purpose task`），也可查询 `--purpose retrieval` 或显式等级；多轮检索、筛选和重排序使用检索用途。宿主读取结果后向其 agent 派工接口实际传入 `model` 和 `reasoning_effort`；basepack 不自行调用模型。

## 启用记忆

在 `memory init` 前，先核项目配置的 `[memory]`，为本项目选定独立的 `data_dir`、`endpoint` 和 init 生成的 `project_id`。模板的 18080 是待选择的默认值；若已有项目占用它，直接编辑新项目配置中的 endpoint。例子中两个项目可以共用 exe、namespace/database 和共享模型服务，但各自使用下列值：

| 项目 | memory.data_dir 的实际位置 | memory.endpoint | memory.project_id |
| --- | --- | --- | --- |
| A | `<project-A>/.basepack/memory` | `http://127.0.0.1:18080` | A 的 init 生成的 UUID |
| B | `<project-B>/.basepack/memory` | `http://127.0.0.1:18081` | B 的 init 生成的另一 UUID |

再按 [项目 SurrealDB](administrator.md#项目-surrealdb) 启动。该示例从目标配置读取 endpoint，启动绑定与客户端使用同一个值。普通用户可手动启动隐藏进程供同项目多聊天共用，SCM 托管是管理员可选项。启动调用结束后，必须在下一次独立调用检查 `/ready`，然后加载本项目的凭据，执行下面的 init/brief；只有 PID 不算可用。每个新调用 shell 都要提供 `password_env` 指定的变量，凭据读取方式见管理员示例。

```powershell
bp --config '<absolute-project>/.basepack/config.toml' memory init
bp --config '<absolute-project>/.basepack/config.toml' memory guide
bp --config '<absolute-project>/.basepack/config.toml' memory brief --task '当前任务'
```

memory init 才安装 schema、绑定数据库身份，并把 brief 与已安装 skill 的入口加入项目 instructions；普通 init 不启动服务、不建库。误连另一 UUID 的库会失败，保留 UUID 随本项目移动与恢复。由宿主实际读取并执行入口，才会取得启动信息。首建、混合检索、任务内小批维护与恢复见 [记忆使用](memory.md)。配置 source_scope 后，启动快检也发现声明范围内的新增文件；默认只检查已登记原件。

## 版本升级

0.6.1 → 0.6.2 保持项目 schema 2、机器 schema 1 和原有数据；已有项目显式从 [项目模板](../src/basepack/project/templates/project.toml) 补入 `[ai]` 及其等级映射，再用 `config show` 和 `config ai` 核对。

0.6.0 → 0.6.1 保留项目配置、UUID 和记忆数据，先保留旧 wheel 与原生备份，再普通安装新客户端并从源码外核安装位置、read/search 和小批维护。0.5.0 升级也保留 schema 2 项目、schema 1 机器配置及资源数据。已有 0.5.0 embedding 服务的协议与语义身份兼容，可继续运行；本次客户端升级无需停模型。启用记忆的旧配置显式补齐当前 [项目模板](../src/basepack/project/templates/project.toml) 中的 memory 字段，为本项目生成新 UUID，然后运行 memory init。不要复制另一项目的 project_id 或数据库。

0.4.0 的资源接口切换按 [管理员升级步骤](administrator.md#升级与回滚) 处理。当前 Python embedding 使用 `client.embed(inputs, timeout=...)`，超时只结束调用方等待。

当前版本不提供旧项目 `migrate` 命令。项目配置仍是 schema 1 时，先在保留的 0.4.0 安装中执行其 `python -m basepack migrate --from-config '<absolute-old-config>'`，检查 `.basepack/migration/` 备份和映射、数据位置及宿主入口，完成 schema 2 迁移后再升级。历史 ClassAd 中的绝对路径保持原含义，项目移动后按旧备份与映射回查。

## 移动与重新检出

移动启用记忆的项目时，先停止该项目数据库并确认进程退出，保留配置、业务原件和完整记忆数据；按新目录调整服务 cwd、日志与 endpoint，保留 project_id 后再启动并核 read/search。也可按 [原生备份恢复](memory.md#备份与恢复) 搬迁。Python 和机器配置绑定仍须有效；已保存作业材料中的绝对路径需按新位置修复，Condor 历史不会随目录移动。新检出通过 init 重建被忽略的配置和 instructions，AGENTS 与业务源码可正常提交；知识通过对应项目备份恢复。

本路线开发安装使用 `python -m pip install -e '<repo>/experiments/20261106-basepack'`，源码位置须稳定且可供执行账户读取。普通部署构建 wheel 后安装到解释器管理的 site-packages，项目不保存包目录或 PYTHONPATH。依赖或安装元数据变化时重新安装，受影响的运行进程须按管理员流程重启。具体开发、构建和根 tmp 验证命令见 [路线 README](../README.md)。
