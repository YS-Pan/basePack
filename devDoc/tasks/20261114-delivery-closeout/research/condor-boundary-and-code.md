# Condor 问题、原生职责与自有代码量

2026-11-14。基于源码提交`06d4e09`（basePack 0.12.0.dev1）、本项目历史原证和当日HTCondor官方文档。调查未运行新作业、安装依赖或改变Condor配置；代码计数与原生能力分别核对，历史本机观测不推广为所有版本/平台。

**调查后的决定：** 用户已选择接受原生策略时效、取消额外PID回收确认，保留参数保真及提交恢复。待实施合同统一以[收尾计划第二节](../plan.md#condor原生职责与必要封装)为准；下文保留调查时的实现基线与取舍依据，其中尚待用户选择的表述已由该决定接续。

## 普适性与影响

| 事项 | 性质与已知证据 | 暂不处理的影响 |
| --- | --- | --- |
| wait路径抛`subprocess.TimeoutExpired` | basePack调用原生命令的封装问题；job14367只记录子进程约4.04秒超时，总耗时未知，未证明HTCondor普遍提前结束等待 | 调用者拿不到正常等待结果，业务流程可能中断；已提交作业仍由Condor运行和管理。不能据此认定作业失败或自动重提；发生频率未知 |
| PID复用后`cleanup_confirmed=false` | PID复用是操作系统通用行为，缺陷在本地仅用PID判断原进程；job14368已证明旧进程退出、PID被后来进程复用 | 主要是回收确认误报及默认30秒确认窗口的额外等待。当前代码只观察PID/后代，实际取消调用`condor_rm`，不按该PID直接杀进程；此例未证明资源泄漏 |
| Windows空参数保真 | 本机实际探针发现参数转换丢空字符串；已有中文、引号、反斜杠/空参数回归，尚不能判为全部Windows/Condor版本均有的厂商缺陷 | 删掉包装而未验证原生参数矩阵，可能导致位置参数移动、运行错误或结果含义变化 |
| 原生策略执行有延迟 | 早期本机3秒执行/排队限制分别观察到11/52秒生效；官方periodic策略按周期计算 | 接受原生时效可以简化客户端；要求更及时的客户端截止时，完全删除主动观察会改变行为。历史秒数不是当前上限或频率保证 |
| 单卡多作业累计显存记账 | 本站共享GPU策略，不是Condor故障；背景模型与普通作业并存 | 在保持四个同卡名额时删掉累计记账，单个申请分别合法也可能总量超额。声明式记账仍不提供驱动级显存隔离 |

槽位账户无普通home、user-site不可读及沙箱NTSSPI/ACL等属于Windows账户、安装位置或应用依赖边界，不是已证明的通用调度器缺陷；三工具中的相应环境适配不计入本次basePack jobs代码量。

## 哪些已可交给原生能力

| 能力 | 原生机制与当前关系 | 取舍 |
| --- | --- | --- |
| 等待作业 | `condor_wait -wait N`监视原生事件日志，basePack已经调用 | 0表示完成或中止，不证明业务成功；1同时包括等待到期和缺日志/不存在作业等错误。需要按输出/状态区分，外层Python超时不能一律吞成正常到期 |
| 排队与执行时限 | 当前submit已写`periodic_remove`和`allowed_execute_duration` | 原生策略不是客户端秒级截止的自动等价物。periodic默认60秒评估；allowed_execute_duration超限hold且不含文件传输。可在明确接受原生时效后减少客户端重复计时 |
| 停止和清理 | `condor_rm`负责活动作业停止/清理及后续history；当前取消已经用它 | 若完成合同以Condor管理范围为准，可讨论将本地PID核查降为诊断。若仍要独立检查已知进程，则需正确进程身份；此额外检查也不证明任意逃逸后代全部回收 |
| 终态时间 | 原生日志提供事件；Python `JobEventLog`支持结构化读取 | 可替代文本正则的候选。须先核目标Windows/Python ABI可用；`htcondor eventlog read --json`是否含所需终止时间字段也待核，不能为删14行就无条件引入新依赖 |
| 容量、GPU共享 | 自定义可消耗资源、partitionable slot、JOB_TRANSFORM均是原生能力，本站已采用 | `gpus_minimum_memory`筛选设备物理容量，不累计扣减共享显存；本站配置把声明转换成可消耗资源申请。若改独占普通GPU调度可简化共享策略，但会改变并发能力，且作业树外背景服务仍需协调 |

官方依据：[condor_wait](https://htcondor.readthedocs.io/en/25.x/man-pages/condor_wait.html)、[condor_rm](https://htcondor.readthedocs.io/en/25.x/man-pages/condor_rm.html)、[作业策略与GPU申请](https://htcondor.readthedocs.io/en/25.x/man-pages/htcondor-jdl.html)、[JobEventLog](https://htcondor.readthedocs.io/en/25.x/apis/python-bindings/api/version2/htcondor2/jobeventlog.html)。进程族的best-effort及Linux专有增强见[原生进程跟踪说明](https://htcondor.readthedocs.io/en/23.0/admin-manual/setting-up-special-environments.html#group-id-based-process-tracking)；未找到据以保证本站Windows任意后代回收的证据，不能把Linux机制当作当前Windows能力。

## 当前代码量

统计为物理行、非空行、非空且非整行注释的代码行，保留docstring。范围是active路线`src/basepack/jobs/`五个完整文件；不含少量分散在共享配置/doctor/根CLI中的接线，也不含其它项目应用适配。

| 文件 | 物理行 | 非空行 | 代码行 |
| --- | ---: | ---: | ---: |
| `client.py` | 256 | 233 | 228 |
| `submit.py` | 111 | 94 | 94 |
| `worker.py` | 33 | 28 | 28 |
| `cli.py` | 42 | 37 | 37 |
| `__init__.py` | 6 | 4 | 4 |
| **合计** | **448** | **396** | **391** |

以下按互斥源码范围分组，合计仍为391代码行；分组包含混合职责，不是可删除工作量：

| 分组 | 代码行 | 机制与代码位置 |
| --- | ---: | --- |
| 普通接口适配 | 211 | JobSpec、字段/参数/环境编码、文件材料、资源观测、CLI等剩余范围；不是故障补丁 |
| 状态、等待、取消、清理及限时策略 | 123 | [client.py 114–227、230–238](../../../../experiments/20261106-basepack/src/basepack/jobs/client.py#L114)与submit.py 91–96。含status34、observe29、confirm_cleanup22、cancel14、wait3、run6、worker_pids9及submit策略6代码行 |
| Windows参数包装worker | 28 | [worker.py](../../../../experiments/20261106-basepack/src/basepack/jobs/worker.py)：JSON保留完整argv，再用subprocess启动；还含PID/环境/退出回执，不全是参数补丁 |
| 三项差异/恢复处理 | 29 | [client.py](../../../../experiments/20261106-basepack/src/basepack/jobs/client.py)：成功空JSON输出转空列表3行（37–40）；提交响应异常按唯一token反查queue/history14行（92–106）；终态事件时间提取12行（241–254） |

提交响应恢复用于避免同一副作用被重复提交；没有证据表明每个Condor都会丢响应。终态事件时间处理源于已撤销作业缺CompletionDate且EnteredCurrentStatus仍为QDate的本机观察。空查询处理只接受成功空输出，非空坏JSON仍报错。当前清理仍是`pid_exists`，尚未实施PID＋创建时间；当前等待短轮次叠加subprocess期限，也未实施拟修方案。

站点示例单列：[60_resources.conf](../../../../experiments/20261106-basepack/examples/condor/60_resources.conf)为21/18/14行，[70_job_transforms.conf](../../../../experiments/20261106-basepack/examples/condor/70_job_transforms.conf)为19/18/13行，合计40物理、36非空、27非注释行。它们是仓库样例，不是wheel包数据；历史已部署不等于本次重新确认机器配置逐字一致。

三个专属测试文件共740物理、611非空、608代码行，37个test函数，参数化实例更多；未执行。用户资源/管理员专属章节约140物理行，系统资源说明相关段另计，均不与代码求和。

## 后续决定与边界

调查后已按用户选择更新[收尾计划](../plan.md#condor原生职责与必要封装)：移除额外PID确认及客户端重复作业时限，修正观察等待结果/错误传播，保留必要参数包装及不重复提交恢复；站点共享显存继续沿原生配置管理。这里的代码量仍描述现有产品，尚未实施删减。

原生结构化事件读取是候选，但引入绑定/版本和部署负担必须小于实际收益。391行不是必须保留的结论，也不是全部可删的结论。没有重跑作业、验证新机或证明跨平台普适性；本次只读源码计量、历史检索及官方文档核实。

历史依据：[首轮资源结果](../../../archive/20261107-resource-coordination/result.md#预算修复与边界)、[R6](../../../archive/20261107-resource-coordination/native-condor.md)、[R7](../../../archive/20261107-resource-coordination/standard-submit-result.md)、[职责整改结果](../../../archive/20261110-rectification/jobs-result.md)、[迁移问题记录](../../../archive/20261113-agenttools-migration/progress.md#使用中发现的条件与未决问题)。计量及检索原证在项目根`artifacts/runs/20261114-condor-review/`；后台自动维护结果与收尾沿[进度](../progress.md)。
