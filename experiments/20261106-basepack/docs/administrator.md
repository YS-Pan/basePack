# 机器部署与维护

本页属于当前 active 路线 [20261106-basepack](../README.md)，按 0.4.0 接口说明单机 Windows、单张 NVIDIA GPU 的部署。复用 Python 3.13、固定 Qwen3-VL-Embedding-2B 权重与 HTCondor；模型目录含 model.lock.json 和 model/。机器配置使用 schema 1，维护路径与 embedding 设置；Condor 维护普通容量和站点策略。本机实际安装及验收状态见 [资源进度](../../../devDoc/tasks/20261107-resource-coordination/progress.md)。

## 安装与执行账户

稳定安装普通 wheel。系统目录安装通常需要管理员终端，确认 pip 没有回落 user-site：

```powershell
python -m pip install --no-deps --no-user '<basepack-wheel>'
python -s -c "import basepack; print(basepack.__file__)"
```

包、配置、输入和模型须对服务及 Condor 执行账户可读，项目产物目录须可写。用真实小作业验证 slot 账户能加载包、写结果和连接共享服务；doctor 只读检查不能代替该验证。embedding 依赖及固定版本见 [pyproject.toml](../pyproject.toml) 的 extra，CUDA PyTorch 须适配驱动；已有环境直接复用。机器模板通过 `from basepack.project.init import template` 读取，项目接入见 [说明](setup-project.md)。

源码构建与开发安装的目标是 `<repo>/experiments/20261106-basepack`，交付和回滚 wheel 留在该路线 `dist/`；命令见 [路线入口](../README.md)。开发 editable 与普通 wheel 在同一解释器中只保留一种有效安装；项目只绑定 Python 和机器配置，不保存包副本或 PYTHONPATH。服务账户与作业账户可不同，权限按文件和 loopback 实际访问核定。本机服务由交互用户启动，普通作业使用 Condor slot 账户。

CondorClient 只使用机器配置的 bin_dir/config_file，向原生命令显式传 CONDOR_CONFIG。受限 sandbox 的 Windows SSPI 认证可能失败；保留原错误，在正常用户上下文复核，不因此改认证政策。

## Condor 容量与策略

普通作业容量和调度由 Condor 管理，运行时无需调用 basePack。本站入口为 `C:/condor/condor_config`，加载两份配置，本路线的 `examples/condor/` 样例是维护源，机器上部署的配置仍由管理员维护：

| 配置 | 职责 |
| --- | --- |
| [60_resources.conf](../examples/condor/60_resources.conf) | CPU/RAM、同卡名额、内部显存资源及 START 条件 |
| [70_job_transforms.conf](../examples/condor/70_job_transforms.conf) | schedd 标准字段转换与提交拒绝 |

本机容量合同保持 12 CPU/24576 MiB RAM、4 个同卡名额及 7164 MiB 普通 GPU 池；背景程序合计预留 9216 MiB。4 个名额是同一物理 GPU 的共享令牌。额度只在 60 配置定义，70 引用；保留已有的 JOB_TRANSFORM_NAMES、SUBMIT_REQUIREMENT_NAMES 和匹配策略。

basePack 和原生用户都提交官方 `request_gpus = 1`、`gpus_minimum_memory = <峰值> MB`。schedd 从 GPUsMinMemory 生成内部 RequestGPUMemoryMiB，并向原 Requirements 追加显存门槛，保留 RequireGPUs 及硬件筛选；CPU 作业不转换。内部资源改名只需同步站点配置，客户端不镜像额度。

