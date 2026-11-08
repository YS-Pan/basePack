# 机器部署与维护

本版支持单机 Windows、单张 NVIDIA GPU。复用现有 Python 3.13、固定 Qwen3-VL-Embedding-2B 权重与 HTCondor；模型目录含 model.lock.json 与 model/。机器配置是路径与预算的唯一维护源，随包模板由 `from basepack.setup import template` 读取，见 [项目接入](setup-project.md)。

## 包与执行账户

稳定安装普通 wheel。系统目录安装通常需要管理员终端，确认 pip 没有回落 user-site；使用 `python -s -c "import basepack; print(basepack.__file__)"` 核实际位置，并通过真实 Condor 小作业核 slot 账户能加载包、读配置/输入/权重、写结果和连接 broker。doctor 只读检查不能代替这些作业。embedding 依赖因固定预处理锁定兼容版本，见 [pyproject.toml](../pyproject.toml) 的 embedding extra；CUDA PyTorch 须适配驱动，已有环境直接复用，普通项目无需重复安装。

开发使用同一解释器的 editable 安装，源码目录须保持可读和稳定；稳定部署不需要源码仓库。项目只引用该 Python 和机器配置，不保存包目录或 PYTHONPATH。服务账户与普通作业账户可以不同，权限按实际文件和 loopback 访问核定。本机验证的服务入口由交互用户启动，普通作业为 Condor slot 低权限账户。

适配器只用机器配置中的 bin_dir/config_file，显式向 CLI 传 CONDOR_CONFIG，不依赖提交 shell 的 PATH。Windows SSPI 在受限进程中可能认证失败；本机受限 sandbox 失败、正常用户 PowerShell 成功，未因此改认证政策。保留原错误并在正常执行上下文检查，按安装版 Condor 的真实配置诊断。

## 显存与 CPU/RAM 预算

固定 `B = total_gpu_mib - embedding_gpu_mib - system_gpu_mib`。embedding 预留 E 始终保留，即使模型尚未加载也不借给普通任务；GPU 作业 H 必须不超过 B。E 包括加载、允许输入/批次、CUDA context 和缓存峰值，S 包括桌面/驱动和余量；CPU/RAM 同样先留出服务与桌面，再填写 budget.cpus/memory_mib。

2026-11-08 本机最大输入标定样例：T=16380 MiB，文本 batch4×2048 token 与 1024² 图片加文字共2048 token 的 allocator 峰约7786 MiB，整卡基线约1009 MiB、采样峰8937 MiB，进程 RSS 峰约2054 MiB。采用 E=9216 MiB、S=2048 MiB、B=5116 MiB。16 CPU/48349 MiB 的机器为 Condor 留 12 CPU/24576 MiB；初始 32768 MiB 在观察到桌面基线约20 GiB 后收紧。这是该模型、上限与机器的实测配置，采样整卡增量和 allocator reserved 都不等于精确进程显存。RAM 验收检查声明准入及排队，不把声明额度全部实际分配。

从项目入口生成派生配置：

```powershell
python -m basepack --config '<project-config>' resources budget-config
```

将返回的 config 文本保存到本机 Condor 已加载的配置片段位置；机器 TOML 是维护源，片段不单独修改。片段设置可分配 CPU/RAM，发布 BasePackGpuBudgetMiB 与 BasePackBudgetId。排空已有工作后重载 Condor，查询本机 partitionable 父 slot，核发布值、hash、TotalCpus/TotalMemory 与命令输出一致；所有任务提交前核预算发布，GPU 额外检查 H≤B。`request_gpus=1` 负责普通 GPU 作业彼此排队，不把设备总显存门槛当作 B。

本机实测 reconfig 能发布新 hash，却不会缩小已有 partitionable 父 slot 的 CPU/RAM。修改这两项后须先排空队列，再平稳重启 startd，随后核实际容量；只有 hash 更新不能放行：

```powershell
$env:CONDOR_CONFIG = '<native-condor-config>'
& '<condor-bin>/condor_reconfig.exe'
& '<condor-bin>/condor_restart.exe' -peaceful -daemon startd
& '<condor-bin>/condor_status.exe' -constraint 'PartitionableSlot =?= true' -af Name TotalCpus TotalMemory BasePackGpuBudgetMiB BasePackBudgetId
```

2026-11-08 本机实际父 slot 已核为 12 CPU、32768 MiB RAM、5116 MiB 普通 GPU 预算。其他机器按自己的标定与发布输出核值。

保留符合本机需要的 START/SUSPEND/PREEMPT 与 starter 线程策略，核最终应用环境。本机父 slot 会产生 dynamic slots，一个父 slot 不代表一次只跑一个 CPU 任务。显存粗估失准时返回原始 OOM，不切换 CPU或回收其他项目进程；重新标定前暂停新提交并排空相关工作。

## 共享服务生命周期

先在所有 Condor 作业树之外启动轻量 broker，模型在首个请求时加载：

```powershell
python -m basepack.embedding.broker --machine-config '<absolute-machine-config>'
```

这是前台进程；作为本机长期入口时可由任务计划或服务管理器启动，选择已验证账户。不要从 Condor payload 启动 broker。作业内客户端只连现有 broker，再由 broker 启动其自有模型进程；普通作业取消后共享模型继续服务其他项目。

机器 state_dir 保存 broker/worker endpoint、实例锁及 stderr。实例身份含固定模型、预处理、设备和代码版本，不含项目路径。多项目冷请求共用同一实例。worker 空闲到 idle_seconds 后卸载，broker 保留，下次请求按预留预算再启动；单请求取消/截止不退出共享服务。

升级或改模型、输入上限、预算前，暂停新请求与提交，排空相关工作，运行 `embedding stop`，确认 broker/worker 已退出，再切换包/配置并重新标定和发布预算，最后启动 broker。推理和 status 拒绝代码/配置身份不一致的旧实例；stop 按机器 marker 独立清理旧 broker，仍推荐先停再升级。服务异常时保留 stderr 和 PID，核旧进程已退出后再显式启动，不自动重试推理或重复加载。

`embedding status` 查询共享状态，`embedding stop` 是独立管理员动作；返回 stopping 只代表已请求，worker 在当前 forward 完成后退出，确认 PID 消失后才视为释放。普通客户端 close/cancel 只影响本请求。普通任务进程树由 Condor 回收；broker 持有模型 worker 的独立进程所有权，broker 异常退出时也回收其模型进程。
