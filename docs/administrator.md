# 机器部署与维护

0.3.0 的部署范围为单机 Windows、单张 NVIDIA GPU。复用现有 Python 3.13、固定 Qwen3-VL-Embedding-2B 权重与 HTCondor；模型目录含 model.lock.json 与 model/。机器 TOML 维护路径及 embedding 设置，HTCondor 维护普通容量和提交策略。随包机器模板由 `from basepack.setup import template` 读取，见 [项目接入](setup-project.md)。实际部署与验收状态统一见 [资源进度](../devDoc/tasks/20261107-resource-coordination/progress.md)。

## 包与执行账户

稳定安装普通 wheel。系统目录安装通常需要管理员终端，确认 pip 没有回落 user-site；使用 `python -s -c "import basepack; print(basepack.__file__)"` 核实际位置，并通过真实 Condor 小作业核 slot 账户能加载包、读配置/输入/权重、写结果和连接 broker。doctor 只读检查不能代替这些作业。embedding 依赖因固定预处理锁定兼容版本，见 [pyproject.toml](../pyproject.toml) 的 embedding extra；CUDA PyTorch 须适配驱动，已有环境直接复用，普通项目无需重复安装。

开发使用同一解释器的 editable 安装，源码目录须保持可读和稳定；稳定部署不需要源码仓库。项目只引用该 Python 和机器配置，不保存包目录或 PYTHONPATH。服务账户与普通作业账户可以不同，权限按实际文件和 loopback 访问核定。本机验证的服务入口由交互用户启动，普通作业为 Condor slot 低权限账户。

适配器只用机器配置中的 bin_dir/config_file，显式向 CLI 传 CONDOR_CONFIG，不依赖提交 shell 的 PATH。Windows SSPI 在受限进程中可能认证失败；本机受限 sandbox 失败、正常用户 PowerShell 成功，未因此改认证政策。保留原错误并在正常执行上下文检查，按安装版 Condor 的真实配置诊断。

## 通用 HTCondor 节点容量

普通作业的容量和站点策略只由 Condor 管理，运行时无需调用或导入 basePack。本机入口为 `C:/condor/condor_config`，加载以下两份配置；完整规则以样例文件为维护源：

| 配置 | 维护职责 |
| --- | --- |
| [60_resources.conf](../examples/condor/60_resources.conf) | 执行节点 CPU/RAM、同卡共享名额、内部显存资源及 START 条件 |
| [70_job_transforms.conf](../examples/condor/70_job_transforms.conf) | 提交节点 schedd 的原生 JOB_TRANSFORM 和提交拒绝规则 |

本机安装位置分别是 `C:/condor/config/60_resources.conf` 与 `C:/condor/config/70_job_transforms.conf`。保留管理员已有的 `JOB_TRANSFORM_NAMES`、`SUBMIT_REQUIREMENT_NAMES` 及原有匹配策略，按样例追加本站规则。额度只在 60 配置定义，70 引用该值；不要在提交端镜像额度。

本机按用户指定为背景程序合计保留 9 GiB，剩余 `16380 - 9216 = 7164 MiB` 交给普通 GPU 作业，最多 4 个普通 GPU 作业共享同卡；背景包括 embedding 与桌面，不再重复扣除原先的 2 GiB。CPU/RAM 仍给 Condor 12 CPU/24576 MiB。4 个共享名额代表同一物理设备的令牌，不是 4 张卡。其他机器先为常驻程序留足余量，再配置自己的容量。

