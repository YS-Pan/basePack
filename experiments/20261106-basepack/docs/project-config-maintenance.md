# 项目配置维护要点

安装、升级、换宿主/profile、迁移项目或修改 basePack 配置时，按本文核对受影响的项目与功能。普通业务直接使用现有入口；请求新聊天采集时按既有流程刷新 Codex 注册根，不增加每对话全量检查或自动审计。首次操作从 [项目接入](setup-project.md) 开始，字段默认值以 [项目模板](../src/basepack/project/templates/project.toml) 和 [机器模板](../src/basepack/project/templates/machine.toml) 为准。

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

本轮实际可用额度 A 与 C 分开：A 已扣业务、检索及其它占用，不含主 agent。将宿主已有 A 传给派工脚本，由脚本按实际工作量安排；没有 A 时只能说明配置上限。0.18有限任务池还须保留Terra第二turn的恢复名额，固定Luna池及活动worker由程序预登记，不能从瞬时agent列表计算最后退队者。新调用读取新配置，已封口wave继续使用固定身份和回执；容量不足、启动失败及恢复沿[任务池生命周期](memory.md#有限任务池与两段式-terra)，不临时增加无reader的Terra。

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
| Codex 项目重绑、注册/删除/移动其它项目或 worktree 变化 | 更新 `[memory.codex]`；请求新采集时取得完整当前注册根，向 `memory collect` 传 `--codex-registry` 覆盖本轮采集绑定，这不写回 TOML。核 projectId、清单完整性和 gaps，旧 `registry_complete=true` 不证明今天完整。宿主 projectId 与 basePack UUID 是两种身份；见 [聊天接入](setup-project.md#codex-项目聊天接入) |
| 采集新聊天或明确使用已有原件 | 独立 `memory collect --codex-registry <json> --output <receipt>`；绑定项目 maintain 显式选择 `--collection <receipt>` 或 `--retained`。加载回执核归属/hash，retained 不证明 freshness；采集和语义结果分开。见 [维护入口](memory.md#自动维护与手动维护) |
| 新增非 Git 原件、显式包含项、目录布局或 ignore 规则变化 | 按实际额外来源同步 `memory.source_scope` 与 Git 忽略规则，核 discovery boundaries/gaps。Git 内普通新文件及根 private 独立 Git 的已跟踪/未忽略新文件默认发现，后者无需逐项配置 source_scope。显式 `--scope` 实际限制新增、已登记、缺失和 pending 来源，不追加 private；范围外余项保留，已接受知识不因此删除。见 [来源发现](memory.md#自动维护与手动维护) |
| 私有分类范围变化或业务正文需原位私有 | 更新 `[memory].private_scope`；默认 `[]`，根 private 固定私有，`['.']` 为全项目。分类不改变 discovery，freeze 固定规则，规则变化或分类改变沿版本合同重新处理；不以补标覆写历史。核受影响原件及固定依据，复用输入未变的兼容向量；见 [私有资料](memory.md#私有资料与分享边界) |
| 新建/迁移 private 独立仓库或补齐旧记录标记 | 核公共忽略、私有 Git 自身忽略及发现范围，保持外层项目 UUID/数据库；来源缺失沿既有合同。旧来源迁移或补标按已确认映射限定范围，保留历史与恢复材料，记明未覆盖/未知记录；不随升级自动执行 |
| 检索模式变化或旧检索配置升级 | 新调用读取 `memory.search_mode`；vector/hybrid 均需要兼容向量，切模式本身不当然重建索引。按一次实际查询核模式与覆盖；支持值、literal 和旧模式升级见 [启动与检索](memory.md#启动与检索) |

## 数据、凭据与服务变化

下表的 embedding/HTCondor 设置来自机器配置；账户、服务定义与 Condor 站点策略各有维护位置。共享设施变更按影响范围核项目，不把当前项目 TOML 当作所有运行状态的控制面。

| 变更触发 | 同步位置与最小确认 |
| --- | --- |
| 数据库 endpoint、namespace/database、`data_dir` 迁移或恢复 | 先收尾活动维护及未明发布，再按 [项目 SurrealDB](administrator.md#项目-surrealdb) / [备份与恢复](memory.md#备份与恢复) 迁移。改配置不移动 store 或迁库，也不绕过旧 owner。同项目保留 UUID；新项目独立目录/端口/身份。核 launcher 配置路径/cwd及旧路径服务定义，跨调用核 `/ready`、目标 UUID 和原知识依据 |
| `username`/`password_file` 恢复、迁址或账户轮换 | 客户端与 launcher 使用同一凭据文件。已有库缺文件先恢复原凭据；改写文件不轮换数据库已存账户。确需轮换时按 [数据库管理](administrator.md#项目-surrealdb) 同步账户和文件，只记录路径与结果，用新调用核认证及原知识读取 |
| 重启系统、修改 launcher、运行账户或托管方式 | 配置正确不代表进程已运行；手动进程按本项目入口重开，同一 store 只启动一次。启动调用结束后另一次调用核 `/ready`，PID 不代替就绪；见 [数据库管理](administrator.md#项目-surrealdb) |
| embedding endpoint、service_name、model_root、环境或 device 改变 | 同步客户端目标与实际服务启动设置；运行服务不会自动采用新包或启动参数，需要时按 [升级与回滚](administrator.md#升级与回滚) 处理。核 status、identity、实际 device/dtype、attention_backend、supported_context_tokens及gpu_memory_semantics，再做必要的一次编码；仅改客户端包不当然重启共享服务 |
| 模型锁、前处理或相关库改变 | 按实际 `embedding_identity` 和编码输入版本决定补建兼容向量。相同模型在 CPU/CUDA 间切换或仅搬路径不当然改身份；`max_pixels` 等语义设置和身份见 [共享服务与身份](administrator.md#共享服务与身份)。0.15移除旧机器 `max_length`，适配层固定32768实际token上限且不截断；CUDA后端、该上限及软目标不改变身份，未变旧输入继续复用，实际分块／输入改变才重新编码；见 [首建与维护](memory.md#首建与维护) |
| GPU、常驻负载、模型或 CUDA 负载改变 | 有影响时重核峰值并协调 embedding 软目标和 Condor 普通池。`gpu_memory_mib` 模板9216 MiB是可调整目标，不设分配器硬闸，0关闭按目标清理空闲缓存；纯文本初始batch4、含图batch1，合法输入仍可能OOM并保留原错。分别记录allocated／reserved／进程口径，约99%目标不是已验证保证；CPU不套CUDA目标，Condor作业申报合同保持。见 [容量与策略](administrator.md#condor-容量与策略) |
| HTCondor `bin_dir`/`config_file`、安装或资源池策略改变 | 客户端路径、`CONDOR_CONFIG` 和实际站点配置保持一致；实时容量/GPU规则由 Condor 维护。核 status/queue及必要的小作业，涉及 GPU 才核该路径；见 [Condor 容量与策略](administrator.md#condor-容量与策略) |
| `jobs.jobs_dir`、项目保存位置或作业执行环境改变 | 新配置不移动历史材料/回执或运行任务的 cwd。核解析后的作业路径和受影响任务输出，沿现有活动/历史状态处理；旧 PID 或目录名不构成清理证据；见 [普通重任务](resources.md#普通重任务) |

保留每项目原有身份与知识，按现有项目约定记录实际变更、检查和余项；问题反馈使用 [既有格式](setup-project.md#问题记录与反馈)。

## 按变化边界准备恢复集合

先记录客户端版本、wheel、配置及当前 owner/发布状态。结束自有维护并确认发布结果后升级；安装与数据兼容验收结束后，才另开语义维护。积压不是升级失败，也不要求每次重新理解全部资料。

0.17 使用 memory schema 3，member identity 仍为 2；0.16 旧库须按 [版本升级](setup-project.md#升级到-017) 在隔离原生恢复副本上 migrate，再由 finalize 全字段验证并显式写入 marker 3，之后由新客户端 init 并同步切换客户端／库。普通 init 拒绝已绑定但无标记的旧库，不代替桥接或重置合法 J。保留 UUID、原件、知识版本、依据、图、mandatory/private 和未变向量；旧事件不补造锚点，新 J 从切换基点计，未知旧接受时点保留显式 cutover 观察起点。共享 embedding 身份及运行服务不随客户端更新。独立 skills 副本另行同步。

`memory publish` 继续与 freeze/apply 共用发布合同；作者提案引用固定 prepare path/hash，由程序编译依赖及身份。固定稿接续保留 batch_id 和 UUID，数据库 receipt 为权威；本地 result 写失败保留同一 frozen 及 owner/control，不为补投影新建 batch。旧作者稿先结清或作废后重新 prepare；纯 Python 编译仍须传项目配置，见 [发布流程](memory.md#首建与维护)。0.18有限任务池不改变memory schema或行为算法；接入新轮前先在自然边界结束旧worker，固定接受／未发稿与范围、确认发布终态，再由原父任务正确关闭旧轮。新波不继承旧worker协议。Terra二段固定发布结果即FINAL，原父任务在核Terra FINAL与最后Luna通知ack／宿主终态后机械关闭wave，不为等待ack增加Terra轮次。任务池、预登记worker、固定稿、执行回执及通知受理状态随原owner/control保留恢复，停止、claimed、全异常或未明通知不能自动释放；见[任务池生命周期](memory.md#有限任务池与两段式-terra)。

有限wave恢复须从当前 `maintenance/wave.json` 按固定引用收集wave history／closure、初始化与执行回执、stage／handoff、作者草稿及其prepare、coverage／errors、frozen／result和宿主通知证据。部分文件可能在项目 `tmp/`，只复制memory目录不足以恢复。保留原文件字节及原项目根／原绝对路径到恢复位置的映射，按hash核对全部引用；映射本身不表示已支持迁址。跨项目根直接resume旧wave尚未验证，不自动改写固定JSON或新增通用重绑定机制。

| 本次改变 | 需要保留的恢复材料 | 最小实际确认 |
| --- | --- | --- |
| 仅客户端代码、提示词或生成入口 | 新旧 wheel、原配置/凭据及入口块外业务正文；沿用已有可用的数据恢复链 | 在源码外核安装路径与版本，执行受影响操作；刷新托管块并核业务正文 |
| schema、知识版本或访问状态 | 上项加升级前原生 export、项目 UUID、知识历史、关系、原始交付/去重身份及数据库引用的 `behavior/<sha>.json` 模型文件 | 独立物理库桥接与字段比对；核原证、精确版本、模型 hash 及同 delivery_id 重试，再核新功能。重训全史重放，不转换旧权重 |
| private_scope 规则变化、已确认旧记录补标或来源迁移 | 升级前 export、原私有规则／配置、限定来源映射及公私原件/附件恢复集合 | 核正文未变而分类改变的新来源版本及历史回读；freeze 后规则变化须冲突。旧 frozen 按明确条件接续，输入未变向量复用，未知记录不声明公开 |
| 共享模型或服务、数据库底座 | 对应环境/启动配置、原可用 wheel 与数据恢复集合；模型锁及语义身份按实际变化保存 | 按管理员流程切换受影响设施，核真实调用；只有向量身份或输入改变才重建相应索引 |

恢复集合必须能取得其引用的公私原件、受管聊天/附件、图片 assets 及必要选留证据，也覆盖 private 独立 Git 和其忽略但仍需保留的材料；原生数据库 export 不包含全部文件，完整备份仍含公私内容。升级不要求逐份重复制所有研究 artifacts。已有备份可作为不可变基底：记录其绝对位置、hash 清单及本次新增/变更覆盖层，核引用文件仍可取得，写清恢复次序。原件只存在于活动项目、无可用备份时，路径清单不能代替备份；先把缺少的内容纳入恢复集合。相同 hash 的已有内容可复用，不能把 Git 忽略或同一磁盘的存在当作长期备份；公开分享另按 [分享边界](memory.md#私有资料与分享边界) 准备。

本次恢复点与基底一起保留，移动或清理前按恢复清单核引用。此流程不授权清理旧 artifacts、原证、活动 control 或发布未明回执；保留周期由业务项目决定。恢复后的语义现行性仍按已接受内容与已知缺口说明，不用安装成功、向量兼容或字段一致代替判断。
