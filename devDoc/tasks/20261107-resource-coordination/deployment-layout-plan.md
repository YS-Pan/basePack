# 安装位置与项目配置布局计划

2026 年 11 月 8 日更新。basePack 的记忆和资源协调共用系统 Python 包入口：本机开发用 editable 安装，稳定部署用普通 wheel。模型保留在 AgentTools，项目数据库留在各项目，HTCondor 独立安装。本页保留部署合同；资源R0–R5及公共入口已交付，普通wheel源码外验收见 [结果](result.md)，维护状态见 [进度](progress.md)，实际操作见 [项目接入](../../../docs/setup-project.md)。

公共安装与配置骨架由 [本任务 R0](plan.md#r0-复用准备与预算标定) 先交付，本页是两项工具共用的部署合同；[记忆任务](../20261106-memory-system/plan.md) 引用它，记忆数据库和检索建设仍由该任务负责。

## 位置与责任

| 内容 | 建议位置 | 维护责任 |
| --- | --- | --- |
| basePack 代码、依赖、随包模板 | 普通 wheel 安装进系统 Python；开发模式由该解释器引用源码仓库 | pip 管理安装，项目统一通过模块调用；模式边界见下节 |
| 模型权重 | AgentTools/models/组织/模型/revision | 机器部署时维护，多个项目共用固定版本 |
| 机器路径、模型选择与资源预算 | AgentTools/basepack.toml | 全机一份，各项目引用；embedding 和 Condor 使用同一预算来源 |
| embedding 实例注册、endpoint、运行锁 | AgentTools/state/basepack/embedding/ | 独立共享服务的运行状态 |
| HTCondor 程序、原生配置与守护进程状态 | HTCondor 自己的安装/运行目录 | 按其安装管理，basePack 只配置入口与必要适配 |
| 项目接入配置 | 项目根/basepack.toml | agent 的固定路径入口，本机有效 |
| 记忆数据库、索引及必要派生数据 | 项目根/.basepack/memory/ | 只属于该项目，具体文件格式随检索底座确定 |
| 项目重任务提交材料、stdout/stderr 和结果定位 | 项目根/.basepack/jobs/ | 只属于该项目；队列终态仍以 Condor 为源 |

site-packages 的绝对目录由解释器管理，项目不保存 package_dir，也不配置 PYTHONPATH。执行时读取配置中的 Python，以 `python -m basepack` 调用安装包；业务项目不复制 app 源码。普通 wheel 部署不依赖源码仓库，开发模式的源码引用由 pip 建立。

## 开发安装与正式部署

| 模式 | 安装与实际源码位置 | 使用边界 |
| --- | --- | --- |
| 本机开发 | 建好 pyproject.toml 和包结构后，对选定系统 Python 执行一次 `-m pip install -e <源码仓库>`；源码留在仓库，site-packages 保存安装信息与导入引用 | 日常修改已有 Python 模块由新进程加载，源码路径须稳定，服务和 Condor 执行账户须能读取 |
| 稳定部署与发布验收 | 对同一解释器普通安装已构建 wheel，代码和模板安装进 site-packages | 换路径、新项目和正式发布均用此模式验证，可脱离源码仓库运行 |

普通代码修改无需反复打包安装；依赖、命令入口或安装元数据变化时重新安装，模板/资源映射变化要核随包内容。已运行的 embedding 服务或 worker 在受影响工作结束后重启才加载新代码，不以重装代替重启。[pip 本地项目安装](https://pip.pypa.io/en/stable/topics/local-project-installs/)、[setuptools 开发模式](https://setuptools.pypa.io/en/latest/userguide/development_mode.html)

同一解释器只维护一种有效安装；editable 与 wheel 显式切换，影响引用该 Python 的所有项目。完整功能批次用普通 wheel 验收后作为稳定运行版本，开发模式不能替代打包验收。项目配置在两种模式下保持相同字段，安装模式与实际加载位置由工具查看，不另建一份有效配置。

## 运行后的文件结构

以下展示普通 wheel 部署。开发模式仅将 basepack 的源码位置改为仓库引用，模型、机器状态与项目数据位置沿用同一约定。机器绝对路径是本机示例，不写进公共源码默认值；AgentTools 的空 profile 保持原用途。

```text
C:/Program Files/Python313/
  python.exe
  Lib/site-packages/basepack/       记忆、embedding 服务和 Condor 适配代码

D:/AgentTools/
  basepack.toml                     全机共享配置，拟新增
  models/                          保留现有模型布局
    Qwen/Qwen3-VL-Embedding-2B/<revision>/
  state/basepack/embedding/         拟新增的共享服务状态

C:/condor/
  bin/
  condor_config                    指向已有原生配置，不复制到项目

业务项目/
  AGENTS.md                        短指针，告诉 agent 先读哪个配置
  basepack.toml                    实际接入配置，不进 Git
  basepack.example.toml            可选的可分发模板，不参与运行加载
  .gitignore
  .basepack/                       不进 Git
    memory/                        本项目数据库、索引与派生数据
    jobs/                          本项目重任务材料与日志
  ...                              原业务文件保持原布局
```

## 两份配置的边界

每个项目只有一个实际接入文件。把 Python 启动路径放在这里，agent 读完即可启动工具；模型和 Condor 的公共路径集中到机器文件，避免各项目分别修改公共设置。两份配置按职责引用，不做多层覆盖或同名字段合并。

项目根的 `basepack.toml` 示例：

```toml
schema_version = 1

[runtime]
python = 'C:\Program Files\Python313\python.exe'
machine_config = 'D:\AgentTools\basepack.toml'

[project]
root = '.'

[memory]
data_dir = '.basepack/memory'

[resources]
jobs_dir = '.basepack/jobs'
```

`D:/AgentTools/basepack.toml` 的路径部分示例：

```toml
schema_version = 1

[shared]
state_dir = 'state/basepack'

[embedding]
model_root = 'models/Qwen/Qwen3-VL-Embedding-2B/9f2f7e710d6d81056aa5c0a4f04764fec6bb7bda'
device = 'cuda:0'

[htcondor]
bin_dir = 'C:\condor\bin'
config_file = 'C:\condor\condor_config'
```

机器文件同时保存 [资源专项](plan.md#显存与其他资源预算) 标定出的 embedding 峰值预留和系统余量；上例只展示路径，未填尚未测得的预算。首版共用一套固定模型配置，切换配置时一并核定预算。动态 endpoint 由共享状态发现，不把端口/PID 或模型实际安装位置再复制到每个项目。

相对路径按下表解析，当前工作目录不参与数据目录定位：

| 字段 | 解析基准 |
| --- | --- |
| runtime.python、runtime.machine_config | 使用明确绝对路径，作为启动与机器绑定 |
| project.root | 相对项目配置文件所在目录 |
| memory.data_dir、resources.jobs_dir | 相对解析后的 project.root，落在该项目内 |
| 机器文件中的相对路径 | 相对机器配置文件所在目录，默认即 AgentTools |

默认配置放项目根；已有项目若选 `config/basepack.toml`，其 project.root 写 `..`，AGENTS 指向实际文件，其他项目相对目录仍按项目根解析。调用时显式 `--config`，不向父目录寻找配置来代替未接入的子项目。独立实验单元使用自己的项目配置和数据库。

HTCondor 适配器使用已配置 bin_dir，给子进程显式传 config_file 对应的 CONDOR_CONFIG；机器环境变量与当前 shell 的 PATH 不成为另一份配置源。独立 embedding 只读取自身所需配置，不以 Condor 接入成功为启动条件。Python 包、路径或配置缺失时直接报告具体位置，不遍历整盘猜测或切换其他解释器。

## agent 如何取得路径

由项目 AGENTS 提供短入口，例如：

> 本项目的 basePack 接入配置为 basepack.toml。使用记忆或资源协调前，读取该文件，按 runtime.python 启动 basepack，命令显式传该配置的绝对路径。首次接入或环境变化时运行 config show 与 doctor；平常直接执行所需动作。

`config show` 在一次调用内解析项目文件与机器文件，返回实际 Python、包版本/安装模式/实际加载位置、项目根、数据库目录、模型根、共享服务状态目录及 Condor 入口，并标出两份源配置位置。平常的 memory/resources 命令内部使用同一个配置模块，agent 无需手工传递所有底层路径。该输出用于查看，不另存为第二份有效配置。

已交付调用形式如下：

```powershell
& 'C:\Program Files\Python313\python.exe' -m basepack --config '<project>/basepack.toml' config show
& 'C:\Program Files\Python313\python.exe' -m basepack --config '<project>/basepack.toml' doctor
```

doctor 检查配置、包定位、相关路径及对应设施的只读接入，开发模式包括源码引用可读性；服务和作业账户下的真实调用另按 R0 验证。实际向量推理和 GPU 并行验收沿资源专项执行，不以路径可见代替功能通过。平常不在每轮任务启动时重复跑全套环境检查。

## GitHub 源码与使用说明

复用现有 devDoc 和 skills，不重组它们。运行工具落地时补这些实际内容：

```text
basePack/                          GitHub 源码仓库
  README.md                       产品入口、安装命令、接入说明链接
  docs/setup-project.md            指导 agent 建立基于 basePack 的项目
  pyproject.toml                  wheel、依赖、入口和模板打包声明
  src/basepack/
    __main__.py                   模块启动入口
    config.py                     项目/机器配置与路径解析的唯一实现
    embedding/                    独立 embedding 客户端/服务
    resources/                    Condor 适配与重任务入口
    templates/
      project.toml                项目配置模板
      machine.toml                机器配置模板
      agents-snippet.md           项目入口短文
  skills/                         既有 skills 与后续按需交付的 skill
  devDoc/                         既有开发材料
```

模板随安装包分发，维护源各一份；init 从已安装包读取，不要求新项目能访问本机源码仓库。未来 `docs/setup-project.md` 区分本机首次部署与每个项目接入，并覆盖这些步骤：

1. **本机首次部署。** 选系统 Python，稳定使用安装 basePack wheel；本机开发按 [两种安装模式](#开发安装与正式部署) 建立 editable 引用。复用/准备共享模型，核独立安装的 HTCondor，建立 AgentTools/basepack.toml，标定预算并验证设施；已经部署过的机器直接复用。
2. **每个新项目接入。** 用所选 Python 执行拟议 `-m basepack init --project-root <project> --machine-config <machine-file>`。init 以当前解释器的 sys.executable 写入 runtime.python，创建项目 basepack.toml、合并 AGENTS 入口与 Git 忽略规则，并按需要提供不含本机绝对路径的 example。现有业务说明保持原意，实际数据目录在对应动作使用时创建。
3. **检查并开始使用。** 按项目配置运行 config show/doctor；再分别演示项目局部记忆和普通重任务。给出文本/图片 embedding 与预算内 GPU 并行的实际验收入口。
4. **换机器或升级。** 新机器普通安装 wheel 并建立机器配置，再填写项目的 Python/机器文件路径；保持项目数据目录。稳定升级按完整功能批次更新安装包，并在工作结束后重启受影响服务。配置与数据库按各自版本维护；模型身份/预处理变化按记忆接口处理索引兼容，不把换安装路径当作换语义模型。

默认项目 Git 忽略项为 `/basepack.toml` 和 `/.basepack/`；AGENTS 与可选 basepack.example.toml 可提交。自定义配置放子目录时，init 忽略实际选定路径。example 只是模板，运行时仅加载所选项目文件及其引用的机器文件，不增加 local.toml、环境变量等多层覆盖。

## 从旧方案到本方案

| 旧位置或先前建议 | 新位置或处理 |
| --- | --- |
| 各项目 .context-memory/app 源码副本 | 系统 Python 统一包入口；开发模式引用唯一源码仓库，稳定部署安装 wheel |
| runtime.json 与模型合同里的机器路径 | 项目 basepack.toml 的启动绑定 + 机器 basepack.toml 的公共路径；语义模型身份仍随项目索引记录 |
| 各项目 cache/vl-worker | AgentTools/state/basepack/embedding，改为机器级同模型实例 |
| 旧项目数据库和业务状态 | 留在旧项目，新项目重新建立自己的 .basepack/memory，不自动导入 |
| 先前建议的 .memory/ | 新实例统一建议 .basepack/memory；本仓库尚无实际数据库，不涉及搬迁 |
| 现有 AgentTools/models 和 Condor | 保留物理位置，只建立明确配置引用 |

旧设计确实把依赖放进系统 site-packages、权重放进 AgentTools；但 [install_context.py](<D:/project/20261024 doc system/20261102 context/scripts/install_context.py>) 154–171 仍复制 app 并生成项目 runtime.json，[旧安装说明](<D:/project/20261024 doc system/20261102 context/docs/INSTALL.md>) 也明确代码在 .context-memory/app。统一包入口及两种安装模式是本次部署目标，不冒称旧实现已完成。11 月 7 日只读检查得到系统 purelib 为 C:/Program Files/Python313/Lib/site-packages，basic_memory 可定位，basepack/context_memory 未被该解释器发现。

## 实施接续与完成条件

资源 R0 先交付 basepack 包、配置模块、随包模板、init、config show 和可按设施选择检查的 doctor；README 与项目接入说明同步交付。公共入口通过后，embedding 和 Condor 分别按各自探针放行 R1/R2，R3 再联合验收；两链客户端只解析自身所需配置。共享服务启动方式、运行账户与作业内访问在 R0 核定，实例生命周期独立于普通作业。详细合同与放行条件以 [资源专项](plan.md#实施批次) 为准；记忆 P0/P1 复用公共骨架，P2 接入同一个 embedding 客户端。

R0 验证：editable 的最小代码修改能被新进程加载，最小普通 wheel 的入口与模板可用，config show 能识别实际安装；两个项目共用代码和机器配置、各自目录分离，子目录显式配置正确定位。R1/R2 随命令补各链示例。R5 用普通 wheel 从开发目录外启动，核代码与模板来自安装包，再验证两链调用、项目移动、AGENTS 入口及新检出接入；切回稳定安装后重启受影响服务。资源阶段只用合成项目，不要求先实现记忆数据库；真实数据库隔离由记忆 P1/P5 验收。正式部署的源码、模板和配置不含对旧开发目录的运行依赖。
