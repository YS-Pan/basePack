# 资源工具

公共配置由 [config.py](../../../src/basepack/config.py) 解析，产品调用见 [资源使用](../../../docs/resources.md)，机器维护见 [管理员说明](../../../docs/administrator.md)。本模块不维护记忆索引、图或数据库。

## 独立 embedding

[embedding](../../../src/basepack/embedding/) 从旧 VL runtime 提取固定模型、严格图文预处理、归一化和内部批处理，使用本地权重及已有系统 Python。模型语义身份包含固定权重清单、FP16、预处理版本与输入上限；设备与代码身份进一步决定运行实例。

机器级 broker 必须在 Condor 作业树之外启动。创建锁保证一个 broker；broker 按需创建并拥有一个模型 worker，机器共享目录保存 endpoint、锁与 stderr，不保存项目资料或向量。项目客户端只连接，多个项目的批量/查询请求进入同一内存队列。正常关闭客户端只取消自身请求。

worker 在线程接入层处理状态、取消与截止，单线程模型循环执行 forward。截止覆盖排队、加载与推理等待；在算 forward 可完成，但结果丢弃，后续内部批次不再执行。空闲边界卸载；broker 崩溃由 Windows Job Object 回收其 worker。异常原始类型、信息与 traceback 返回调用方，不自动重试推理。

修改运行代码或机器模型配置前，先用旧安装停止并确认旧服务退出；实例代码身份不一致时直接拒绝旧 endpoint。模型进程启动/失败与普通作业的生命周期独立。

## 普通重任务

[resources](../../../src/basepack/resources/) 提供 JobSpec 与 run/submit/status/wait/cancel。任务参数和日志留在项目 jobs_dir；队列、事件和历史由 Condor 维护。每次提交使用唯一标识，响应不确定时按标识查询原生队列/历史，不重复提交。

机器 TOML 是资源预留的唯一来源，budget-config 生成 Condor 片段。所有提交核实际父 slot 的预算版本、显存预算及 CPU/RAM 总量；GPU 还要求声明 H 不超 B，requirements 固定本机和预算版本，request_gpus=1 使普通 GPU 任务彼此排队。embedding 的 E 始终保留，两链共享显存靠预算协作，不依赖整卡排他锁。

Windows submit 的字段分别编码，文件采用本机原生编码。实际探针表明 Condor 参数转换会丢失空参数，因此随包薄 worker 从 UTF-8 JSON 读取应用参数数组，再用系统进程 API 启动应用。worker 继承最终 starter 环境并保留 GPU 可见性，stdout/stderr 由 Condor 接管；它和应用后代均属于原生作业树。

run 执行有界等待，排队/执行时限同时写入 Condor 原生策略；wait 的时限只结束观察。取消结果分别报告终态与 cleanup_confirmed，确认包含原生历史及已知本任务进程消失；撤销或确认失败保留原错误。完成退出码和显式回传产物只是机械检查，调用者仍核业务结果。

## 证据

实际设施、预算和功能验收统一记录在 [资源进度](../../tasks/20261107-resource-coordination/progress.md)。本机详细 JSON、时间线和日志位于忽略目录 `artifacts/`，测试覆盖请求取消竞态、实例启动竞态及字段/进程处理缺陷，不替代真实 GPU/Condor 验收。
