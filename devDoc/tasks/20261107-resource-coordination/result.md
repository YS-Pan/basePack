# 资源工具 R0–R5 交付结果

路径追溯（2026-11-09）：下文保留当时的运行路径；选留原证现归根 `artifacts/runs/<原批次>/`，原 dist 包现归 `experiments/20261106-basepack/dist/`，位置映射见[布局迁移结果](../../archive/20261109-project-layout/result.md)。

2026-11-08。R0–R5 已完成本机功能验收；运行源码版本 `9fc1d4d`，普通 wheel `basepack-0.1.0-py3-none-any.whl` 已安装到系统 Python。记忆检索、建图和数据库未纳入本轮。

本页保留 0.1.0 的验收条件；当前 0.2.0 通用 Condor 节点与多作业共享结果见 [后续改造](native-condor.md)，现行状态以 [资源进度](progress.md) 为准。

## 交付与稳定部署

- [公共入口与使用文档](../../../experiments/20261106-basepack/docs/setup-project.md)：init/config show/doctor，显式项目配置与唯一机器配置、随包模板；editable开发和普通wheel已分别实际安装验证。
- [资源调用](../../../experiments/20261106-basepack/docs/resources.md)：共享图文embedding、批次、一次run和长任务接续；[管理员说明](../../../experiments/20261106-basepack/docs/administrator.md)负责broker账户、启动、预算发布及升级。
- [模块边界](../../system/modules/resources.md)、[resources skill](../../../experiments/20261106-basepack/skills/resources/SKILL.md)与[小示例](../../../experiments/20261106-basepack/examples)已交付。
- 稳定包在 `C:/Program Files/Python313/Lib/site-packages/basepack`；机器配置 `D:/AgentTools/basepack.toml`。轻量broker26696在作业树外以交互账户运行，首请求再载模型，重启机器后需按管理员说明启动。

最终wheel为35350 B，SHA256 `40f3426fb3990f8ba1de7bdc0f6d392464766e661b6818cc72058bba805a1019`；校验和在 `dist/SHA256SUMS.txt`。22份运行代码、模板和许可在源码/wheel/实际安装间逐字节一致。Git只保存源码、短文档、skill和小样例，验收输入、日志及wheel留忽略目录；未向远端发布。

## 实际功能结果

| 场景 | 核实结果 | 详细证据（仓库忽略目录） |
| --- | --- | --- |
| 公共安装与配置 | editable临时代码被新进程加载；最小普通wheel源码外初始化两项目，子目录配置、AGENTS合并与数据路径分离正常 | `artifacts/r0/*-receipt.json` |
| 现有Condor设施 | CPU14263/GPU14264真实数值；slot账户可加载系统包、读权重/中文输入、回传嵌套输出、访问作业外loopback；最终线程/设备UUID实测 | `artifacts/condor/r0-successful-probes.json`、`r2-receipt.json` |
| 最大embedding标定 | 4×2048 token与1024²图文共2048 token输出有效归一化向量；allocator峰7786MiB、整卡采样峰8937MiB、RSS峰2054MiB | `artifacts/resource-acceptance/embedding/calibration.json` |
| 共享服务 | 跨项目冷启动同PID、单请求取消/截止不伤其他请求；空闲再载、worker崩溃原请求失败、broker崩溃回收、显式停止/重启通过 | 同目录 `r1-real.json` |
| 普通作业生命周期 | 复杂Unicode/空参数、退出7、观察超时不取消、取消父子孙、缺输出held原错及清理；原生执行截止在无客户端强制下生效 | `artifacts/condor/r2-*.json` |
| 无匹配诊断 | 普通wheel下14298声明scratch大于执行盘而小于项目输出盘可用，实际queued未执行；better-analyze明确Disk条件0slot、No machines matched，随后取消确认 | `artifacts/condor/r2-queue-analysis.json` |
| 两机制并行 | 热模型先启动14278/14280、普通H5000MiB先启动14284均有正确GPU重叠；最大embedding forward内分别3/2个矩阵进展点，值256.0；第二普通GPU排队 | `artifacts/resource-acceptance/joint/warm-first.json`、`heavy-first.json` |
| 其他资源 | CPU/RAM声明满配时排队、可容纳时并行，单任务超CPU/RAM/GPU/输出盘拒绝；最终24GiB RAM复测通过；原生排队截止52秒后生效 | 同目录 `capacity-32768.json`、`capacity.json` |
| 联合取消与异常退出 | 作业内冷embedding后另一项目复用；取消作业父子孙消失，worker35956继续；请求deadline/cancel隔离。14293应用创建睡眠孙进程后exit7，两者实际消失 | 同目录 `lifecycle.json`；`artifacts/condor/r4-abnormal-tree.json` |
| 最终普通wheel | 源码外两项目、移动B、新检出接入与图文调用通过；共worker16464，GPU14295值512.0/exit0/cleanup确认；最大文本推理期间50个普通GPU正确进展点 | `artifacts/r5/wheel-receipt.json`、`deployed-state.json` |

