# 公共包与资源协调维护计划

更新：2026 年 11 月 8 日。R0–R7 已交付，本轮将架构评审、命名和两侧目录要求收敛为 R8 待实施计划。现行版本仍为 0.3.0；本轮只维护文档，未修复代码、移动文件或升级部署。实际状态只维护在 [进度](progress.md)，源码/实例布局及安装迁移只维护在 [部署合同](deployment-layout-plan.md)。

目标以 [项目纲领](../../project-charter.md) 为准。当前先完成这次公共工具维护，再继续 [记忆 P0–P5](../20261106-memory-system/plan.md)；底座比较和小资料集准备可并行，不以全部改名完成为前提。

## 保留的边界

- 项目知识、索引、输入引用和作业材料属于各自项目；系统 Python、模型、机器配置和服务状态共享，Condor 独立安装。
- embedding 由作业树外轻量启动者拥有一个模型 worker；客户端直接请求 worker。worker 按需加载、空闲整进程退出，请求取消不杀共享模型，Windows Job Object 保证所有权。
- Condor 是普通作业的容量、队列、终态及 GPU 策略权威。作业客户端只生成标准申请、观察状态和确认回收；embedding 与作业模块相互独立。
- 保留延迟导入模型依赖、原始错误、UTF-8 参数 worker、提交不确定时只查询不重投、成功空查询处理和必要故障回归。CPU/RAM 预检只读实际总量；原生时限与 run 的交互时限均保留，依据见 [历史验收](result.md#预算修复与边界)。
- 当前统一 wheel 与同代代码/配置校验继续使用。先做职责和配置解耦；独立客户端发行版、跨版本服务兼容、通用后端/插件和统一进程框架留待真实需求，不扩大本批。

## R8 设计决定

### 命名与公共接口

以下为本批拟实施的名称，当前实现尚未切换；路径映射和完整目标树见部署合同。

| 当前名称 | R8 目标 | 说明 |
| --- | --- | --- |
| Config / load_config / load_machine | ProjectConfig / load_project_config / load_machine_config | 与保留的 MachineConfig 区分作用域 |
| 根 config.py、setup.py、doctor.py、templates/ | project/ 下的 config.py、init.py、doctor.py、templates/ | 项目接入源码与模板一起归组 |
| resources / ResourceClient | jobs / CondorClient | Python 模块、CLI jobs 和项目 TOML 的 [jobs] 同批迁移 |
| broker.py | supervisor.py | 表达模型进程生命周期管理职责 |
| runtime.py / Runtime | qwen3_vl.py / Qwen3VLEmbedder | 表达当前固定模型实现 |
| owned.py / OwnedJob | process_owner.py / WorkerProcessOwner | 表达模型进程所有权 |
| model_identity / instance_key / service_key | embedding_identity / deployment_fingerprint | 分开向量语义与部署一致性，计算函数与登记字段同名 |
| _cleanup / _admission | _confirm_cleanup / _check_request | 表达确认回收与提交前检查 |

JobSpec、EmbeddingClient、MachineConfig、worker 名称和顶层 init/config/doctor/embed 命令保留。embedding 管理入口统一为 `embedding --machine-config <file> serve|status|stop`，取代暴露内部角色名的 broker 动作。resources skill 和 docs/resources.md 覆盖两条资源链，保留名称；basePack 品牌、包名 basepack、现有 devDoc 和技能发现联接保持原约定。

### 模块与配置依赖

`project/config.py` 是项目/机器配置及路径解析的唯一实现，子包入口保持轻量。ProjectConfig 只解析公共绑定；模块按明确契约读取自身必需节，不让 embedding/作业操作强制依赖未启用的 memory 配置。机器配置可只包含实际使用的设施。重复机器路径从 MachineConfig.path 派生。

EmbeddingClient 接受明确的机器配置/服务发现设置，公开请求、取消和关闭；管理 status/stop 放入 admin.py 的直接函数，启动归 supervisor。机器管理无需项目目录或项目配置。此为调用职责分离，沿用现有凭据，不宣称新增账户权限隔离。

embedding 的 transport 只处理 JSON/HTTP 与远程错误；registry 维护登记文件、锁和部署匹配；identity 维护向量语义标识。模型实现只接收模型/推理设置，脱离 HTTP 与登记模块；worker 保留请求队列和推理生命周期。搬移时将宽泛的 directory/settings 分别明确为 service_state_dir/embedding_settings；已由公开入口 normalize 的输入在内部准备阶段直接使用。

jobs 的 client 保留生命周期编排，submit 集中 JobSpec、字段编码及提交材料，_processes 集中本机进程树观察；薄 worker 保留。payload 只保存一份 spec，worker 从中读取 executable/arguments。各 CLI 统一 register_commands/dispatch，返回简单的结果与退出码；作业成功/清理的退出规则留在 jobs CLI，根入口只组合命令和输出。

### 身份合同

| 身份 | 决定因素与用途 |
| --- | --- |
| 协议版本 | RPC 动作、请求/响应和错误格式；单一显式版本，不建立兼容协商矩阵 |
| embedding_identity | 模型 revision/文件身份、dtype、指令、图像预处理和 pooling 版本等向量语义，供索引记录和比较 |
| deployment_fingerprint | 显式服务代码清单及相关运行配置，检查登记实例和安装是否同代；不作为向量空间标识或完整环境证明 |

图像缩放等会改变向量的设置计入 embedding_identity；仅影响接纳的 max_length、分批、线程、空闲时限和部署路径归运行设置。真正改变向量语义时更新预处理合同版本，P2 据此处理索引兼容。

本批保留代码指纹与配置不匹配时拒用旧实例的保护，拆分/改名后更新唯一服务文件清单，覆盖新登记/身份/进程所有权和配置解析实现。进程启动时固定自己的部署身份，status 返回实际运行身份，管理员可报告与磁盘目标的差异；协议版本不替代这项校验。客户端仍受同代安装约束，不宣称已经支持独立版本升级。

管理员停止旧实例时，仍能使用旧 marker 中的 endpoint/凭据，不先要求新代码匹配。保留 broker.json、broker.lock 等既有登记路径，避免单纯改源码名称引入第二套发现目录。

## 实施批次

所有阶段当前均待实施。按阶段提交和运行必要回归；稳定安装与实例迁移集中在 R8.4，一次完成公开接口切换，不逐小改反复部署。

### R8.0 修复已复现缺陷

- submit 使用局部规范化副本，保持调用者 JobSpec 不变；回归同一相对 cwd 的 spec 在两个项目复用，以及提交失败后对象未改变。[现状](../../../src/basepack/resources/client.py)
- 在客户端锁内先拒绝重复活动 request_id，再登记状态；用假 RPC 验证第二个同 ID 明确失败，首请求的结果、取消和清理正常，不同 ID 并发不受影响。[现状](../../../src/basepack/embedding/client.py)

两项已在本轮审查用内存替身复现，尚未修复；实施时将它们写成必要回归，不启动模型来证明状态逻辑。

### R8.1 项目接入源码与实例目录

按部署合同归组 project/，同步轻量配置作用域、模板读取、package-data、所有导入和包根诊断。新实例统一生成 .basepack/config.toml 和 instructions.md，按需创建局部数据目录；根只保留宿主短指针与 Git 忽略规则。

**完成：** 配置/模板回归通过；包根和模板定位正确；无 memory 或 Condor 节的 embedding 配置仍可按自身合同使用；任意 cwd、深层配置和中文/空格路径正确解析，原业务指令保留。

### R8.2 embedding 职责与身份

拆分 transport/registry/identity，收紧 client/admin 边界，实施 supervisor、模型类和进程所有权命名，固定身份合同及启动时身份。机器管理命令直接读取机器配置，旧实例 status/stop 仍可诊断与关闭。

**完成：** 模型实现不依赖传输/登记；同代与错代检查、管理员停止旧实例、共享单 worker、取消/截止隔离、冷启动取消、空闲退出及崩溃回收相关回归通过。向量语义标识不因纯运行设置变化而改变，语义版本变化能够被识别。

### R8.3 作业职责与命名

迁移 jobs/CondorClient、CLI jobs、项目 [jobs] 节及 worker 模块入口，拆出 submit/_processes，消除重复 payload 和回执读取。明确 wait 只观察，run 管理作业时限；保留原生时限、查询、取消和清理确认行为。

**完成：** spec 不变性、payload 单一来源、复杂 argv/空参数、应用失败、资源预检、提交响应不确定、成功空查询、状态与回收回归通过。标准 GPU 字段及 Condor 站点策略不变，不重标定额度或改写服务器规则。

### R8.4 一次性迁移与普通 wheel 交付

按部署合同准备 wheel、配置映射和交付说明，排空旧作业并用旧安装停止共享服务，统一切换项目 schema、CLI/API/模块入口后再恢复运行。同步 README、使用/管理员文档、示例、相关 skills、系统说明及结果记录，清除本批失用实现和模板。

**完成：** 普通 wheel 源码外两项目初始化、旧配置迁移、项目移动和新检出重建通过；所有模板可从安装包读取，轻量命令不加载模型依赖。用一次真实图文 embedding 与 CPU/GPU 作业核结果、并存、取消、另一项目服务存活、日志和资源归还。复验受影响的生命周期，既有额度/性能实验按风险复用，不以文件 hash 或测试数量代替功能验收。记忆数据库的真实隔离与应用效果仍由 P1/P5 验收。

## 顺序与分工

R8.0 → R8.1 → R8.2/R8.3 → R8.4。embedding 与 jobs 在明确公共配置接口后可独立分工，公共入口/模板和最终部署各有一个 owner；主 agent 统一检查差异、文档与 main 提交。R8 完成即接续记忆闭环，不增加通用平台建设。

## 已完成阶段索引

R0–R7 的原始方案保留在 Git 历史；以下保留阶段入口，实际结论、当时预算和限制以结果文档为准，早期串行/预算生成方案不再是当前待办。

### R0 复用准备与预算标定

公共包与配置、环境和路径探针已交付，见 [R0–R5 结果](result.md)。

### R1 将旧 embedding 服务改为跨项目共用

跨项目共享模型和请求局部生命周期已交付，见 [R0–R5 结果](result.md)。

### R2 普通重任务的 Condor 薄入口

提交、状态、等待、取消及参数桥接已交付，见 [R0–R5 结果](result.md)。

### R3 两机制并行与其他资源准入

联合 GPU 与普通资源验收已交付，见 [R0–R5 结果](result.md)。

### R4 生命周期与故障回归

作业树和共享服务隔离的实际结果见 [R0–R5 结果](result.md)。

### R5 安装与使用交付

普通 wheel 源码外验收及使用说明已交付，见 [R0–R5 结果](result.md)。

R6 通用节点容量与同卡共享见 [结果](native-condor.md)；R7 标准提交转换见 [计划](standard-submit-plan.md) 和 [结果](standard-submit-result.md)。这些历史结论保持当时条件。
