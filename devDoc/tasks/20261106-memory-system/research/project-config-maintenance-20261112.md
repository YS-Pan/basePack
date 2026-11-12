# 项目配置维护要点盘点与文档交付依据

2026-11-12（北京时间）。根据用户要求，盘点并发上限之外类似的配置维护事项，供[现行维护计划](../task-duration-and-worker-naming-plan.md)交付使用者说明。本文是计划依据，未修改实际配置或产品；S2 并发字段仍待实施。

## 结论与读取机制

需要一份面向使用者及协助维护的 agent 的“项目配置维护要点”。建议在实施时交付 `experiments/20261106-basepack/docs/project-config-maintenance.md`，按变更事件查阅；项目接入、升级和维护配置入口链接它，不要求每个普通对话扫描全部配置。

不能把所有配置都称为安装快照。新 CLI 调用通过 [load_project_config](../../../../experiments/20261106-basepack/src/basepack/project/config.py)读取项目与机器 TOML，`resolve_ai()` 解析所加载的项目值；长驻 Python 调用者已经构造的 config 对象不会因文件编辑而自动重载。真正需要区分的是：

- 外部状态采集快照：拟议 S2 并发上限，以及未提供本轮注册清单时使用的 Codex 绑定配置。
- 生成或复制的副本：instructions／AGENTS 托管块、复制安装的独立 skills；包或原件更新不等于这些副本已同步。
- 运行时及持久状态：服务按启动配置运行，数据库目录、账户和向量身份有自己的维护流程；修改 TOML 不自动完成相应操作。

## 项目与宿主配置

| 项目 | 何时需要维护 | 要同步什么、如何确认 |
| --- | --- | --- |
| S2 `[ai].max_concurrent_subagents`（待实施） | 用户改宿主并发上限、切 profile／宿主、升级／重新接入 | 重新取得有效上限并归一化为不含主 agent 的 C，同步 basePack 配置及简短来源说明；`config show` 核解析值。它是安装／接入快照，不自动跟踪系统；不为核数字启动完整记忆维护 |
| `[ai]` 默认档位、各 tier 的 model／reasoning_effort | 模型／推理强度的可用性或用户选择改变 | 项目值每次解析，但不自动探测宿主可用性，也不自动采用新版模板初值；用 `config ai` 及所用 purpose／tier 核映射，实际派工仍须传入这些参数 |
| `runtime.python`、`runtime.machine_config`、`project.root` | 客户端环境重建、配置文件／项目／共享设施搬迁 | 同步绝对 Python／机器配置路径和相对配置的 root，核 instructions 与实际 launcher／服务定义中保存的路径；从新路径运行 `config show`，确认目标项目和数据目录 |
| instructions／AGENTS 入口及客户端／schema 版本 | 安装新包、生命周期接口或路径改变 | 按版本接入流程刷新托管块、保留业务块外内容；核实际解释器、配置、skill 位置与版本，再做受影响的业务操作。不能通过重跑普通 init 覆盖既有配置；当前 init 对已存在文件报错 |
| `[memory.codex]` 项目绑定与注册根 | 宿主项目重绑、其它项目注册／删除／移动、worktree 变化 | 既有合同已要求每次维护刷新完整注册根；本轮 `--codex-registry` 覆盖采集绑定，不等于写回 TOML。核 projectId、完整性及 gaps；旧 `registry_complete=true` 不证明今天仍完整；宿主 projectId 与 basePack UUID 是两种身份 |
| `memory.source_scope`、Git ignore 与原件布局 | 新增非 Git 原件／显式包含项、目录重组、发现规则改变 | 按原件范围同步配置和忽略规则，核 discovery boundaries／gaps；Git 内普通新文件通常自动发现。缩小 scope 不清空已登记来源或历史 pending，不能借此删除已接受知识 |
| `memory.search_mode` | 切换 vector／hybrid 或升级旧检索配置 | 新 CLI 读取当前模式，两种模式都需要兼容向量；按实际查询核行为，切模式本身不当然重建索引。支持值及 literal 使用条件链接现有检索说明，不另复制一套规则 |
| 独立 skills 的复制／目录联接 | skill 更新、项目移动／新检出、宿主发现规则改变 | 复制目录须按选定版本更新，联接须核目标；客户端 wheel 不包含这些独立技能。核完整目录、相对引用和宿主实际列表，不能以 init／core doctor 成功代替发现验收 |

若宿主用户级配置改变影响多个已接入项目，应按实际作用域同步受影响项目的容量快照；项目／profile 级变化不批量覆盖无关项目。沿用各项目配置与身份，不复制其它项目的知识或状态。

## 设施与持久状态的联动

下表的 embedding／HTCondor 参数位于 `runtime.machine_config` 指向的机器配置；服务定义、数据库账户和 Condor 原生策略各有自己的维护位置。共享设施变更需核受影响项目，不把当前项目 TOML 当作所有运行状态的唯一控制面。

