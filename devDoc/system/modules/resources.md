# 资源工具

本页描述 active 路线 [20261106-basepack](../../../experiments/20261106-basepack/README.md) 的资源模块职责与合同。当前 0.6.2 客户端兼容已验的 0.5.0 共享 embedding 服务；安装与升级边界见 [部署合同](../deployment.md)，资源部署、预算和验收基线见 [R9 结果](../../archive/20261107-resource-coordination/r9-result.md)。产品操作见 [资源使用](../../../experiments/20261106-basepack/docs/resources.md)，服务安装与维护见 [管理员说明](../../../experiments/20261106-basepack/docs/administrator.md)。

[project/config.py](../../../experiments/20261106-basepack/src/basepack/project/config.py) 唯一解析项目 schema 2 与机器 schema 1 配置；各功能按需读取自身节，实例数据统一在项目 `.basepack/`。0.6.2 保持既有 schema，项目使用 agent 配置时需补入 `[ai]`；更老的 schema 1 项目先用保留的 0.4.0 迁移。本模块不维护记忆索引、图或数据库。

## 共享 embedding

[embedding/qwen3_vl.py](../../../experiments/20261106-basepack/src/basepack/embedding/qwen3_vl.py) 通过 Sentence Transformers 6.2.0 加载本地 Qwen3-VL-Embedding-2B，复用其图文预处理、last-token pooling、归一化和请求内批处理。必要的薄适配负责输入限制、CUDA 分配器预算，以及在 Transformer forward 前按实际 attention_mask 拒绝超长输入；截断被显式关闭，图片原件经验证后交给库处理。

[identity.py](../../../experiments/20261106-basepack/src/basepack/embedding/identity.py) 维护 `embedding_identity`：模型 revision/文件清单、Sentence Transformers 版本、FP16、指令、图像缩放和 pooling/归一化合同共同决定语义。服务地址、模型存放路径、队列期限、请求批次、线程和预算不改变此标识。0.5.0 引入新的身份，0.6.1 保持兼容。[记忆向量模块](../../../experiments/20261106-basepack/src/basepack/memory/vectors.py) 已按身份与输入版本判断复用、过滤不兼容向量，并通过 `memory embed` 重建。

[service.py](../../../experiments/20261106-basepack/src/basepack/embedding/service.py) 只适配 LitAPI：setup 加载一份常驻模型，predict 调用编码器。LitServe 0.2.19 提供 HTTP、队列、健康检查和 worker 管理；单设备、单推理 worker、单 API 接入线程，跨请求批次为 1。请求内批次由模型库处理。`restart_workers=True` 负责重建失败 worker，失败请求不自动重投。

Shawl 1.9.0 由 Windows 服务管理器启动，在 Condor 作业树之外拥有整个服务进程树。选定配置为 `--no-restart --kill-process-tree --stop-timeout 3000`：主进程或 Shawl 故障使服务停止，管理员手动重启；管理员停止后保持停止。模型常驻，不再由客户端请求或空闲时限管理其存活。

[EmbeddingClient](../../../experiments/20261106-basepack/src/basepack/embedding/client.py) 明确接收 MachineConfig，将输入发送至配置 endpoint 的原生 `/predict`，结果包含向量、worker PID 和语义身份。客户端 timeout 只限制等待；LitServe 的 queue_timeout 只判断排队请求是否过期，两者都不打断已经开始的推理，也不停止共享服务。传输和推理错误沿框架原始信息及服务日志定位。

机器管理独立于项目：`embedding --machine-config <file> status` 读取 `/health` 和 `/info`，后者提供模型身份和依赖版本；`stop` 调用 `sc.exe stop`。停止请求被接受不等于进程已经回收，完成状态由 Windows 服务状态和实际进程检查确认。安装、日志位置和停止方法见管理员说明。

## 普通重任务

[jobs/](../../../experiments/20261106-basepack/src/basepack/jobs) 公开 JobSpec 与 CondorClient。client 编排 run/submit/status/wait/cancel，submit 集中字段编码、局部规范化和提交材料；psutil 只观察本任务已知 PID 及其子树，回收确认不逐项读取全系统进程属性。payload 只保存一份 spec，薄 UTF-8 worker 从中读取 executable/arguments；参数与日志留在项目 `[jobs].jobs_dir`。提交响应不确定时按唯一提交标识查询，避免重复提交。

HTCondor 是普通容量与策略权威。`capacity` 读取实际父 slot 的总量和剩余量：标准 CPU/RAM/GPU 映射为 cpus/memory_mib/gpus；其他 MachineResources 在总量和剩余均发布时按原名和单位展示。客户端按实际 CPU/RAM 总量检查请求能否容纳，当前剩余不足由 Condor 排队；项目配置不镜像普通额度。

容量与队列查询的认证边界、正常用户上下文复核、实时 startd 配额及设备/进程核对见[管理员说明](../../../experiments/20261106-basepack/docs/administrator.md#安装与执行账户)及其[容量与策略](../../../experiments/20261106-basepack/docs/administrator.md#condor-容量与策略)。

GPU JobSpec 只生成官方 `request_gpus = 1` 和 `gpus_minimum_memory = <峰值> MB`。schedd 的 JOB_TRANSFORM 根据站点策略生成内部显存申请并追加匹配条件，保留原 Requirements、RequireGPUs 和硬件筛选。CPU 作业不做 GPU 转换。本站省略原生显存声明时预订全池；非法、超池和多 GPU 申请由提交规则拒绝，规则对所有标准提交端一致，详见管理员说明。

背景服务与普通作业共享物理 GPU，以固定预留协调。共享令牌和显存记账不提供显存硬隔离，应用须按申报控制实际峰值；WDDM 下单进程 CUDA free 不能代表全卡余量，动态 free 不参与准入。

Windows Condor 参数转换会丢失空参数，因此 worker 从 UTF-8 JSON 读取完整参数数组，再由系统进程 API 启动应用；它和应用后代属于 Condor 作业树，继承最终 starter 环境并保留 GPU 可见性，stdout/stderr 由 Condor 接管。

run 管理排队与执行时限，并写入 Condor 原生策略；wait 只观察，观察过期保留作业。取消和完成后的回收确认结合原生历史与已知任务进程消失，分别报告终态和 cleanup_confirmed；失败保留原错误。jobs CLI 负责成功及回收退出码，根 CLI 只组合命令和输出。调用者仍需检查有意义的业务结果。

## 验证入口

当前资源查询边界、正常用户 CPU 作业与 GPU/共享 embedding 并存复核见[运行环境](../environment.md)及其原证；GPU 并存的证据范围以该页说明为准。功能结果和进程回收按实际业务结果核验，测试数量不替代验收。运行原证按批次选留于根 `artifacts/runs/`；历史 R8 的取消、空闲退出与私有 RPC 证据只适用于当时实现，见 [R8 结果](../../archive/20261107-resource-coordination/maintenance-result.md)。
