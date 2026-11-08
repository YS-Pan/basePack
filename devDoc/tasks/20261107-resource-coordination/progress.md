# 资源协调进度

更新：2026 年 11 月 8 日（北京时间）。

## 当前阶段

[R0–R5 计划](plan.md) 正在实施。R0 公共包/配置已交付，embedding 提取标定与 Condor 真实探针并行推进；随后分别放行 R1/R2，再联合执行 R3–R5。记忆建设由 [独立任务](../20261106-memory-system/plan.md) 维护。

## 已完成

- R0 公共入口：pyproject、basepack 包、唯一配置解析、随包模板、init/config show/按设施 doctor、README 与项目接入说明。系统 Python editable 新进程能加载临时代码修改；最小普通 wheel 安装到系统 site-packages，从源码外初始化两个中文/空格项目，含子目录配置、独立数据路径、随包模板及 core doctor。3 项配置回归通过，原始证据在 `artifacts/r0/`；普通用户 pip 回落用户站点的问题经管理员系统安装解决。
- 当前 Condor 探针已实际执行 CPU/GPU 小作业，slot 低权限账户可读源码、权重和中文输入，返回嵌套输出并连通作业外 loopback；GPU 矩阵结果与 CPU 一致。取消探针已确认父/子 PID 消失。入口实现及完整验收仍在进行，详见后续回执。

- 已先读旧项目相关聊天，再核代码、测试与历史回执，形成 [旧实现复用清单](research/legacy-implementation.md)。本地多模态 runtime、批处理、项目局部热复用和 owned 进程清理可提取，跨项目共享与真实并行仍待实现。
- 已据用户要求修订为独立 embedding 服务与 Condor 普通重任务两条链，以固定显存预留衔接；明确公共入口先行、各链探针分别放行，以及请求隔离、作业外服务所有权、旧 watchdog 改造、预算发布和组合取消验收。
- 已完成 [安装与项目配置布局](deployment-layout-plan.md)：系统 Python 包、机器共享配置、项目接入文件、局部数据/任务目录、随包模板与 agent 读取入口。配置、命令和安装包仍待交付。
- 已有 [初次设施调查](research/infrastructure.md) 和 [系统环境快照](../../system/environment.md)，它们只提供各自时点的观测，不代表当前接入成功。
- 已按用户要求由三名 subagent 分查 yadof 的 admin_tool、dev_doc 与实现/测试，主 agent 复读关键原证，形成 [Windows Condor 使用经验](research/yadof-condor.md)。补 R0/R2 的线程环境、字段引用、资源单位、slot、传输与超时探针，区分已解决事故、撤回方案及旧部署特例；本次未运行作业或修改机器配置。
- 已据后续讨论维护 [部署合同](deployment-layout-plan.md#开发安装与正式部署)：开发机使用系统 Python editable 引用，稳定部署和发布验收普通安装 wheel；补重装/服务重启时机、源码账户访问及安装来源检查，项目配置保持统一。R0/R5 与 Condor R2/R4 的完成条件已同步，尚未实际安装或验证运行行为。

## 待核与边界

- 11 月 6 日查询曾因缺少配置源退出；11 月 7 日只读复核已见注册表配置入口，但未重跑 Condor 查询。配置、认证、执行账户与路径访问按 R0 实测。
- embedding 峰值预算、作业外启动方式、同模型跨项目单实例、普通作业生命周期及两链真实 GPU 并行尚未验证。
- 记忆任务 P0/P1 复用本任务 R0 的包/配置入口，P2 接入 R1 的共享 embedding 客户端；本任务用合成请求验收，不等待记忆索引、建图或数据库实现。

## 下一步

1. R0 继续提取最小 runtime、标定预算；复核 slot 账户实际包加载位置与参数边界。
2. embedding 探针通过即推进 R1；Condor 作业和账户/路径探针通过即推进 R2，GPU 准入待 E/S 标定后启用。
3. 两链完成后执行 R3 真实并行，再完成 R4 生命周期回归、R5 普通 wheel 换路径交付，实际实现同步 [系统说明](../../system/overview.md)。

详细动作和完成条件在 [计划](plan.md) 维护，本页记录实际状态。系统配置预算尚未更改，不以探针成功替代 R3/R4 联合验收。
