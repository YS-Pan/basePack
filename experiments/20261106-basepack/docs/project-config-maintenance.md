# 项目配置维护要点

安装、升级、换宿主/profile、迁移项目或修改 basePack 配置时，按本文核对受影响的项目与功能。普通业务直接使用现有入口；每次维护仍按既有流程刷新 Codex 注册根，不增加每对话全量检查或自动审计。首次操作从 [项目接入](setup-project.md) 开始，字段默认值以 [项目模板](../src/basepack/project/templates/project.toml) 和 [机器模板](../src/basepack/project/templates/machine.toml) 为准。

## 先分清读取机制

| 机制 | 真实来源与生效时机 | 维护动作 |
| --- | --- | --- |
| 外部状态快照 | `[ai].max_concurrent_subagents` / `concurrency_source` 是接入 agent 从宿主采集的容量及来源；未传本轮注册清单时使用的 Codex 绑定也是已采集信息 | 外部状态变化后重新取得并同步，文件不会自动跟随宿主 |
| 每次读取配置 | 新 CLI 调用加载项目 TOML 与 `runtime.machine_config`；模型档位、检索模式等按该次配置解析 | 修改权威配置后发起新调用；长期 Python 调用者需重新加载其 config 对象 |
| 生成或复制的副本 | instructions / AGENTS 托管块、复制安装的独立 skills | 按对应入口刷新或复制；更新 wheel/原件不等于副本已同步 |
| 启动配置与持久状态 | 服务使用启动时加载的参数；数据库、账户、历史作业、向量身份各有状态 | 按所属流程迁移、轮换、重启或补建；编辑 TOML 本身不完成这些动作 |

先找到本项目 `.basepack/instructions.md` 中的实际 Python 与配置。以下命令均使用这两个入口：

```powershell
& $python -X utf8 -m basepack --config $config config show
& $python -X utf8 -m basepack --config $config config ai
```

`config show` 核解析路径、目标项目和容量快照；`config ai --purpose retrieval` 或 `--tier <tier>` 核所用映射。确认只覆盖本次影响：设施变化选择对应 `doctor --facility embedding|condor`，再做一次必要的实际操作。配置解析成功不代替知识可读、宿主派工或设施生效。

## 宿主容量、模型与接入变化

### 修改并发上限或切换宿主/profile

接入 agent 从宿主有效配置或明确报告取得上限，归一化为**不含主 agent、包含全部后代**的 subagent 上限 C，写入 `[ai].max_concurrent_subagents`，并在 `concurrency_source` 保存简短的配置来源与计数口径。未知时取得明确值后再配置，不猜默认数。它与使用本项目的宿主绑定，不是每个 Python 环境唯一的机器常量。

新项目通过 `init --max-concurrent-subagents <C> --concurrency-source '<来源与口径>'` 采集。已有项目使用定点更新，不重跑普通 init：

```powershell
& $python -X utf8 -m basepack --config $config config set-concurrency --max-concurrent-subagents <C> --concurrency-source '<有效配置位置与计数口径>'
& $python -X utf8 -m basepack --config $config config show
```

改宿主上限、切 profile/宿主及升级接入时重新取得 C。用户级变更同步其影响的已接入项目；项目/profile 级变更只同步相应项目。该命令只更新容量与来源，不连接数据库，不改 UUID、凭据或知识，也无需为核数字启动完整维护。

