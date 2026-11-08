# 资源协调进度

更新：2026 年 11 月 8 日（北京时间）。

## 当前阶段

[R0–R5 计划](plan.md) 正在实施。R0–R2 已完成；R3/R4 联合验收进行中，R5 使用文档和 skill 已准备，完整普通 wheel 验收待联合结束。记忆建设由 [独立任务](../20261106-memory-system/plan.md) 维护。

## 已完成

- R0 公共入口：pyproject、basepack 包、唯一配置解析、随包模板、init/config show/按设施 doctor、README 与项目接入说明。系统 Python editable 新进程能加载临时代码修改；最小普通 wheel 安装到系统 site-packages，从源码外初始化两个中文/空格项目，含子目录配置、独立数据路径、随包模板及 core doctor。3 项配置回归通过，原始证据在 `artifacts/r0/`；普通用户 pip 回落用户站点的问题经管理员系统安装解决。
- 当前 Condor 探针已实际执行 CPU/GPU 小作业，slot 低权限账户可读源码、权重和中文输入，返回嵌套输出并连通作业外 loopback；GPU 矩阵结果与 CPU 一致。取消探针已确认父/子 PID 消失。入口实现及完整验收仍在进行，详见后续回执。
- R0 标定：固定 max_length=2048、文本 batch4、max_pixels=1048576；真实向量为 2048 维且 L2 有效。allocator 峰 7786 MiB，整卡基线约1009 MiB、采样峰8937 MiB，RSS 峰2054 MiB。采用 E=9216、S=2048、B=5116 MiB；物理16 CPU/48349 MiB 留给 Condor12 CPU/24576 MiB。初始 RAM32768 在桌面基线约20 GiB 后收紧。机器配置 `D:/AgentTools/basepack.toml`，派生片段 `C:/condor/config/60_basepack.conf`；peaceful 重启 startd 后实际发布容量与 hash `5dd7fc9014b383e0` 已核，证据 `artifacts/r0/published-budget-final.json`。
- R1 共享 embedding 已通过：跨项目并发冷请求同 PID；加载期/在算取消、排队截止后另一项目继续；文本最大批次/图片有效；空闲卸载再载、worker 崩溃原请求失败后新请求重启、broker 崩溃回收 worker、显式停止均实测。代码与接口见 [模块说明](../../system/modules/resources.md)，证据 `artifacts/resource-acceptance/embedding/calibration.json`、`r1-real.json`；3 项服务竞态回归通过。
- R2 已验证真实计算、UTF-8 参数数组保真、中文/空格字段、最终线程环境和 CUDA 可见性、slot 账户全局包加载、嵌套输出回传、应用 exit7 原错误、观察超时不取消、父子孙进程取消、run 执行到期及无客户端原生执行到期。实际提交单位为 memory MiB/disk KiB；原生3秒执行上限实测11秒移除，有检查延迟。证据 `artifacts/condor/r0-successful-probes.json`、`r2-receipt.json`、`r2-native-cleanup.json`。所有任务核预算版本与真实容量，GPU H 超 B 直接拒绝。
- R2 收尾：最终24GiB预算下，缺少显式输出实际触发 held12，run 返回原始缺件诊断并撤销确认；CLI 应用 exit7 返回完整 JSON 与外部退出1。证据 `artifacts/condor/r2-held-receipt.json`、`r2-cli-failure-receipt.json`。整批8项回归通过。
- R3 最新 warm-first 已取得真实 GPU 重叠：最大文本4×2048 token、1024²图文均有效，普通矩阵任务在 forward 窗口内产生正确进展，第二普通 GPU 排队且模型保持可用。CPU/RAM 声明准入及排队已验证初始预算，最终24GiB RAM 相关项重测中；原生排队时限已在无 run 强制情况下生效。联合证据持续写入 `artifacts/resource-acceptance/joint/`，完整结论待下列余项完成。

- 已先读旧项目相关聊天，再核代码、测试与历史回执，形成 [旧实现复用清单](research/legacy-implementation.md)。本地多模态 runtime、批处理、项目局部热复用和 owned 进程清理可提取，跨项目共享与真实并行仍待实现。
- 已据用户要求修订为独立 embedding 服务与 Condor 普通重任务两条链，以固定显存预留衔接；明确公共入口先行、各链探针分别放行，以及请求隔离、作业外服务所有权、旧 watchdog 改造、预算发布和组合取消验收。
- 已完成 [安装与项目配置布局](deployment-layout-plan.md)：系统 Python 包、机器共享配置、项目接入文件、局部数据/任务目录、随包模板与 agent 读取入口。配置、命令和安装包仍待交付。
- 已有 [初次设施调查](research/infrastructure.md) 和 [系统环境快照](../../system/environment.md)，它们只提供各自时点的观测，不代表当前接入成功。
- 已按用户要求由三名 subagent 分查 yadof 的 admin_tool、dev_doc 与实现/测试，主 agent 复读关键原证，形成 [Windows Condor 使用经验](research/yadof-condor.md)。补 R0/R2 的线程环境、字段引用、资源单位、slot、传输与超时探针，区分已解决事故、撤回方案及旧部署特例；本次未运行作业或修改机器配置。
- 已据后续讨论维护 [部署合同](deployment-layout-plan.md#开发安装与正式部署)：开发机使用系统 Python editable 引用，稳定部署和发布验收普通安装 wheel；补重装/服务重启时机、源码账户访问及安装来源检查，项目配置保持统一。R0/R5 与 Condor R2/R4 的完成条件已同步，尚未实际安装或验证运行行为。

## 待核与边界

- 剩余联合项：先普通 GPU 后冷 embedding、作业内冷请求与取消后独立服务存活、最终 RAM 容量验收及普通 wheel 换路径安装。
- Windows SSPI 在受限进程中失败、正常用户上下文通过；实测保留现有认证与 slot 账户配置。RAM 验证覆盖声明准入和排队，没有把全部声明额度实际分配；显存测量的采样盲区见管理员说明。
- 记忆任务 P0/P1 复用本任务 R0 的包/配置入口，P2 接入 R1 的共享 embedding 客户端；本任务用合成请求验收，不等待记忆索引、建图或数据库实现。

## 下一步

1. 完成 R2 最后诊断及 R3/R4 最终联合项，核数值、向量、时间线及回收。
2. 排空并停止受影响服务后普通安装最终 wheel，从源码外验证两项目、移动项目和新检出接入；补结果、实际检查与余项。

详细动作和完成条件在 [计划](plan.md) 维护，本页记录实际状态；预算修改、安装与服务重启均记录实际操作，不以探针成功替代完整联合验收。
