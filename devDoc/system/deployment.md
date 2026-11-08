# 包结构、项目配置与部署合同

更新：2026 年 11 月 9 日。当前唯一 active 路线为 [20261106-basepack](../../experiments/20261106-basepack/README.md)，工程根为 `experiments/20261106-basepack/`。本页维护 0.4.0 的源码布局、实例目录及从 0.3.0 升级的显式迁移合同，对应 [R8 维护计划](../tasks/20261107-resource-coordination/plan.md#实施批次)。使用步骤见 [项目接入](../../experiments/20261106-basepack/docs/setup-project.md)，阶段实施、部署和验收状态统一见 [进度](../tasks/20261107-resource-coordination/progress.md)；0.3.0 的原交付条件保留在 [R7 回执](../tasks/20261107-resource-coordination/standard-submit-result.md)。

R9 的库替换和允许的行为变化见 [复用计划](../tasks/20261107-resource-coordination/plan.md#r9-复用优先的资源实现)。本页以下仍描述当前 0.4.0；项目数据与机器设施的归属继续沿用。候选服务若需要独立共享环境、固定 endpoint 或 Windows 服务配置，在实际选定后更新本合同，不预先把目标写成已部署状态。旧双进程、marker 和代码指纹属于当前实现，不是未来必须保留的安装要求。

本路线的源码、声明、测试、用户文档、示例及资源 skill 归入同一实验工程；项目接入代码和模板位于其 `src/basepack/project/`。由 basePack 管理的业务项目局部文件集中在各自 `.basepack/`，运行代码通过正常安装使用。根 devDoc 保留现行合同与任务材料，R8 的实施记录仍在原资源任务。

## 位置与责任

| 内容 | 维护位置与责任 |
| --- | --- |
| 产品代码、依赖、模板 | 开发维护源为 `experiments/20261106-basepack/`；运行代码由 pip 管理安装 |
| 项目接入源码与模板 | `experiments/20261106-basepack/src/basepack/project/`，同一职责集中维护 |
| 实例配置、操作指令、索引、作业材料及其它生成数据 | 各接入项目 .basepack/，按模块用途组织 |
| 模型与版本清单 | AgentTools/models/组织/模型/revision，多项目显式共用 |
| 机器配置 | AgentTools/basepack.toml，全机一份，保存路径和 embedding 设置 |
| embedding 登记、锁与运行日志 | AgentTools/state/basepack/embedding/，只保存共享服务状态 |
| 普通作业容量、站点策略及原生状态 | HTCondor 的安装/运行目录，Condor 唯一维护 |
| 原件、业务源码及用户指定导出 | 沿用业务布局，工具保存引用和必要派生内容 |

共享安装路径由解释器管理，不在项目保存 package_dir/PYTHONPATH 或 app 副本。机器路径通过显式配置定位，公共源码不写死本机绝对路径。根 `skills/file-structure/`、`skills/agent-team/` 与 `devDoc/` 保留项目级职责；本路线资源技能在 `experiments/20261106-basepack/skills/resources/`，对应根 `.agents/skills/resources` 发现联接。开发临时材料默认进入根 `tmp/`，需长期复核的原证选留到根 `artifacts/runs/`，生命周期见 [文档约定](../documentation.md)。

## 0.4.0 源码结构

以下源码树相对实验工程根 `experiments/20261106-basepack/`；各 __init__.py 按需导出公开接口，保持轻量。记忆模块到 P0 有实际实现时创建。

```text
src/basepack/
  __init__.py
  __main__.py                    命令组合与输出
  project/                       项目接入源码与模板
    __init__.py
    config.py                    ProjectConfig、MachineConfig 及唯一解析实现
    init.py                      初始化项目、合并宿主短入口
    migrate.py                   显式迁移旧项目配置与生成材料
    doctor.py                    只读诊断
    templates/
      project.toml
      machine.toml
      instructions.md
      agents-snippet.md
  embedding/
    __init__.py
    cli.py
    client.py                    请求、取消与关闭
    admin.py                     机器 status/stop
    supervisor.py                启动并拥有模型进程
    worker.py                    接入、请求队列与模型生命周期
    transport.py                 JSON/HTTP 与远程错误
    registry.py                  登记、锁及部署匹配
    identity.py                  向量语义身份
    qwen3_vl.py                   固定 Qwen3VLEmbedder
    process_owner.py             WorkerProcessOwner
    LICENSE/NOTICE 文件           保留原许可文件名
  jobs/
    __init__.py
    cli.py
    client.py                    CondorClient 生命周期编排
    submit.py                    JobSpec、字段编码及提交材料
    _processes.py                本机进程树观察
    worker.py                    UTF-8 参数桥接
```

### 源码迁移映射

以下保留 R8 从 0.3.0 到 0.4.0 的包内迁移关系；当时根源码现已整体归入实验工程，表内相对模块关系继续有效。

| 0.3.0 维护位置 | 0.4.0 维护位置 |
| --- | --- |
| src/basepack/config.py | project/config.py，Config 改为 ProjectConfig，加载函数明确项目/机器作用域 |
| src/basepack/setup.py | project/init.py |
| src/basepack/doctor.py | project/doctor.py |
| src/basepack/templates/ | project/templates/，补详细指令模板 |
| embedding/broker.py | embedding/supervisor.py；登记文件路径保留 |
| embedding/runtime.py | embedding/qwen3_vl.py |
| embedding/owned.py | embedding/process_owner.py |
| embedding/transport.py 中登记/锁、身份逻辑 | 分别归 registry.py、identity.py；传输逻辑留原文件 |
| embedding/client.py 的机器管理操作 | embedding/admin.py |
| resources/ | jobs/，client 中提交编码/材料和 OS 观察分别归 submit.py、_processes.py |

表内相对目标均位于本路线的 `src/basepack/`。R8 已同步修改内部导入、公开 Python API、示例、测试和说明，旧路径没有第二份实现或转发模块。模板读取锚定 basepack.project，package-data 对应 project/templates/；许可仍随 embedding 打包。移动后 config show/doctor 的 package_dir 仍指 basepack 包根，模板检查指 project/templates/。

## 运行后的文件结构

```text
业务项目/
  AGENTS.md                      仅合并 basePack 的短指针
  .gitignore                     追加 /.basepack/
  .basepack/                     整目录 Git 忽略
    config.toml                  唯一实际接入配置
    instructions.md              完整项目操作入口
    memory/                      未来记忆数据库、索引及派生内容
    jobs/                        提交材料、回执、stdout/stderr、事件日志
    ...                          地图、委托、缓存和临时材料按实际需要归组
  ...                            原有业务内容
```

根 AGENTS/.gitignore 是宿主和版本控制所需入口，保留原业务内容，只合并最短指针/规则。共享 skills 复用维护源；不假定 .basepack/ 内的指令或 skill 会被宿主自动发现，确需发现联接时单独验证。新检出通过 init 重建被忽略的本机配置和完整入口，可分发模板只由安装包维护。

本工具默认生成的向量、索引、派生图片、日志和临时材料均进入 .basepack/；业务原件和用户显式指定的导出目标保持原归属，普通作业中的业务程序输出仍遵循用户给定路径。

## 两份配置的边界

项目文件只绑定运行 Python、机器配置及项目局部设置。R8 项目 schema 升为 2，将旧 [resources] 节显式迁为 [jobs]；机器文件继续 schema 1，不因项目命名调整而升级。解析按文件职责检查版本，不自动覆盖、合并或回退旧格式。

.basepack/config.toml 示例；memory 节仅在启用记忆时必需：

```toml
schema_version = 2

[runtime]
python = 'C:\Program Files\Python313\python.exe'
machine_config = 'D:\AgentTools\basepack.toml'

[project]
root = '..'

[memory]
data_dir = '.basepack/memory'

[jobs]
jobs_dir = '.basepack/jobs'
```

机器文件的路径部分示例，实际模型参数和额度沿用当前部署，不在本批重新标定：

```toml
schema_version = 1

[shared]
state_dir = 'state/basepack'

[embedding]
model_root = 'models/Qwen/Qwen3-VL-Embedding-2B/9f2f7e710d6d81056aa5c0a4f04764fec6bb7bda'

[htcondor]
bin_dir = 'C:\condor\bin'
config_file = 'C:\condor\condor_config'
```

| 字段 | 解析基准 |
| --- | --- |
| runtime.python、runtime.machine_config | 明确绝对路径 |
| project.root | 项目配置文件所在目录 |
| memory.data_dir、jobs.jobs_dir | 解析后的项目根，受管理数据统一位于其 .basepack/ 内 |
| 机器文件的相对路径 | 机器配置所在目录 |

init 默认写 .basepack/config.toml，对应 project.root = '..'。保留 --config-name，但新生成配置限于 .basepack/ 内，按真实深度计算根；详细入口指向实际选定配置。每个实例只有一份有效配置，调用显式传 --config，不向父目录搜索。开发验证实例在根 tmp 中隔离；业务实例继续属于各自业务项目，路线切换不自动复制真实数据库。

## agent 如何取得路径

资源调用前，根 AGENTS 的最短指针引导读取 .basepack/instructions.md；记忆启用后，P1 须验证任务开始/接续时的读取触发和 brief 实际交付。详细指令给出所选配置及启动方式，必须保留的信息直接交付，避免把全部合同变成每轮必读内容。

调用形式：

```powershell
& '<python>' -m basepack --config '<project>/.basepack/config.toml' config show
& '<python>' -m basepack --config '<project>/.basepack/config.toml' jobs run --spec '<spec.json>'
& '<python>' -m basepack embedding --machine-config '<machine.toml>' serve
```

config show 返回解析位置与实际安装信息，不另存为第二份有效配置。doctor 仅作只读诊断；首次接入或设施变化时使用，实际推理与作业结果另行验收。项目调用只读取该功能所需配置，机器管理直接用机器配置。

## 开发安装与正式部署

| 模式 | 约定 |
| --- | --- |
| editable 开发 | 对选定开发 Python 安装 `-e <repo>/experiments/20261106-basepack`；源码路径稳定，权限覆盖相应执行账户，新进程加载普通代码改动 |
| 普通 wheel 稳定部署 | 代码与模板进入解释器管理的 site-packages；源码外验收，不依赖开发仓库或旧项目 |

构建、回归和安装命令见 [路线 README](../../experiments/20261106-basepack/README.md)。pytest 不保留持久缓存，临时夹具与构建 TEMP/TMP 显式指向根 tmp；交付与回滚包位于本路线 dist。同一解释器只保留一种有效安装。依赖、入口或元数据变化时重新安装；运行中的进程按受影响范围重启。当前保留一个发行包和可选 embedding 依赖，共用已有模型和环境；专用模型解释器或独立客户端发行版留待实际冲突需求。

从 0.3.0 升级到 0.4.0 的顺序：

1. 准备新 wheel、旧配置到目标的映射和可恢复备份；核实际调用方和在途工作。备份随所属项目的 .basepack/ 保存，不创建新的根目录工具文件。
2. 暂停提交并排空旧作业，用旧安装停止共享服务。旧 resources.worker 入口与旧 payload 不能留到删除模块后再执行。
3. 普通安装新 wheel，对实际接入配置执行 `migrate --from-config <old-config>`，显式迁移项目 schema/节名、配置路径和宿主指针，再启动新服务。新解析器直接拒绝不支持的项目版本，旧配置只在显式迁移步骤读取，不建设长期双格式加载。
4. 完成源码外功能验收后恢复提交；失败时按记录恢复对应安装和配置。站点 60/70 容量/提交策略、机器 schema、模型及共享状态物理位置保持原合同。

## 从旧方案到本方案

| 原位置或接口 | 显式迁移 |
| --- | --- |
| 根 basepack.toml | .basepack/config.toml，默认 project.root 从 . 改为 .. |
| 旧自定义配置 | 按原解析出的项目根重算新相对路径，保持实际项目根不变 |
| schema 1 的 [resources] | 项目 schema 2 的 [jobs]，jobs_dir 路径保持原语义 |
| 完整根 AGENTS 片段 | 详细内容到 instructions.md，根只留触发明确的短指针 |
| 原有 .basepack/memory、jobs | 保持物理位置；旧自定义数据目录完成在途工作后按映射迁入 |
| resources CLI/API/worker 模块 | 一次切到 jobs CLI/CondorClient/新模块路径，交付说明列出全部变化 |
| 旧项目 app 副本、runtime.json、局部模型缓存 | 仅作历史参考；新工具统一安装、共享模型，不自动接管旧知识或任务状态 |

`project/migrate.py` 只在显式迁移时读取 schema 1，按原解析项目根生成 schema 2 配置。`--config-name` 可指定 `.basepack/` 内的深层目标。原配置、已有 AGENTS/忽略文件/详细入口及改写前 JSON 备份到所属项目 `.basepack/migration/<id>/files/`，mapping.json 保存来源、目标和数据移动映射；成功后移除与目标不同的旧有效配置。TOML 字段和值保留，注释不保留。

已在 `.basepack/` 内的数据保持物理位置；旧自定义目录必须在原项目内且低于项目根，迁入 `.basepack/memory` 或 `.basepack/jobs` 前拒绝目标冲突。迁移修复已知生成 JSON 的路径字段，保留业务 arguments/environment。已完成 Condor 历史 ClassAd 保留原 BasePackPayload 绝对路径，目录移动后的历史 status 不保证可用，可按备份与映射回查。

项目整体移动后，配置按新位置解析，已有作业材料的绝对路径和来源定位仍须核对。模型身份与索引兼容按记忆合同处理，安装路径变化不等于向量语义变化。

## 实施接续与完成条件

R8 的分步动作与完成条件保留在 [R8.0–R8.4](../tasks/20261107-resource-coordination/plan.md#实施批次)，实际交付见进度；后续复用实现按 [R9](../tasks/20261107-resource-coordination/plan.md#r9-复用优先的资源实现) 接续。本页保留 0.4.0 布局与迁移合同：源码/模板唯一维护源、普通 wheel 包根，以及源码外两项目、任意 cwd、深层配置、中文/空格路径、移动、新检出与显式迁移的原验收范围不变。R9 以自己的功能结果和资源归还验收，记忆数据库隔离与应用效果仍由 P1/P5 验证。

## R8 项目局部文件统一目录

此入口保留前两次目录讨论的引用。两侧目录要求、命名与后续架构整理已统一到本页和 [当前维护计划](../tasks/20261107-resource-coordination/plan.md)，状态仅在 [资源进度](../tasks/20261107-resource-coordination/progress.md) 维护；R0–R7 的历史部署与验收条件仍见各结果文件，不以新目标覆盖旧证据。
