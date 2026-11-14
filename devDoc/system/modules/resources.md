# 资源工具

本页描述 active 路线 [20261106-basepack](../../../experiments/20261106-basepack/README.md) 的资源模块职责与合同。客户端沿用既有 0.5.0 共享 embedding 协议；安装与升级边界见 [部署合同](../deployment.md)，资源部署、预算和验收基线见 [R9 结果](../../archive/20261107-resource-coordination/r9-result.md)。产品操作见 [资源使用](../../../experiments/20261106-basepack/docs/resources.md)，服务安装与维护见 [管理员说明](../../../experiments/20261106-basepack/docs/administrator.md)。

[project/config.py](../../../experiments/20261106-basepack/src/basepack/project/config.py) 唯一解析项目 schema 2 与机器 schema 1 配置；各功能按需读取自身节，实例数据统一在项目 `.basepack/`。0.6.2 保持既有 schema，项目使用 agent 配置时需补入 `[ai]`；更老的 schema 1 项目先用保留的 0.4.0 迁移。本模块不维护记忆索引、图或数据库。机器配置不再保留无消费者的 `[shared].state_dir`；embedding 的日志路径由 SCM/Shawl 服务定义显式指定，作业材料仍使用项目 `[jobs].jobs_dir`，不因此搬迁现有日志。

## 共享 embedding

[embedding/qwen3_vl.py](../../../experiments/20261106-basepack/src/basepack/embedding/qwen3_vl.py) 通过 Sentence Transformers 6.2.0 加载本地 Qwen3-VL-Embedding-2B，复用其图文预处理、last-token pooling、归一化和请求内批处理。必要的薄适配负责输入限制、CUDA 分配器预算，以及在 Transformer forward 前按实际 attention_mask 拒绝超长输入；截断被显式关闭，图片原件经验证后交给库处理。

`resolve_device(auto)` 根据 Torch 的可用性优先选 CUDA，否则 CPU；显式设备保持用户选择。CPU 不访问 CUDA 或 nvidia-smi，CUDA 才要求正显存预算并设置分配器上限。LitServe 按已选设备使用 cpu/devices=1 或 cuda/设备索引；`/info` 的 model 提供 device 和 dtype，旧服务无需新增字段即可继续兼容。

[identity.py](../../../experiments/20261106-basepack/src/basepack/embedding/identity.py) 维护 `embedding_identity`：模型 revision/文件清单、Sentence Transformers 版本、FP16、指令、图像缩放和 pooling/归一化合同共同决定语义。服务地址、模型存放路径、队列期限、请求批次、线程和预算不改变此标识。0.5.0 引入新的身份，0.6.1 保持兼容。[记忆向量模块](../../../experiments/20261106-basepack/src/basepack/memory/vectors.py) 已按身份与输入版本判断复用、过滤不兼容向量，并通过 `memory embed` 重建。

0.7.0 沿用该身份算法，CPU/CUDA 同模型与精度直接复用索引；正常浮点差异和近同分换序按语义等价处理。CPU/CUDA 依赖分别由 `embedding-cpu`、`embedding-cuda` extra 选择；跨设备实际证据在[本轮整改](../../archive/20261110-rectification/progress.md)维护。

首次准备使用 [短脚本](../../../experiments/20261106-basepack/examples/prepare_embedding_model.py) 调用官方 hf 下载并验证固定 revision，再从实际文件生成 model.lock.json；模型保存为 model_root/model/，清单记录模型名、revision 及文件相对路径、字节数和 SHA256。该步骤只在准备时运行。已有服务继续保留原锁；重建清单可能改变身份，调用项目据实际身份重建向量。机器模板显存预算 0 是待标定占位，首次启动前按机器测量填写正预算并协调 Condor 普通池。

[service.py](../../../experiments/20261106-basepack/src/basepack/embedding/service.py) 只适配 LitAPI：setup 加载一份常驻模型，predict 调用编码器。LitServe 0.2.19 提供 HTTP、队列、健康检查和 worker 管理；单设备、单推理 worker、单 API 接入线程，跨请求批次为 1。请求内批次由模型库处理。`restart_workers=True` 负责重建失败 worker，失败请求不自动重投。

编码器把已知输入合同错误标为 `EmbeddingInputError`，服务将其映射为 HTTP 422；其它模型故障保留原异常。token 超限仍由 forward 前的实际 attention_mask 拒绝；只在该失败路径重复预处理，给出原请求顺序的 token 数和超限索引，避免 Sentence Transformers 内部按长度重排后无法定位。无原文截断或推理重投。此错误呈现属于当前源码，旧服务需按管理员升级流程安装才生效。

Shawl 1.9.0 由 Windows 服务管理器启动，在 Condor 作业树之外拥有整个服务进程树。选定配置为 `--no-restart --kill-process-tree --stop-timeout 3000`：主进程或 Shawl 故障使服务停止，管理员手动重启；管理员停止后保持停止。模型常驻，不再由客户端请求或空闲时限管理其存活。