`GPUMemoryMiB` 是本站管理员定义的消耗资源，单位约定为 MiB，使用 HTCondor 原生 [自定义资源机制](https://htcondor.readthedocs.io/en/25.x/admin-manual/ep-policy-configuration.html#dividing-system-resources-in-multi-core-machines)。若已有 `MACHINE_RESOURCE_NAMES`，将该资源加入名单。`GPU_DISCOVERY_EXTRA` 的 `-repeat` 允许多个作业分到同一物理 GPU；`-divide` 分的是整卡广告容量，不会先扣背景预留。[GPU 发现参数](https://htcondor.readthedocs.io/en/25.x/man-pages/condor_gpu_discovery.html)

普通用户和 basePack 只提交官方 `request_gpus = 1` 与 `gpus_minimum_memory = <峰值> MB`。schedd 从标准作业属性 `GPUsMinMemory` 生成内部 `RequestGPUMemoryMiB`，并向原 `Requirements` 追加显存资源门槛。原 `RequireGPUs`、架构、系统和文件传输条件保留；CPU 作业不做 GPU 转换。内部资源改名只需同步调整 60/70 的资源定义、START、内部 Request 与匹配条件，客户端不需要修改。

本站把 `gpus_minimum_memory` 额外作为显存预订量，接收提交时可解析的正数，`MB` 为 MiB、`GB` 为 GiB；内部整数资源用 `ceiling` 向上取整，避免小正数零记账。省略属性时预订整池、与其他 GPU 作业串行；显式 `undefined`、零、负值、依赖执行节点 `TARGET` 的动态表达式、超过整个普通池或申请多于 1 个 GPU，在提交阶段用官方参数名说明原因并拒绝。有效申请仅因剩余资源不足时排队。提交拒绝表达式在 `JOB`（作业）与 `SCHEDD`（schedd）命名空间求值。转换对本 schedd 的新提交作业统一生效，不按客户端身份区分，也不重写已有队列。[原生提交转换与拒绝规则](https://htcondor.readthedocs.io/en/25.x/admin-manual/ap-policy-configuration.html)

官方 `gpus_minimum_memory` 仍是设备容量下限，`GlobalMemoryMb` 与 `RequireGPUs` 的设备筛选含义保持不变；累计预订来自本站规则。[官方提交字段](https://htcondor.readthedocs.io/en/25.x/man-pages/htcondor-jdl.html) 资源按申报量记账，应用仍须限制实际峰值；没有显存硬隔离或吞吐提升承诺。

修改 CPU、slot 定义、GPU 共享数或消耗资源总量后，暂停新提交并排空作业，平稳重启 startd，再核实际发布容量。`reconfig` 不能重建已有 slot：

```powershell
$env:CONDOR_CONFIG = '<native-condor-config>'
& '<condor-bin>/condor_config_val.exe' -subsystem STARTD -verbose NUM_CPUS MEMORY MACHINE_RESOURCE_GPUMemoryMiB
& '<condor-bin>/condor_restart.exe' -peaceful -daemon startd
& '<condor-bin>/condor_status.exe' -constraint 'PartitionableSlot =?= true' -af Name TotalSlotCpus TotalSlotMemory TotalSlotGPUMemoryMiB Cpus Memory GPUMemoryMiB
python -m basepack --config '<project-config>' resources capacity
```

父 slot 的 `TotalSlot*` 是总容量，`Cpus/Memory/GPUMemoryMiB` 是当前剩余量。`resources capacity` 保留标准 `cpus/memory_mib/gpus` 键；其余 `MachineResources` 仅在总量与剩余数量均发布时按原名、原生单位展示，Windows 未发布数值的 `Swap` 会省略。basePack 只按标准 CPU/RAM 总容量提前准入；GPU 与站点额度由 Condor 决定。保留本机需要的 START/SUSPEND/PREEMPT 与 starter 线程策略，核最终应用环境；父 slot 可以创建多个动态 slot。

embedding 自身的分配器额度由机器 TOML 的 `[embedding].gpu_memory_mib` 维护，独立服务不依赖 Condor。修改模型、输入上限或自身额度时重新标定背景峰值，随后调整节点供普通作业使用的容量。已有最大输入标定见 [资源结果](../devDoc/tasks/20261107-resource-coordination/result.md)；回执的 allocated/reserved/peak 是本进程 PyTorch 指标，WDDM 下 CUDA free 不代表全卡其他进程占用，全卡峰值使用外部 nvidia-smi 时间采样。动态 free 不参与准入。

## 从 0.2.0 切换到标准提交

1. 准备 0.3.0 普通 wheel 和候选 60/70 配置。暂停所有提交端的新作业与 embedding 请求，用正常认证上下文核队列并排空；备份 0.2.0 wheel、现行 Condor 配置和机器 TOML，备份放配置加载目录之外。
2. 用旧安装执行 `embedding stop`，确认 broker/worker 已退出。升级所有项目使用的普通 wheel，核安装来源及执行账户可读性。
3. 成对部署 60/70 并用 `condor_reconfig` 重载。容量与 slot 定义未变时无需重建 slot；若变更了这些定义，按上节排空并平稳重启 startd。核实际容量、已加载的转换和提交拒绝规则。
4. 在普通作业树之外启动 broker，用原生 Condor 和 basePack 分别核标准字段转换、正确结果、排队与取消归还，再核 embedding 继续服务，确认后恢复提交。

新规则只读取官方显存字段。旧 0.2.0 客户端仅发送内部申请，会被当成未申报而预订整池，切换期间不能混用。回滚同样暂停并排空、停止服务，成对恢复旧 wheel 与旧 Condor 配置（移除新增的 70），重载并核旧合同，再恢复 broker 和提交；不要只回滚一侧。

`condor_submit -dry-run` 只核客户端解析，不执行服务器转换。验收须保存新作业的实际 ClassAd，核内部申请与追加条件同时存在，并核事件、业务结果和资源归还。小矩阵仅证明调度记账，不代表实际分配全部申报显存或测得吞吐性能。

## 0.1.0 到 0.2.0 的历史迁移

1. 暂停新请求和作业提交，排空普通作业。用旧安装执行 `embedding stop`，确认 broker/worker 已退出。
2. 将机器 TOML 的 `[budget].embedding_gpu_mib` 迁为 `[embedding].gpu_memory_mib`，本机保留值为 `9216`；删除旧 `[budget]` 节及普通预算字段。
3. 普通安装 0.2.0 wheel，升级所有项目使用的提交端。旧包依赖专属预算属性，不能继续向新的通用节点提交作业；本版不保留该兼容分支。
4. 将旧 `60_basepack.conf` 归档到 Condor 配置加载目录之外，改用通用 `60_resources.conf`。按上节平稳重启 startd，核实际容量和 GPU 共享数，再启动 broker 并恢复请求。

升级后核 `resources capacity`，再运行普通 CPU/GPU 作业及 embedding 联合验证。历史 0.1.0 回执保留其原有条件，不作为新节点共享行为的验收。

## 共享服务生命周期

先在所有 Condor 作业树之外启动轻量 broker，模型在首个请求时加载：

```powershell
python -m basepack.embedding.broker --machine-config '<absolute-machine-config>'
```

这是前台进程；作为本机长期入口时可由任务计划或服务管理器启动，选择已验证账户。不要从 Condor payload 启动 broker。作业内客户端只连现有 broker，再由 broker 启动其自有模型进程；普通作业取消后共享模型继续服务其他项目。

机器 state_dir 保存 broker/worker endpoint、实例锁及 stderr。实例身份含固定模型、预处理、设备和代码版本，不含项目路径。多项目冷请求共用同一实例。worker 空闲到 idle_seconds 后卸载，broker 保留，下次请求按预留预算再启动；单请求取消/截止不退出共享服务。

升级或改模型、输入上限、自身额度前，暂停新请求与提交，排空相关工作，运行 `embedding stop`，确认 broker/worker 已退出，再切换包/配置并重新标定；若背景峰值变化，按上节调整 Condor 容量，最后启动 broker。推理和 status 拒绝代码/配置身份不一致的旧实例；stop 按机器 marker 独立清理旧 broker，仍推荐先停再升级。服务异常时保留 stderr 和 PID，核旧进程已退出后再显式启动，不自动重试推理或重复加载。

`embedding status` 查询共享状态，`embedding stop` 是独立管理员动作；返回 stopping 只代表已请求，worker 在当前 forward 完成后退出，确认 PID 消失后才视为释放。普通客户端 close/cancel 只影响本请求。普通任务进程树由 Condor 回收；broker 持有模型 worker 的独立进程所有权，broker 异常退出时也回收其模型进程。
