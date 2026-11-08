# R7：标准提交接口与 Condor 站点策略解耦

2026-11-08，R7.0–R7.4 已完成：0.3.0 普通 wheel 与 schedd JOB_TRANSFORM 已部署，原生调度及联合 embedding 真实验收通过。实际结果见 [R7 回执](standard-submit-result.md)，执行状态统一维护在 [进度](progress.md)，原 R0–R5 计划保留在 [原计划](plan.md)。

## 目标与既定约束

不了解 basePack 的用户，也能用标准 Condor 提交方式运行任务。用户和 basePack 只声明官方参数，内部显存资源名、额度与转换规则由机器管理员维护；Condor 的配置和运行无需调用 basePack 代码。

```ini
request_gpus = 1
gpus_minimum_memory = 3000 MB
```

保留用户已确定的容量：背景合计预留 **9 GiB / 9216 MiB**；本卡总量16380 MiB，普通显存池为 **7164 MiB**；同卡最多 **4个普通GPU作业**。CPU/RAM保持12 CPU/24576 MiB。独立embedding继续由背景服务管理，普通任务的匹配、记账、排队和进程生命周期交给Condor。

4个GPU名额是同一物理设备的共享令牌，不代表4张物理卡。显存额度按申报量记账，应用自行限制实际峰值；本轮不增加驱动硬隔离，也不承诺并发必然提高吞吐。

## 提交合同与职责

| 维护方 | 职责 |
| --- | --- |
| 普通用户、basePack等提交客户端 | 使用官方request字段；basePack将现有JobSpec.gpu_memory_mib转换为gpus_minimum_memory，不再发送内部显存资源申请 |
| 执行节点配置 `60_resources.conf` | 维护CPU/RAM、4个共享名额及7164 MiB显存池；内部资源名由管理员定义，保留节点准入规则 |
| 拟新增的提交策略 `70_job_transforms.conf` | 由schedd统一转换新作业，添加内部资源申请和匹配条件，并以官方参数给出提交错误；不按提交者是否为basePack区别处理 |
| 独立embedding | 保留自己的模型与分配器设置；普通作业取消不影响其生命周期 |

两份Condor配置由本机主配置加载。额度数值只在节点容量配置维护，转换规则引用它；内部资源改名只需调整Condor配置，客户端源码不随之修改。

官方 `gpus_minimum_memory` 仍表示设备容量下限；本站点额外将其作为作业的显存预订量。这是机器使用约定，不宣称该字段原生提供显存累计配额。原 `GlobalMemoryMb`、`RequireGPUs` 和其他匹配条件保留原义。

以下为本计划确定的站点策略，实施结果与检查范围以 [R7 回执](standard-submit-result.md) 为准；不追溯改变 R0–R6 的历史条件：

| 输入 | 处理 |
| --- | --- |
| CPU作业，无GPU申请 | 不做GPU转换，正常调度 |
| 申请1个GPU名额，并填写正的gpus_minimum_memory | 将其MiB数值作为内部显存申请，允许在总额度和名额范围内共享 |
| 申请GPU但省略显存需求 | 整个作业预订普通显存全池，排队后串行运行；用户无需知道内部资源名 |
| 显式填写零、负值或不支持的显存表达式 | 提交时清晰拒绝，错误说明引用官方参数；不产生零成本GPU申请 |
| 单作业显存需求超过整个普通池 | 提交阶段说明无法满足；仅暂时剩余不足时排队 |
| 申请多于1个GPU | 当前单物理卡共享池清晰拒绝，避免将重复名额误当成多卡支持 |

## 实施批次与完成条件

### R7.0 核定提交链与转换原型

读取实际Condor配置及当前队列，核本机25.4的schedd转换、提交拒绝规则和重载方式。保留现有探针 `artifacts/native-condor/probe-job-transform.conf` 与 `.ads`；此前离线输出符合预期但工具退出1，先查清调用或工具问题，不能记作通过。`condor_submit -dry-run`只核客户端解析，不能代替服务器转换验收。

构造CPU、显存已填、显存省略及非法值的最小作业描述，检查转换结果、退出码和原始错误；内部Request字段与Requirements追加须同时验证。仅修改Request属性不会重新触发condor_submit生成资源匹配条件。

**完成：** 明确默认值、拒绝条件、单位、规则顺序和错误信息；可解释离线工具结果，形成可供真实schedd验证的短配置。多GPU的离线乘法样例不作为双卡能力证据。

### R7.1 建立通用Condor站点策略

在schedd使用原生JOB_TRANSFORM，只处理本范围GPU作业：从官方作业属性取数，生成内部显存申请，并显式追加资源门槛。保留原Requirements、RequireGPUs、架构、系统及文件传输条件；CPU作业不变。转换结果由站点策略决定，不依赖提交端自行填写内部字段。