| 项目 | 何时需要维护 | 要同步什么、如何确认 |
| --- | --- | --- |
| `memory.endpoint`、namespace／database、`data_dir`、UUID | 换端口、迁移、恢复或新项目接入 | 改配置不搬 store、不迁数据；涉及目录／库切换先沿既有合同收尾活动维护与未明发布，不能换路径绕过 owner。核 launcher 的配置路径／cwd及确有旧路径的服务定义；同项目迁移保留 UUID，新项目独立目录／端口／身份，按既有迁移流程核 ready、目标 UUID 和已有知识依据 |
| `memory.username/password_file` | 凭据恢复、路径改变或真正轮换账户 | 客户端与 launcher 同读一份文件；改写文件不会轮换数据库内已存账户，已有库缺失时恢复原凭据。按管理员流程同步账户及文件，只记录路径与结果；用新调用核认证和原知识读取 |
| 数据库启动与托管方式 | 系统重启、改 launcher／服务账户／启动方式 | 配置正确不代表进程已运行；手动进程重启后需按入口重开。启动调用结束后跨调用检查 `/ready`，不以 launcher PID 代替就绪；同一 store 不重复启动，详细流程链接管理员说明 |
| embedding endpoint／service_name／model_root／device | 服务迁址、环境或设备切换 | 同步客户端目标与实际服务启动配置；运行服务不会自动采用文件里的新启动设置，需要生效时沿原托管流程处理。核 status、identity、实际 device／dtype和必要的一次编码；仅改客户端包不当然重启共享服务 |
| 模型及编码语义与向量兼容性 | 模型锁定内容、前处理或相关库版本变化 | 以实际 `embedding_identity` 和编码输入版本判断是否补兼容向量；同模型 CPU／CUDA切换或仅搬模型路径不当然改变身份。`max_pixels` 等语义设置见身份实现，`max_length` 是超限拒绝限制，不自动截断或当然触发全量重建 |
| CUDA 预算、服务负载与 Condor 背景预留 | GPU／常驻程序／模型或承诺负载变化 | 有影响时重新核峰值并协调服务额度和 Condor 普通池；分配器预算不是全卡硬隔离，CPU 路径不套 CUDA 预算。按实际变更选择编码／资源检查，不要求每次改配置都重跑 GPU 并存全验收 |
| HTCondor `bin_dir/config_file` 与站点资源策略 | Condor 安装迁移、配置或资源池改变 | 客户端路径、CONDOR_CONFIG和实际站点配置相符；容量和 GPU 规则由 Condor 维护，不在 basePack 复制实时池容量。按管理员变更流程核 status／queue及需要的小作业；涉及 GPU 才核对应路径 |
| `jobs.jobs_dir` 与执行路径 | 项目／保存位置或执行环境变化 | 新配置不自动移动历史作业材料、回执或正在运行任务的 cwd；核实际解析路径及受影响作业输出，沿已有历史／活动状态处理，不凭旧 PID 或目录名作清理结论 |

## 一个已核的入口刷新边界

[refresh_project_entry](../../../../experiments/20261106-basepack/src/basepack/project/init.py) 在 instructions 已存在时保留原文件，只替换 `basepack-memory` 托管块。[instructions 模板](../../../../experiments/20261106-basepack/src/basepack/project/templates/instructions.md)首段的 Python／配置路径及 `config show` 示例在块外，所以 `memory init` 不保证这些旧路径随搬迁或升级更新。

维护说明须要求核对实际首段、托管块和启动入口，按已有块外字节保护合同处理；不能承诺“重新 memory init 就刷新全文路径”，也不为更新路径覆盖用户正文。本轮只读确认该机制，没有改变刷新实现或复现新的迁移验收。

## 交付要求与依据

未来用户说明按“变更触发 → 配置真实来源与读取机制 → 需同步位置 → 最小确认 → 详细操作链接”组织，不再复制一份完整字段默认值、身份算法或服务部署教程。仅做所改配置相关的核对：路径和解析值用 `config show`，模型映射用 `config ai`，设施诊断按功能选择 doctor，结果用必要的一次实际操作确认。不得把每次维护配置扩成全库审计或完整设施回归。

字段与联动依据：[项目模板](../../../../experiments/20261106-basepack/src/basepack/project/templates/project.toml)、[机器模板](../../../../experiments/20261106-basepack/src/basepack/project/templates/machine.toml)、[项目接入](../../../../experiments/20261106-basepack/docs/setup-project.md)、[管理员说明](../../../../experiments/20261106-basepack/docs/administrator.md)、[资源使用](../../../../experiments/20261106-basepack/docs/resources.md)、[记忆使用](../../../../experiments/20261106-basepack/docs/memory.md)、[向量身份实现](../../../../experiments/20261106-basepack/src/basepack/embedding/identity.py)。本次检查为只读源码／文档盘点，未运行迁库、轮换、重启或模型重建。