本轮实际可用额度 A 与 C 分开：A 已扣业务、检索及其它占用，不含主 agent，尚未扣维护的额外业务预留。将宿主已有 A 传给派工脚本，由脚本计算。没有 A 时返回的是配置允许的组织上限，不能称为当前空闲席位。维护回执固定已开始的布局，新配置供下一轮使用；运行中缩减未启动派工见 [记忆维护](memory.md#自动维护与手动维护)。

### 模型、解释器或入口变化

| 变更触发 | 同步位置与最小确认 |
| --- | --- |
| 模型/推理强度的可用性或用户选择改变 | 修改项目 `[ai]` 的默认用途与 tier 映射；新调用直接读取它，不自动探测宿主可用性或采用新版模板值。用 `config ai` 核所用 purpose/tier，实际派工传入脚本返回的模型和推理强度；见 [Agent 模型等级](setup-project.md#agent-模型等级) |
| Python、机器配置或项目移动 | 同步 `runtime.python`、`runtime.machine_config`、相对配置文件解析的 `project.root`；核 instructions、包装脚本、launcher 和实际包含旧路径的服务定义。从新入口运行 `config show` 核项目与数据目录；见 [移动与重新检出](setup-project.md#移动与重新检出) |
| 客户端升级、生命周期接口或入口路径变化 | 按 [版本升级](setup-project.md#版本升级) 安装并执行 `memory init` 刷新托管块，保留配置与业务正文。核实际解释器、版本、配置与已安装 skill 路径，再做受影响操作 |
| 独立 skill 更新、项目移动或新检出 | 复制安装须更新完整目录；目录联接核目标及相对引用，再核宿主实际技能列表。独立技能不在 wheel 内，init/core doctor 成功不代表已发现；见 [skills 安装与发现](setup-project.md#独立-skills-安装与发现) |

**入口刷新边界：**已有 instructions 只替换 `basepack-memory` 托管块，AGENTS 只替换 `basepack` 托管块。instructions 首段的 Python/配置路径及 `config show` 示例在块外，`memory init` 不保证更新这些旧路径；核对后定点修改相关正文，保留其它块外字节。普通 `init` 遇已有配置报错，用于新接入而非覆盖升级。

## 来源、聊天与检索设置变化

| 变更触发 | 来源、同步动作与最小确认 |
| --- | --- |
| Codex 项目重绑、注册/删除/移动其它项目或 worktree 变化 | 更新 `[memory.codex]`；每次维护前取得完整当前注册根，传 `--codex-registry` 覆盖本轮采集绑定，这不写回 TOML。核 projectId、清单完整性和 gaps，旧 `registry_complete=true` 不证明今天完整。宿主 projectId 与 basePack UUID 是两种身份；见 [聊天接入](setup-project.md#codex-项目聊天接入) |
| 新增非 Git 原件、显式包含项、目录布局或 ignore 规则变化 | 同步 `memory.source_scope` 与 Git 忽略规则，核 discovery boundaries/gaps；Git 内普通新文件通常自动发现。缩小 scope 不清除已登记来源、历史 pending 或已接受知识；见 [来源发现](memory.md#自动维护与手动维护) |
| 检索模式变化或旧检索配置升级 | 新调用读取 `memory.search_mode`；vector/hybrid 均需要兼容向量，切模式本身不当然重建索引。按一次实际查询核模式与覆盖；支持值、literal 和旧模式升级见 [启动与检索](memory.md#启动与检索) |

## 数据、凭据与服务变化

下表的 embedding/HTCondor 设置来自机器配置；账户、服务定义与 Condor 站点策略各有维护位置。共享设施变更按影响范围核项目，不把当前项目 TOML 当作所有运行状态的控制面。

| 变更触发 | 同步位置与最小确认 |
| --- | --- |
| 数据库 endpoint、namespace/database、`data_dir` 迁移或恢复 | 先收尾活动维护及未明发布，再按 [项目 SurrealDB](administrator.md#项目-surrealdb) / [备份与恢复](memory.md#备份与恢复) 迁移。改配置不移动 store 或迁库，也不绕过旧 owner。同项目保留 UUID；新项目独立目录/端口/身份。核 launcher 配置路径/cwd及旧路径服务定义，跨调用核 `/ready`、目标 UUID 和原知识依据 |
| `username`/`password_file` 恢复、迁址或账户轮换 | 客户端与 launcher 使用同一凭据文件。已有库缺文件先恢复原凭据；改写文件不轮换数据库已存账户。确需轮换时按 [数据库管理](administrator.md#项目-surrealdb) 同步账户和文件，只记录路径与结果，用新调用核认证及原知识读取 |
| 重启系统、修改 launcher、运行账户或托管方式 | 配置正确不代表进程已运行；手动进程按本项目入口重开，同一 store 只启动一次。启动调用结束后另一次调用核 `/ready`，PID 不代替就绪；见 [数据库管理](administrator.md#项目-surrealdb) |
| embedding endpoint、service_name、model_root、环境或 device 改变 | 同步客户端目标与实际服务启动设置；运行服务不会自动采用新启动参数，需要时按 [升级与回滚](administrator.md#升级与回滚) 处理。核 status、identity、实际 device/dtype及必要的一次编码；仅改客户端包不当然重启共享服务 |
| 模型锁、前处理或相关库改变 | 按实际 `embedding_identity` 和编码输入版本决定补建兼容向量。相同模型在 CPU/CUDA 间切换或仅搬路径不当然改身份；`max_pixels` 等语义设置和身份见 [共享服务与身份](administrator.md#共享服务与身份)。`max_length` 是超限拒绝限制，不自动截断或当然要求全量重建；补建见 [首建与维护](memory.md#首建与维护) |
| GPU、常驻负载、模型或 CUDA 承诺负载改变 | 有影响时重核峰值并协调 embedding 额度和 Condor 普通池；分配器预算不是全卡硬隔离，CPU 路径不套 CUDA 预算。按实际影响选择编码/资源检查；见 [容量与策略](administrator.md#condor-容量与策略) |
| HTCondor `bin_dir`/`config_file`、安装或资源池策略改变 | 客户端路径、`CONDOR_CONFIG` 和实际站点配置保持一致；实时容量/GPU规则由 Condor 维护。核 status/queue及必要的小作业，涉及 GPU 才核该路径；见 [Condor 容量与策略](administrator.md#condor-容量与策略) |
| `jobs.jobs_dir`、项目保存位置或作业执行环境改变 | 新配置不移动历史材料/回执或运行任务的 cwd。核解析后的作业路径和受影响任务输出，沿现有活动/历史状态处理；旧 PID 或目录名不构成清理证据；见 [普通重任务](resources.md#普通重任务) |

保留每项目原有身份与知识，按现有项目约定记录实际变更、检查和余项；问题反馈使用 [既有格式](setup-project.md#问题记录与反馈)。

## 按变化边界准备恢复集合

先记录客户端版本、wheel、配置及当前 owner/发布状态。结束自有维护并确认发布结果后升级；安装与数据兼容验收结束后，才另开语义维护。积压不是升级失败，也不要求每次重新理解全部资料。

| 本次改变 | 需要保留的恢复材料 | 最小实际确认 |
| --- | --- | --- |
| 仅客户端代码、提示词或生成入口 | 新旧 wheel、原配置/凭据及入口块外业务正文；沿用已有可用的数据恢复链 | 在源码外核安装路径与版本，执行受影响操作；刷新托管块并核业务正文 |
| schema、知识版本或访问状态 | 上项加升级前原生数据库 export，保留项目 UUID、知识历史、关系、交付去重身份及访问状态 | 在隔离库 import；验证旧知识/原证、精确版本回读及同 delivery_id 重试，再核新功能 |
| 共享模型或服务、数据库底座 | 对应环境/启动配置、原可用 wheel 与数据恢复集合；模型锁及语义身份按实际变化保存 | 按管理员流程切换受影响设施，核真实调用；只有向量身份或输入改变才重建相应索引 |

恢复集合必须能取得其引用的原件、受管聊天/附件、图片 assets 及必要选留证据，但升级不要求逐份重复制所有研究 artifacts。已有备份可作为不可变基底：记录其绝对位置、hash 清单及本次新增/变更覆盖层，核引用文件仍可取得，写清恢复次序。原件只存在于活动项目、无可用备份时，路径清单不能代替备份；先把缺少的内容纳入恢复集合。相同 hash 的已有内容可复用，不能把 Git 忽略或同一磁盘的存在当作长期备份。

本次恢复点与基底一起保留，移动或清理前按恢复清单核引用。此流程不授权清理旧 artifacts、原证、活动 control 或发布未明回执；保留周期由业务项目决定。恢复后的语义现行性仍按已接受内容与已知缺口说明，不用安装成功、向量兼容或字段一致代替判断。
