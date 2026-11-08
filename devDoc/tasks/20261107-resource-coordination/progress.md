# 资源协调进度

更新：2026 年 11 月 8 日（北京时间）。

## 当前阶段

R0–R7 已完成本机部署和真实验收，稳定安装仍为 0.3.0。R8 按 [维护计划](plan.md) 和 [部署合同](deployment-layout-plan.md) 顺序实施；源码检查与 R8.4 部署验收分别记录。

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

| 阶段 | 状态 | 下一项交付 |
| --- | --- | --- |
| R8.0 | 源码完成 | JobSpec 局部规范化副本；锁内拒绝重复活动 request_id；全套 27 项回归通过 |
| R8.1 | 源码完成 | project/ 唯一源码/模板、按需功能配置、.basepack/ 配置与指令；全套 34 项通过，构建包模板核验通过 |
| R8.2 | 源码完成 | supervisor/模型/所有权及 transport/registry/identity/admin 拆分；全套 51 项通过，机器 CLI 轻量检查通过 |
| R8.3 | 源码完成 | jobs/CondorClient、schema 2/[jobs]、submit/_processes 与单份 spec payload；全套 74 项通过 |
| R8.4 | 实施中 | 0.4.0 wheel 与显式迁移已准备，源码 92 项通过；待系统安装、实例迁移与真实验收 |

R8.0 使用内存替身验证跨项目复用、失败不变性及重复 ID 的结果/取消/清理隔离；未启动模型或改变稳定安装。主 agent 全套检查：`PYTHONPATH=src python -m pytest -q --basetemp artifacts/r80-root-pytest`，27 passed。

## 0.3.0 交付快照

以下沿用 R7 回执，不是本轮重新查询的服务/队列状态；实施升级前须核实际在途工作和运行实例。

- Condor 的 60_resources.conf 维护 12 CPU、24576 MiB RAM、4 个同卡名额和 7164 MiB 普通池；70_job_transforms.conf 维护标准字段转换。背景预留为 9216 MiB，机器 TOML 维护 embedding 自身设置。
- 系统 Python 为 C:/Program Files/Python313/python.exe，普通包在其 Lib/site-packages/basepack。0.3.0 wheel 为 dist/basepack-0.3.0-py3-none-any.whl，SHA256 为 ee19d7ec94be4abc933f58854b62c5129ebf2763db6d42cd95033f40df4ee26a；22 份代码/模板/许可一致，源码与源码外回归各 22 项通过。
- R7 原生 14319–14331 和普通客户端 14332–14334 的调度、CUDA 结果、图文 embedding、取消及资源归还通过。回执最终队列为空，独立 broker 43200 无模型驻留，测试 worker 21732 已退出；服务不是登录自启。
- 原始材料为 artifacts/standard-submit/；R6 为 artifacts/native-condor/。历史时限、测量和合作声明边界见各结果，不据小矩阵、声明额度或测试数量推断显存硬隔离和吞吐。

## 下一步

R8.2 的 22 项 embedding 回归覆盖语义/运行身份、协议、旧 marker 管理、请求隔离、冷启动、空闲退出及 Windows supervisor 崩溃后 worker 回收与重启。机器 CLI 不加载项目配置或模型依赖；当时源码全套 51 passed（`artifacts/r82-root-pytest`），尚未部署。

R8.3 项目 schema 2/[jobs] 已切换；wait 只观察，run 管理交互时限，原生 Condor 时限保留。40 项 jobs 回归覆盖 spec 不变性、单份 payload、复杂 argv/空参数、应用失败、标准字段、资源预检、提交不确定、空查询和取消回收；全套 74 passed（`artifacts/r83-root-final-pytest`）。

R8.4 已准备 0.4.0 普通 wheel（30 份包文件与源码逐字节一致）与显式 `migrate --from-config`；配置/迁移回归 28 项，全套源码 92 passed（`artifacts/r84-source-pytest`）。升级前实际检查见 `artifacts/r8/before.json`：系统 0.3.0 普通安装，旧 broker 43200、无 worker，队列为空，12CPU/24576MiB/4名额/7164MiB 全部可用。找到六份既有源码外试用配置；本轮不接管业务旧库，历史 artifacts 保留原版证据。

下一步用旧安装停止服务，普通安装新 wheel，显式迁移六份配置并做源码外两项目功能验收。稳定安装目前仍为 0.3.0；站点容量、模型和机器 schema 保持当前合同，远端推送与发布不在本次范围。