提交拒绝规则处理非正值、超池额度及多GPU申请，直接依据标准输入判断，避免依赖与transform的执行先后。保留已有JOB_TRANSFORM_NAMES等管理员规则。新配置只覆盖此schedd的新提交作业；已有队列不会自动重写。

**完成：** 原生CLI和Python提交走同一规则；无basePack安装或导入要求，内部字段及原匹配条件正确，普通错误在提交时可见。

### R7.2 将basePack缩为标准提交客户端

GPU提交只生成request_gpus和gpus_minimum_memory；删除提交、capacity映射和GPU准入中的GPUMemoryMiB硬编码。capacity按MachineResources通用发现额外资源并原名展示，不解释特定资源名；说明本机GPU计数是共享名额。保留CPU/RAM基于标准总容量的准入，GPU内部额度的拒绝和排队由Condor负责。

保留现有参数编码、作业追踪、run/submit/status/wait/cancel、日志与回收确认。新增必要回归，证明没有该自定义资源的普通Condor节点仍可按标准字段提交，以及内部资源改名无需修改客户端。

**完成：** 源码提交逻辑不包含本机内部显存资源名；标准字段转换与现有生命周期回归通过。用户说明只要求官方参数，管理员说明负责内部映射。

### R7.3 协调切换与真实验收

先准备新wheel和候选配置，再暂停新提交、排空已有作业并备份当前0.2.0部署。升级提交客户端、部署提交策略并重载schedd，验收后恢复使用；避免新规则把旧客户端仅有的内部显存声明当成“未申报”而按全池计费。不建设长期兼容分支，回滚时成对恢复包与策略。

本轮不改变slot容量或GPU共享数，原则上只需schedd重载；若实施中实际修改slot定义，再排空并按既有流程平稳重启startd。包升级涉及共享服务时沿用已验证的停止/恢复流程。

复用R6的小矩阵和事件日志探针，以不导入basePack的原生提交为主，再验证basePack调用：

| 场景 | 必须观察的结果 |
| --- | --- |
| 原生CLI与Python填写官方GPU/显存字段 | 新队列属性自动含正确内部申请与匹配条件；真实CUDA结果正确 |
| 4项各申请1000 MiB，再提交第5项 | 前4项同卡有真实进展；第5项在显存仍足时因名额排队，释放后执行 |
| 先占5000 MiB，再申请3000 MiB | 尚有GPU名额时仍因显存不足排队；释放后恢复 |
| GPU未填显存 | 自动预订全池；与其他GPU作业互斥，完成或取消后额度恢复 |
| 非法值、超全池、请求多GPU | 明确拒绝；不写成暂时无资源，也不出现零额度GPU作业 |
| 原有GPU筛选和CPU作业 | 不满足原筛选的GPU作业仍不能运行；CPU作业无GPU字段也正确完成 |
| basePack与共享embedding联合 | 普通作业及向量结果正确；取消普通作业后共享模型继续，资源释放单独确认 |

**完成：** 保留job ID、转换后ClassAd、状态、实际结果和清理证据；核节点额度归还，测试任务无遗留。小矩阵证明调度记账，不能冒充全额显存分配或吞吐性能测试。

### R7.4 使用交付与记录

普通用户文档使用官方参数；管理员文档维护60/70配置职责、无显存声明的默认行为和切换步骤。实现完成时再更新现行README、resources skill、系统说明、进度及结果；历史R6按当时条件保留。普通wheel部署后核安装来源、随包文件、源码外调用和必要回归，主agent统一检查差异，在main提交代码、文档与change_log。

**完成：** 新用户无需了解basePack或内部显存资源名即可提交任务；basePack更换为其他标准提交端不改变调度合同，内部资源名变化也不要求客户端改代码。

## 顺序、范围与依据

R7.0确认合同后，Condor策略与客户端改造可分工并行，由主agent统一整合；联合部署和验收按顺序执行。首批只覆盖本机单NVIDIA GPU的普通vanilla作业；多物理GPU逐卡记账、跨schedd部署、late materialization、MPS和性能调优留给实际需求，不并入本轮。

- [schedd提交转换与拒绝规则](https://htcondor.readthedocs.io/en/25.x/admin-manual/ap-policy-configuration.html)：服务器在提交时修改作业描述，规则按顺序应用。
- [转换语言](https://htcondor.readthedocs.io/en/25.x/classads/transforms.html)与[离线工具](https://htcondor.readthedocs.io/en/25.x/man-pages/condor_transform_ads.html)：SET/EVALSET、原属性引用与检查。
- [官方提交字段](https://htcondor.readthedocs.io/en/25.x/man-pages/htcondor-jdl.html)：request_gpus、gpus_minimum_memory及其设备筛选含义。
- [当前模块](../../system/modules/resources.md)与[管理员说明](../../../docs/administrator.md)维护现行行为，[R6回执](native-condor.md)保留实施基线；实际JOB_TRANSFORM启用与验收证据见[R7回执](standard-submit-result.md)。