联合汇总在 `artifacts/resource-acceptance/joint/summary.json`。验收时最终项目位于 `D:/project/20261108-basepack-wheel-acceptance-final/`。11 月 8 日整理后，首轮与最终测试目录均收进本项目 `tmp/acceptance/`；需长期复核的配置、迁移备份、真实作业日志和结果已另存 `artifacts/tmp-reorganization-20261108/evidence/`，原路径映射见同目录上级的 `moves.json`。历史回执保留原路径，临时项目可随任务结束清除。原验收收尾确认所有测试作业、测试broker和模型worker退出，最终独立broker无模型驻留，Condor队列为空。

## 预算、修复与边界

物理16CPU/48349MiB，给Condor12CPU/24576MiB。当前桌面基线约20GiB，故将初始RAM32768收紧；本轮验证声明准入/排队，并未实际分配全部RAM额度。GPU T16380−E9216−S2048=B5116MiB，机器配置派生片段并核发布版本 `5dd7fc9014b383e0`；仅reconfig不缩小旧父slot，空队列peaceful重启startd后才实际生效。

移除旧整卡锁、13GiB free门槛、项目局部模型所有权和整服务请求watchdog；提取固定本地runtime，不继承旧项目数据库、任务状态或授权。Windows Condor参数实测丢空值，故薄worker读取UTF-8参数文件；其他submit字段采用各自编码，并保留最终starter设备/线程环境。SSPI在受限进程中失败、正常宿主用户通过，保留既有认证政策。

两项测量修复来自真实回执：WDDM下CUDA可能只见本进程device-view，已改名cuda_free_bytes/cuda_total_bytes，全卡峰取外部nvidia采样；未执行即撤销作业缺CompletionDate时从原生终态事件取时间，缺测返回None。R5还捕获收尾删除空查询处理导致的解析回归，按Condor成功空文本合同修复并完整重验；非空坏JSON继续报错。对应资源回归5项，连同配置与服务竞态共11项，最终普通wheel模式全部通过。

这是单机Windows/单NVIDIA GPU/固定Qwen3-VL-Embedding-2B FP16的可用首版。预算依赖合作声明，CUDA allocator峰与采样整卡增量都不是精确进程显存；声明不提供驱动硬隔离。原生执行3秒限制实测11秒、排队3秒限制实测52秒，run另设客户端有界等待并分别报告清理确认。矩阵样例每轮有20ms间歇，最大embedding独立2.708秒、联合2.544/2.551秒，仅说明该合成负载并存，不作吞吐或低延迟保证。没有启用I/O token、多机策略、任务自动重试或记忆数据库。

匹配诊断的范围已单独核对：CPU满配时better-analyze仍可能称可匹配，因为原生分析对partitionable slot会模拟排空；不能将它当作实时空闲容量。[官方说明](https://htcondor.readthedocs.io/en/25.0/man-pages/condor_q.html#analyze)

维护文档77个本地链接目标与Git差异格式检查通过，resources skill静态校验通过。本轮采用4个订阅subagent分管embedding、Condor、联合验收和使用文档，由主agent整合检查并在main分批提交。宿主未提供主上下文/团队总token及完整墙钟计量，记为unknown；原始证据各含实测时间。
