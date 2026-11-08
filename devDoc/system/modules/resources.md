# 资源工具

公共配置由 [project/config.py](../../../src/basepack/project/config.py) 解析。ProjectConfig 只加载公共绑定，各功能按需读取自身配置；MachineConfig.path 是机器配置位置的唯一来源。产品调用见 [资源使用](../../../docs/resources.md)，机器维护见 [管理员说明](../../../docs/administrator.md)。本模块不维护记忆索引、图或数据库。

## 独立 embedding

[embedding](../../../src/basepack/embedding/) 从旧 VL runtime 提取固定模型、严格图文预处理、归一化和内部批处理，使用本地权重及已有系统 Python。模型语义身份包含固定权重清单、FP16、预处理版本与输入上限；设备与代码身份进一步决定运行实例。

机器级 broker 必须在 Condor 作业树之外启动。创建锁保证一个 broker；broker 按需创建并拥有一个模型 worker，机器共享目录保存 endpoint、锁与 stderr，不保存项目资料或向量。项目客户端只连接，多个项目的批量/查询请求进入同一内存队列。正常关闭客户端只取消自身请求。

worker 在线程接入层处理状态、取消与截止，单线程模型循环执行 forward。截止覆盖排队、加载与推理等待；在算 forward 可完成，但结果丢弃，后续内部批次不再执行。空闲边界卸载；broker 崩溃由 Windows Job Object 回收其 worker。异常原始类型、信息与 traceback 返回调用方，不自动重试推理。

机器 TOML 的 `[embedding].gpu_memory_mib` 是模型分配器额度，也参与实例身份；独立 embedding 不依赖 Condor。修改运行代码或机器模型配置前，先用旧安装停止并确认旧服务退出；实例代码身份不一致时直接拒绝旧 endpoint。模型进程启动/失败与普通作业的生命周期独立。

## 普通重任务

[resources](../../../src/basepack/resources/) 提供 JobSpec 与 run/submit/status/wait/cancel。任务参数和日志留在项目 jobs_dir；队列、事件和历史由 Condor 维护。每次提交使用唯一标识，响应不确定时按标识查询原生队列/历史，不重复提交。

普通作业容量与策略由 HTCondor 维护，basePack 是标准提交客户端。`capacity` 读取实际父 slot 的总量和剩余量：标准 CPU/RAM/GPU 对应 `cpus/memory_mib/gpus`，其余 `MachineResources` 仅在总量和剩余数量均有发布时按原名、原生单位展示。客户端只按 `TotalSlotCpus/TotalSlotMemory` 判断 CPU/RAM 能否容纳，GPU 与内部额度的拒绝和排队交给 Condor；当前剩余不足不触发客户端拒绝。项目 TOML 不镜像普通额度，也没有专属预算发布或 hash 匹配。

GPU JobSpec 的 `gpu_memory_mib` 只生成官方 `request_gpus = 1` 与 `gpus_minimum_memory = <峰值> MB`。提交 schedd 的原生 JOB_TRANSFORM 按站点配置生成内部显存申请并追加资源匹配门槛，保留原 Requirements、RequireGPUs 和硬件筛选含义；资源名和数值不进入客户端实现。CPU 作业不做 GPU 转换。本站省略原生显存声明时预订全池，非法、超池和多 GPU 申请由提交规则拒绝，用户错误引用官方参数名。规则对所有标准提交端一致，配置见 [管理员说明](../../../docs/administrator.md)。

背景与普通作业共享物理 GPU，通过管理员固定预留协调；本机 GPU 数量代表同卡共享令牌，应用按声明限制实际峰值。GPU 共享和资源记账不提供显存硬隔离，也不承诺更高吞吐；部署及真实联合验收状态见下方进度入口。

自身 PyTorch allocator 指标与 CUDA device-view 指标分开命名；WDDM 下 CUDA free 不能代表全卡其他进程占用。外部 nvidia-smi 时间线才用于本版全卡峰值证据，动态 free 不参与准入。

Windows submit 的字段分别编码，文件采用本机原生编码。实际探针表明 Condor 参数转换会丢失空参数，因此随包薄 worker 从 UTF-8 JSON 读取应用参数数组，再用系统进程 API 启动应用。worker 继承最终 starter 环境并保留 GPU 可见性，stdout/stderr 由 Condor 接管；它和应用后代均属于原生作业树。

run 执行有界等待，排队/执行时限同时写入 Condor 原生策略；wait 的时限只结束观察。取消结果分别报告终态与 cleanup_confirmed，确认包含原生历史及已知本任务进程消失；撤销或确认失败保留原错误。完成退出码和显式回传产物只是机械检查，调用者仍核业务结果。

## 证据

实际设施、预算和功能验收统一记录在 [资源进度](../../tasks/20261107-resource-coordination/progress.md)。本机详细 JSON、时间线和日志位于忽略目录 `artifacts/`，测试覆盖请求取消竞态、实例启动竞态及字段/进程处理缺陷，不替代真实 GPU/Condor 验收。