[EmbeddingClient](../../../experiments/20261106-basepack/src/basepack/embedding/client.py) 明确接收 MachineConfig，将输入发送至配置 endpoint 的原生 `/predict`，结果包含向量、worker PID 和语义身份。客户端 timeout 只限制等待；LitServe 的 queue_timeout 只判断排队请求是否过期，两者都不打断已经开始的推理，也不停止共享服务。HTTP 错误保留原异常、可读响应流，并附最多 4096 字节的正文；候选编码另附请求输入索引与成员 key、路径、范围。旧服务的通用 500 仍须结合服务原日志定位，不能仅靠客户端恢复被框架隐藏的内部错误。

机器管理独立于项目：`embedding --machine-config <file> status` 读取 `/health` 和 `/info`，后者提供模型身份和依赖版本；`stop` 调用 `sc.exe stop`。停止请求被接受不等于进程已经回收，完成状态由 Windows 服务状态和实际进程检查确认。安装、日志位置和停止方法见管理员说明。

## 普通重任务

[jobs/](../../../experiments/20261106-basepack/src/basepack/jobs) 公开 JobSpec 与 CondorClient。client 编排 run/submit/status/wait/cancel，submit 集中字段编码、局部规范化和提交材料。payload 只保存一份 spec，薄 UTF-8 worker 从中读取 executable/arguments；参数与日志留在项目 `[jobs].jobs_dir`。提交响应不确定时按唯一提交标识查询，避免重复提交。

HTCondor 是普通容量与策略权威。`capacity` 只观察实际父 slot 的总量和剩余量：标准 CPU/RAM/GPU 映射为 cpus/memory_mib/gpus，纯 CPU 节点未发布 GPU 字段时为 0；其他 MachineResources 在总量和剩余均发布时按原名和单位展示。客户端保留请求正值与输出盘空间检查，将匹配、资源准入和排队交给 Condor；项目配置不镜像普通额度。

容量与队列查询的认证边界、正常用户上下文复核、实时 startd 配额及设备/进程核对见[运行环境](../environment.md)；日常配置与诊断见[管理员说明](../../../experiments/20261106-basepack/docs/administrator.md#安装与执行账户)及其[容量与策略](../../../experiments/20261106-basepack/docs/administrator.md#condor-容量与策略)。

GPU JobSpec 只生成官方 `request_gpus = 1` 和 `gpus_minimum_memory = <峰值> MB`。schedd 的 JOB_TRANSFORM 根据站点策略生成内部显存申请并追加匹配条件，保留原 Requirements、RequireGPUs 和硬件筛选。CPU 作业不做 GPU 转换。本站省略原生显存声明时预订全池；非法、超池和多 GPU 申请由提交规则拒绝，规则对所有标准提交端一致，详见管理员说明。

背景服务与普通作业共享物理 GPU，以固定预留协调。共享令牌和显存记账不提供显存硬隔离，应用须按申报控制实际峰值；WDDM 下单进程 CUDA free 不能代表全卡余量，动态 free 不参与准入。

Windows Condor 参数转换会丢失空参数，因此 worker 从 UTF-8 JSON 读取完整参数数组，再由系统进程 API 启动应用；它和应用后代属于 Condor 作业树，继承最终 starter 环境并保留 GPU 可见性，stdout/stderr 由 Condor 接管。

提交材料使用 Condor 的 `periodic_remove` 和 `allowed_execute_duration` 管理排队与执行时限；策略有周期及状态转换延迟。wait 只观察，观察到期保留作业；run 提交一次后按 queue_timeout + run_timeout + 30 秒观察，仍未终态时返回 observation_expired，不撤销。原生 held 单独返回；仅当前 held 或从 held 删除的 HoldReasonCode 46/47 标识执行超时，其它终态原因保留原文与结构字段，timeout 为 null。时间差保留负值，缺失时间保持 null。

cancel 调用 condor_rm，`cancellation_requested` 与随后观察到的终态分开报告；失败保留命令错误。Condor 管理作业停止与清理，客户端不检查进程族。jobs CLI 的 run 根据业务成功设置退出码；提交反查失败时保留原提交错误并附反查错误链；调用者仍需检查有意义的业务结果。

## 验证入口

当前资源查询边界、正常用户 CPU 作业与 GPU/共享 embedding 并存复核见[运行环境](../environment.md)及其原证；GPU 并存的证据范围以该页说明为准。功能结果按实际业务结果核验，测试数量不替代验收。运行原证按批次选留于根 `artifacts/runs/`；历史 R8 的取消、空闲退出与私有 RPC 证据只适用于当时实现，见 [R8 结果](../../archive/20261107-resource-coordination/maintenance-result.md)。
