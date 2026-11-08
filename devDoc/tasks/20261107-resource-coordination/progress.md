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
| R8.2 | 待实施 | embedding 职责拆分、管理入口与身份合同 |
| R8.3 | 待实施 | jobs/CondorClient、CLI/TOML 命名和提交/进程职责整理 |
| R8.4 | 待实施 | 一次性配置/API 迁移、普通 wheel 源码外功能验收和交付说明 |

R8.0 使用内存替身验证跨项目复用、失败不变性及重复 ID 的结果/取消/清理隔离；未启动模型或改变稳定安装。主 agent 全套检查：`PYTHONPATH=src python -m pytest -q --basetemp artifacts/r80-root-pytest`，27 passed。

## 0.3.0 交付快照

以下沿用 R7 回执，不是本轮重新查询的服务/队列状态；实施升级前须核实际在途工作和运行实例。

- Condor 的 60_resources.conf 维护 12 CPU、24576 MiB RAM、4 个同卡名额和 7164 MiB 普通池；70_job_transforms.conf 维护标准字段转换。背景预留为 9216 MiB，机器 TOML 维护 embedding 自身设置。
- 系统 Python 为 C:/Program Files/Python313/python.exe，普通包在其 Lib/site-packages/basepack。0.3.0 wheel 为 dist/basepack-0.3.0-py3-none-any.whl，SHA256 为 ee19d7ec94be4abc933f58854b62c5129ebf2763db6d42cd95033f40df4ee26a；22 份代码/模板/许可一致，源码与源码外回归各 22 项通过。
- R7 原生 14319–14331 和普通客户端 14332–14334 的调度、CUDA 结果、图文 embedding、取消及资源归还通过。回执最终队列为空，独立 broker 43200 无模型驻留，测试 worker 21732 已退出；服务不是登录自启。
- 原始材料为 artifacts/standard-submit/；R6 为 artifacts/native-condor/。历史时限、测量和合作声明边界见各结果，不据小矩阵、声明额度或测试数量推断显存硬隔离和吞吐。

## 下一步

继续 R8.2 → R8.3 → R8.4，每阶段检查后提交。R8.1 暂保项目 schema 1/[resources]，R8.3 一次切 schema 2/[jobs]。稳定安装和实例迁移集中在 R8.4；站点容量、模型和机器 schema 保持当前合同，远端推送与发布不在本次范围。
