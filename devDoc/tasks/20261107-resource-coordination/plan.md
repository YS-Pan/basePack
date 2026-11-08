# 公共包与资源协调维护计划

更新：2026 年 11 月 9 日。本文维护 R9 复用优先路线，并保留已交付 R8 的设计与验收条件。阶段实施、部署及验收的实际状态只维护在 [进度](progress.md)，源码/实例布局及安装迁移合同见 [部署合同](../../system/deployment.md)。

目标以 [项目纲领](../../project-charter.md) 和本轮用户指令为准，共性选择标准见 [复用优先](../20261106-rebuild/plan.md#复用优先)。记忆 P0/P1 可使用现有公共能力并行推进，不等待 R9 完成。

## R9 复用优先的资源实现

当前实现与后续 R9 改动统一在 [20261106-basepack 工程](../../../experiments/20261106-basepack/README.md)；源码、依赖声明、测试、样例和产品说明以实验根为入口，计划、进度与结果仍在根 devDoc 维护。临时验证进入根 tmp，需选留原证进入 artifacts/runs；本次布局迁移不替代 R9 的功能验证。

### 主线与行为取舍

用户确认维持 Sentence Transformers＋LitServe＋Shawl：分别负责模型编码、请求与推理 worker 管理、Windows 服务托管。先验证这一路线，再删除被替代的实现；备选仅在出现具体阻碍时重评，不增加协议或框架比较阶段。调查依据与适用边界见 [现成实现调查](research/reuse-options.md)。

| 内容 | R9 取舍 |
| --- | --- |
| 模型作用域 | 保持机器级单份模型、多项目共用；单设备、单推理 worker，与 HTTP 接入数分开配置，服务在 Condor 作业树外 |
| 生命周期 | 在 LitAPI.setup 加载模型并常驻，predict 调用 Sentence Transformers.encode；空闲整进程退出不再是强制条件 |
| 批处理 | 请求内批次交给 Sentence Transformers；首版 LitAPI.max_batch_size=1，跨请求动态合批在实际吞吐瓶颈出现后启用并测延迟、峰值与结果拆分，不作为首版前置 |
| 取消与截止 | 调用方有界等待并明确报告超时；LitServe 排队 timeout 与客户端等待期限分开配置，均不视为中断已开始的推理；单请求不停止共享服务 |
| 向量语义 | 输入原件不静默截断或丢弃图片；模型、指令、预处理与 pooling 身份可追溯，数值行为改变时明确新身份与索引兼容 |
| 服务协议与诊断 | 采用框架原生 endpoint、错误、健康检查与日志；调用方同批切换，退役旧 RPC、逐请求回执、tokens_only 和逐文件代码指纹，只保留必要的版本/配置诊断 |
| 调度与数据 | 项目局部数据、Condor 普通调度和现有站点政策继续各自维护；本批不更换调度系统或建立动态显存调度层 |

常驻模型不会自动减少当前 Condor 普通池：本站背景预留与普通池额度本就固定。R9 用真实输入峰值核仍能并存，额度调整只由测量支持。错误保留原始信息；重启由服务配置明确安排，推理请求不因丢失响应而盲目重投。

### R9.0 官方模型库小试

复用现有 Qwen3-VL-Embedding-2B revision 与本地权重，安装选定的已发布 Sentence Transformers 版本；用现成图文预处理、模型加载和 pooling 替代重复实现。显式关闭截断并核实际 token；核 FP16 模型与现有 FP32 归一化差异。保留必要的预算设置和输入检查，诊断字段按用途删减。

**完成：** 断网可加载；文本、图片、图文得到有效 2048 维归一化向量，超长输入明确失败；对同一小组资料比较旧新向量与检索排序并决定语义身份。记录适配代码和依赖差异，不要求浮点逐位相同，不下载第二份权重。

### R9.1 现成服务与 Windows 托管小试

用薄 LitAPI 接入 R9.0，复用 LitServe 的 HTTP、队列、健康检查及模型 worker 管理；显式设置单设备、workers_per_device=1、num_api_servers=1。Shawl 负责 Windows 服务启动、停止、退出策略及日志；直接托管新服务，不再包一层旧 supervisor。模型 worker 死亡后的处置使用选定版本的原生配置，与 Shawl 的服务退出重启分开；不自动重投失败请求。若实际依赖冲突，使用 uv 准备独立共享服务环境，项目仍不保存环境或代码副本。

**完成：** 两个源码外项目共用一份模型；客户端超时不影响另一项目，排队期限和客户端等待按各自定义生效；worker 死亡按选定策略报告错误或重建。正常停止、主进程或 Shawl 异常退出在实际账户下核全部辅助进程、模型和显存回收，管理员停止后保持停止，服务重启窗口有明确有界结果。与一项普通 GPU 作业真实并存，记录峰值和结果。Windows 停机已有上游问题线索，见调查；按选定发行版复核并实测，不为复制旧取消或空闲状态机扩写框架。

### R9.2 删除重复实现与固定依赖

将公开客户端和机器管理改为所选软件的薄调用；删除被替代的模型子类、HTTP/队列、supervisor、双端点登记及进程所有权代码，保留仍有用途的向量身份与项目接入。先核实际调用方，明确改名或移除的接口，不保留长期双实现。

通用 TOML 写出用 Tomli-W；进程观察优先 psutil，若仍需少量 Windows Job Object 包装则用 pywin32。仅在净减少维护代码时引入，不叠加 CLI/配置框架。用 uv 记录实际验收版本和 CUDA 发行来源，不直接同步或清理现有共享系统环境；HTCondor CLI 与 UTF-8 作业桥保持，Python bindings 待真实兼容需求再评。

依赖声明与锁使用原生工具维护，交付环境准备命令和服务定义，不再维护第二份私有依赖清单。模型接入采用公开接口；残留补丁就地注明上游依据与删除条件，后续按 [维护简化](../20261106-rebuild/plan.md#后续维护的简化) 在依赖升级时复查。

**完成：** 记录非空源码、必要适配、配置与运维步骤的前后差异，相关测试按新合同更新；本次涉及的重复分支确已删除。依赖环境可按记录准备，权重内容在部署时核一次，不在每次请求全量扫描。

### R9.3 一次交付与接续

核实际调用方与在途请求/作业，用旧入口停止旧服务；准备新 wheel、依赖与服务配置、升级映射及可恢复记录后一次切换。更新使用/管理员说明、resources skill、示例、系统说明和部署合同，产品文档准确说明常驻、观察超时和停止服务的行为。

保留同一组公开入口小样例供依赖升级复用，退役旧内部协议对应的失用测试。交付说明给出原生安装、停止、升级与卸载方式；一次性迁移按确认的支持范围退役，不让历史安装规则进入每次资源调用。

**完成：** 普通安装从源码外两项目完成图文、CPU/GPU、共享服务隔离、日志及进程回收；原有项目配置和业务数据保留，服务升级/停止与回退可操作。既有 Condor 验收按受影响范围复用，不重复全套资源标定。记忆 P2 取得稳定的公开 embedding 接口与语义身份，不耦合 LitServe/Shawl 内部对象。

R9.0 → R9.1 → R9.2 → R9.3；模型和服务先小试、再按实际需要合并为实现批次，统一检查与 main 提交。R9 的完成依据是减少维护量后仍能完成实际流程，不以引入库的数量或测试数量验收。

### 后续触发时再评

- HTCondor 发布可与选定 Windows Python 匹配的 bindings，或现有 CLI 胶水成为实际维护负担时，验证原生 API 能否净减少代码；保留仍有必要的参数与作业结果合同。
- 实际环境转为 Linux/WSL，或代表性请求暴露吞吐瓶颈时，再核 vLLM/Infinity 等现成本地服务；当前不为候选先迁移平台或准备多后端框架。依据沿 [现成实现调查](research/reuse-options.md) 回查并核当时版本。

## R8 已交付边界

以下记录 0.4.0 的设计和原验收条件，供回查与升级使用；R9 按上节取舍实施，不把这些内部机制逐项复制成新库适配要求。

- 项目知识、索引、输入引用和作业材料属于各自项目；系统 Python、模型、机器配置和服务状态共享，Condor 独立安装。
- embedding 由作业树外轻量启动者拥有一个模型 worker；客户端直接请求 worker。worker 按需加载、空闲整进程退出，请求取消不杀共享模型，Windows Job Object 保证所有权。
- Condor 是普通作业的容量、队列、终态及 GPU 策略权威。作业客户端只生成标准申请、观察状态和确认回收；embedding 与作业模块相互独立。
- 保留延迟导入模型依赖、原始错误、UTF-8 参数 worker、提交不确定时只查询不重投、成功空查询处理和必要故障回归。CPU/RAM 预检只读实际总量；原生时限与 run 的交互时限均保留，依据见 [历史验收](result.md#预算修复与边界)。
- 当前统一 wheel 与同代代码/配置校验继续使用。先做职责和配置解耦；独立客户端发行版、跨版本服务兼容、通用后端/插件和统一进程框架留待真实需求，不扩大本批。

## R8 设计决定

### 命名与公共接口

以下为 0.3.0 到 0.4.0 的接口映射；完整源码结构与迁移方式见部署合同。

| 0.3.0 名称 | 0.4.0 名称 | 说明 |
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

依次完成 R8.0 → R8.1 → R8.2 → R8.3 → R8.4，每阶段检查并提交后进入下一阶段。稳定安装与实例迁移集中在 R8.4，一次完成公开接口切换；以下定义各阶段的工作与验收条件，实际结论见进度。

### R8.0 修复已复现缺陷

- submit 使用局部规范化副本，保持调用者 JobSpec 不变；回归同一相对 cwd 的 spec 在两个项目复用，以及提交失败后对象未改变。[实现](../../../experiments/20261106-basepack/src/basepack/jobs/submit.py)
- 在客户端锁内先拒绝重复活动 request_id，再登记状态；用假 RPC 验证第二个同 ID 明确失败，首请求的结果、取消和清理正常，不同 ID 并发不受影响。[实现](../../../experiments/20261106-basepack/src/basepack/embedding/client.py)

两项状态缺陷使用内存替身保留回归，不以启动模型代替状态逻辑验证。

### R8.1 项目接入源码与实例目录

按部署合同归组 project/，同步轻量配置作用域、模板读取、package-data、所有导入和包根诊断。新实例统一生成 .basepack/config.toml 和 instructions.md，按需创建局部数据目录；根只保留宿主短指针与 Git 忽略规则。

**完成条件：** 配置/模板回归通过；包根和模板定位正确；无 memory 或 Condor 节的 embedding 配置仍可按自身合同使用；任意 cwd、深层配置和中文/空格路径正确解析，原业务指令保留。

### R8.2 embedding 职责与身份

拆分 transport/registry/identity，收紧 client/admin 边界，实施 supervisor、模型类和进程所有权命名，固定身份合同及启动时身份。机器管理命令直接读取机器配置，旧实例 status/stop 仍可诊断与关闭。

**完成条件：** 模型实现不依赖传输/登记；同代与错代检查、管理员停止旧实例、共享单 worker、取消/截止隔离、冷启动取消、空闲退出及崩溃回收相关回归通过。向量语义标识不因纯运行设置变化而改变，语义版本变化能够被识别。

### R8.3 作业职责与命名

迁移 jobs/CondorClient、CLI jobs、项目 [jobs] 节及 worker 模块入口，拆出 submit/_processes，消除重复 payload 和回执读取。明确 wait 只观察，run 管理作业时限；保留原生时限、查询、取消和清理确认行为。

**完成条件：** spec 不变性、payload 单一来源、复杂 argv/空参数、应用失败、资源预检、提交响应不确定、成功空查询、状态与回收回归通过。标准 GPU 字段及 Condor 站点策略不变，不重标定额度或改写服务器规则。

### R8.4 一次性迁移与普通 wheel 交付

按部署合同准备 wheel、配置映射和交付说明，核实际调用方，排空旧作业并用旧安装停止共享服务。普通安装后，通过 `migrate --from-config <old-config>` 显式迁移项目 schema、配置路径和宿主指针，再统一切换 CLI/API/模块入口并恢复运行。同步 README、使用/管理员文档、示例、相关 skills、系统说明及结果记录，清除本批失用实现和模板。

**完成条件：** 普通 wheel 源码外两项目初始化、旧配置迁移、项目移动和新检出重建通过；所有模板可从安装包读取，轻量命令不加载模型依赖。用一次真实图文 embedding 与 CPU/GPU 作业核结果、并存、取消、另一项目服务存活、日志和资源归还。复验受影响的生命周期，既有额度/性能实验按风险复用，不以文件 hash 或测试数量代替功能验收。记忆数据库的真实隔离与应用效果仍由 P1/P5 验收。

## R8 顺序与分工

R8 当时按 R8.0 → R8.1 → R8.2 → R8.3 → R8.4 逐阶段完成；公共入口/模板和最终部署各有一个 owner，主 agent 统一检查差异、文档与 main 提交。后续沿 R9 和记忆计划接续。

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
