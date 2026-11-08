# 资源协调进度

更新：2026 年 11 月 8 日（北京时间）。

## 当前阶段

R8.0 → R8.1 → R8.2 → R8.3 → R8.4 已依次完成并在 main 提交。当前稳定安装为 0.4.0 普通 wheel；显式迁移、源码外功能和生命周期验收完成，见 [R8 结果](maintenance-result.md)。接口和位置合同见 [维护计划](plan.md) 与 [部署合同](deployment-layout-plan.md)。

记忆检索、建图和数据库尚未交付，由 [独立任务](../20261106-memory-system/plan.md) 接续。记忆 P0 的底座比较与资料准备可以并行，不等待全部作业改名。

## 已交付

| 批次 | 完成范围与证据 |
| --- | --- |
| R0 | 包、配置、模板、init/config show/doctor，editable/普通 wheel 与设施探针，见 [R0–R5 结果](result.md) |
| R1 | 跨项目共享模型、请求取消/截止、空闲与故障生命周期，见 R0–R5 结果 |
| R2 | Condor 提交/状态/等待/取消、UTF-8 参数桥接，见 R0–R5 结果 |
| R3 | embedding 与普通 GPU 任务联合运行及资源准入，见 R0–R5 结果 |
| R4 | 作业树、共享服务隔离和清理故障回归，见 R0–R5 结果 |
| R5 | 普通 wheel 源码外两项目、移动、新检出及联合验收，使用文档和 resources skill，见 R0–R5 结果 |
| R6 | 通用节点容量、4 个同卡名额与 7164 MiB 普通显存记账，0.2.0 验收见 [结果](native-condor.md) |
| R7 | 官方 GPU 提交字段、schedd 原生转换/拒绝和原筛选保留，0.3.0 验收见 [结果](standard-submit-result.md) |

## R8 状态

| 阶段 | 状态 | 实际交付与阶段检查 |
| --- | --- | --- |
| R8.0 | 完成 | JobSpec 局部规范化副本；锁内拒绝重复活动 request_id；全套 27 项回归通过 |
| R8.1 | 完成 | project/ 唯一源码/模板、按需功能配置、.basepack/ 配置与指令；全套 34 项通过，构建包模板核验通过 |
| R8.2 | 完成 | supervisor/模型/所有权及 transport/registry/identity/admin 拆分；全套 51 项通过，机器 CLI 轻量检查通过 |
| R8.3 | 完成 | jobs/CondorClient、schema 2/[jobs]、submit/_processes 与单份 spec payload；全套 74 项通过 |
| R8.4 | 完成 | 0.4.0 普通安装、六配置迁移、源码外两项目及真实图文/作业/生命周期；源码与源码外各 92 项通过 |

## 0.4.0 当前交付

- 系统 Python 为 `C:/Program Files/Python313/python.exe`，普通包在其 `Lib/site-packages/basepack`。wheel 为 `dist/basepack-0.4.0-py3-none-any.whl`，42319 字节，SHA256 `3322c8eebfcd0a12a4518639cf66e7a202fa76d6a47fa7b34be80cdecab15563`；30 份代码/模板/许可与源码、wheel、安装一致，旧源码入口已移除。
- 用旧安装停止并确认旧 broker 退出后一次安装。六份既有源码外试用配置显式迁到项目 schema 2/[jobs]，备份/映射保存在各项目 `.basepack/migration/`；新两项目、深层中文/空格配置、任意 cwd、移动、新检出及所有模板/轻量命令通过。
- 作业 14335–14338 实得 CPU 499500、应用退出 7、GPU 256；真实图文向量为 2048 维且归一化，GPU 进展与实际 forward 重叠。请求取消/截止、作业取消、另一项目服务存活、日志、原生历史及进程回收均通过。
- 真实已加载模型的 supervisor 崩溃回收、锁释放、冷恢复、正常停止和原配置 300 秒空闲整进程退出通过。2026-11-08 17:07 北京时间最终实查：supervisor 17804、无模型 worker，运行与磁盘部署指纹匹配，队列为空；12CPU/24576MiB RAM/4同卡名额/7164MiB普通池全部可用。服务仍非登录自启。
- 机器 schema 1、模型及共享状态物理位置保持；机器 TOML 和 Condor 60/70 的 SHA256 与升级前相同，背景预留仍为 9216 MiB。本轮未重新标定额度或吞吐，历史额度证据继续见 R6/R7。

回执集中在本机 `artifacts/r8/`，源码外实例为 `D:/project/20261108-basepack-r8-acceptance/`；详细位置和边界见 R8 结果。旧 0.3.0 wheel 保留在 `dist/` 可供恢复，原交付条件见 [R7 结果](standard-submit-result.md)，不把旧 PID 或队列快照作为当前依据。

## 下一步与边界

R8 无未完成验收项。继续 [记忆 P0–P5](../20261106-memory-system/plan.md)，本轮不实现记忆数据库或继承旧业务知识/授权。历史 Condor ClassAd 保留原绝对路径，项目/数据迁址后的旧 status 不保证可用，按迁移备份和映射回查。远端推送与发布不在本次范围。
