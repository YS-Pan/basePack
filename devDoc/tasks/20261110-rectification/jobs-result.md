# Condor 作业观测与职责整改结果

2026-11-10；对应[整改计划](plan.md)第 2 项的作业分支。已完成源码、相关回归和本机正常用户上下文的小作业验收；普通 wheel 与共用客户端升级由安装分支负责，本分支未升级客户端、改 Condor 配置或重启共享服务。

## 实现与取舍

- `jobs/client.py` 移除本机 CPU/RAM total 准入门槛。正值和项目输出盘空间仍由客户端检查；匹配、资源准入、排队归 Condor，`capacity` 仅观测。纯 CPU 池未声明 GPU 时合法显示 0；`MachineResources` 已声明 GPU 却缺数量时，与 CPU/RAM 必需字段一样抛出原始缺字段错误。
- 回收依据分开表达：原生 history 且已知 PID 消失为 `known_processes_and_condor_history`；history 明确 `NumJobStarts=0` 且无执行日期为 `condor_history_never_started`；执行记录或 PID 缺失则 `condor_history_only`、`cleanup_confirmed=false`。空集合不再获得进程检查成功结论。
- 时间差保留负值，执行时间未发布时保持 `null`。超时依据客户端实际观察到的期限，或当前 held/从 held 删除的 `HoldReasonCode` 46/47；旧 hold code 不影响之后的运行状态。删除原因无法分类时保留 `reason` 和结构字段，`timeout=null`，删除英文猜测分支。
- 提交响应丢失时，仍只按本次唯一 token 反查 queue/history，找到实际 ID 即恢复，不二次提交。未找到保持原提交异常；反查失败以原提交异常为主并保留反查异常链。
- [资源使用](../../../experiments/20261106-basepack/docs/resources.md)、[资源模块](../../system/modules/resources.md)及随源码维护的 resources skill 已同步职责和观测合同。

## 回归与实际验收

源码加载自 active 路线，Python 3.13.17，pytest 9.2.0。`test_jobs.py`、`test_jobs_lifecycle.py`、`test_condor_policy.py` 共 **75 passed**；JUnit 在原证目录。覆盖纯 CPU 合法缺 GPU、已声明资源缺字段、负时间与缺时间、缺 PID/迟到回执、hold 代码与无关英文、单次提交恢复及反查异常链、wait/cancel 边界。检查差异通过；未为 skill 增加固定试用或审核流程。

真实执行使用正常用户 `ysPan` 的安全上下文，driver 直接导入修改后的源码。配置的 worker Python 仍为稳定客户端 `D:/AgentTools/envs/basepack-client/Scripts/python.exe`；源码与已安装 worker 的 SHA256 相同，均为 `aa3ade76d2695157b36b10d96d87806c6eb616085fe92df84a2ef37c4e42f541`。本机 Condor 25.4.0，沿现有机器配置和资源策略，未改共享安装。

| 本次作业 | 实际结果 |
| --- | --- |
| `14351.0` CPU、1 CPU/512 MiB、输入输出传输 | 应用退出 0，平方和 `333328333350000` 经 `result.json` 回传；`success=true`；worker/应用与实际 payload PID 均消失，scratch 删除。 |
| `14352.0` 申请 10000 CPU、3 秒队列期限 | 确实提交给 Condor，因无法匹配排队后被原生策略删除；`NumJobStarts=0`，回收 scope 为 never_started。原生未给结构化超时码，保留 `timeout=null` 和完整 RemoveReason。 |
| `14353.0` CPU sleep、3 秒执行期限 | 已启动后删除；客户端实际观察到执行期限并返回 `timeout=execution`，已知进程全部消失。 |
| `14354.0` CPU sleep、主动取消 | `wait(timeout=0)` 返回 observation_expired 且原生作业仍活动；随后 cancel 删除并确认已知进程消失，timeout 未被误标。 |

另在 `14351.0` 已完成的原生 history 上临时隐藏其专用 worker 回执，实际调用回收确认得到 `false/condor_history_only`，没有 `checked_pids`；随后恢复原回执。这是缺观测语义复核，不冒称发生了新的执行失败。

四个 ID 均已离开 queue。取消后的立即 startd 快照尚有待回收动态 slot；随后独立只读复核已为动态 slot **0**，资源恢复到 **12 CPU、24576 MiB RAM、4 个共享 GPU 名额、7164 MiB 普通显存**，所有返回的 checked PID 均不存在。最终源码的 `capacity()` 也取得相同标准资源数量。

验收脚本第一次错误地要求原生删除的队列作业必有 `timeout=queue`，因此断言失败；实际产品已按整改合同返回未知分类。纠正该脚本断言后复用两项已结束作业的原证，继续完成其余两项，没有为满足断言修改产品或重复提交已结束作业。

## 原证、边界与交接

选留原证：`artifacts/runs/20261110-rectification-jobs/`，包含 driver、最终源码快照、JUnit、四项原生 ad、提交材料/事件/worker 回执、业务结果、缺回执复核、最终 startd/queue/PID 结果；开发临时材料位于 `tmp/rectification-jobs/`。

认证执行边界沿[运行环境](../../system/environment.md#当前资源查询与执行边界2026-11-10)：受限沙箱 NTSSPI 错误不属于本次产品失败，也未被修复；本次实际功能验收在正常用户上下文执行。物理池仍是既有 GPU 池；无 GPU 字段的 CPU-only 节点合同由回归验证，本次真实 CPU 作业不申请 GPU。未人为制造网络提交丢响应或 native hold 46/47；这些异常的单次恢复、分类和原错保留由对应回归覆盖。

作业分支无剩余实现项。普通 wheel、安装来源与共用客户端升级沿整改计划第 3 项整合；本次改动没有新增源码/测试文件，现有 source_scope 已含相关文件。