本站要求显存申请在提交时可解析为正数；MB 为 MiB、GB 为 GiB，内部整数额度向上取整。省略显存时预订整池；显式 undefined、零、负值、依赖 TARGET 的动态表达式、超池或多 GPU 申请会被拒绝。有效申请在资源不足时排队。规则对本 schedd 的所有标准提交端生效。字段的设备容量筛选含义保留，累计预订来自本站策略，详见 [官方提交字段](https://htcondor.readthedocs.io/en/25.x/man-pages/htcondor-jdl.html) 和 [原生转换](https://htcondor.readthedocs.io/en/25.x/admin-manual/ap-policy-configuration.html)。

`jobs capacity` 显示父 slot 总量与剩余量，额外 MachineResources 仅在两种数值均发布时按原名、原生单位显示。客户端只检查 CPU/RAM 总量；GPU 拒绝、排队和终态由 Condor 决定。申报量不提供显存硬隔离，也不承诺吞吐提升；应用须限制线程和框架实际峰值，保留 Condor 的 CUDA_VISIBLE_DEVICES。

改变 CPU、slot 定义、GPU 名额或资源总量时，暂停新提交、排空作业并平稳重启 startd，再核实际发布容量；reconfig 不会重建已有 slot。只改变提交规则时按影响重载 schedd。本站配置机制及历史实测见 [R6 结果](../../../devDoc/tasks/20261107-resource-coordination/native-condor.md) 和 [R7 结果](../../../devDoc/tasks/20261107-resource-coordination/standard-submit-result.md)。

embedding 分配器额度由机器 `[embedding].gpu_memory_mib` 维护，独立于 Condor。模型或推理设置改变且可能影响峰值时，重新测量背景用量再调整普通池。PyTorch allocated/reserved/peak 是本进程指标；WDDM 下 CUDA free 不代表全卡其它进程占用，全卡峰值须使用外部 nvidia-smi 时间采样。动态 free 不参与准入。

## 共享服务与身份

在所有 Condor 作业树之外启动轻量 supervisor，首个请求才加载模型：

```powershell
python -m basepack embedding --machine-config '<absolute-machine-config>' serve
python -m basepack embedding --machine-config '<absolute-machine-config>' status
python -m basepack embedding --machine-config '<absolute-machine-config>' stop
```

serve 是前台进程，长期入口可交给任务计划或服务管理器，使用已验证账户。项目客户端只连接；supervisor 按需拥有单个模型 worker。空闲达到 idle_seconds 后 worker 整进程退出，supervisor 留待下次请求。单请求取消、截止或客户端 close 不停止共享模型；普通作业取消也不影响另一项目。

机器 state_dir 下保存登记、锁和日志，物理文件名仍为 broker.json/broker.lock。三类身份分别维护：协议版本标识 RPC 合同；embedding_identity 标识模型 revision/文件、FP16、指令、图像预处理及 pooling 的向量语义；deployment_fingerprint 检查服务代码与运行配置的同代一致性。输入接纳上限、分批、线程、空闲时限及路径变化不改变向量语义标识。

进程启动时固定实际部署身份。客户端拒绝错代实例，管理员 status 报告运行与磁盘目标差异，stop 可使用旧 marker 的 endpoint/凭据。该诊断能力不表示支持客户端独立跨版本升级。返回 stopping 只表示已请求；确认 supervisor/worker PID 消失后才视为释放。Windows Job Object 让 supervisor 异常退出时也回收其 worker；异常时保留 stderr 和 PID，核旧进程退出后显式启动。

## 升级与回滚

从 0.3.0 一次切换到 0.4.0：

1. 准备普通 wheel、旧 wheel 和配置备份，核实际调用脚本、项目配置、服务及 Condor 队列。暂停新请求与提交，等待所有旧作业终结并确认回收；旧 resources.worker 和旧 payload 必须在删除模块前排空。
2. 用仍在安装的 0.3.0 停止共享服务，例如 `python -m basepack --config '<old-project-config>' embedding stop`，确认旧 broker/worker 已退出。不可依据历史 PID 或队列回执操作。
3. 普通安装 0.4.0，并为每份实际配置执行 `python -m basepack migrate --from-config '<old-config>'`。检查 `.basepack/migration/` 的备份与映射、配置和宿主指针。项目变为 schema 2/[jobs]；Python API 改用 basepack.project、CondorClient、EmbeddingClient(machine)，CLI 改用 jobs 及上面的机器管理入口。
4. 在作业树外启动新服务，用源码外项目核图文向量、CPU/GPU 结果、并存、取消、日志和资源归还，再恢复提交。本轮保持机器 schema 1、模型、共享状态位置及 Condor 60/70 策略，不重新标定额度。

失败时保持请求与提交暂停，排空新作业、用新安装停止服务，按迁移映射恢复移动的数据和原配置/AGENTS/忽略文件，再恢复旧 wheel 和调用脚本。确认旧安装来源及配置可用后，用旧入口启动服务并验证，再恢复提交。本站 60/70 未变化，无需因本次包迁移回滚节点策略。

新解析器直接拒绝旧项目 schema；旧格式只由显式迁移读取。机器管理沿用原凭据，不新增账户隔离。迁移与回滚都不接管历史旧项目的知识、数据库或业务授权。
