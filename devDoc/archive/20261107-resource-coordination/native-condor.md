# 通用 Condor 节点与 GPU 共享

路径追溯（2026-11-09）：下文保留当时的运行路径；选留原证现归根 `artifacts/runs/<原批次>/`，原 dist 包现归 `experiments/20261106-basepack/dist/`，位置映射见[布局迁移结果](../20261109-project-layout/result.md)。

2026-11-08 后续批次，接续 [0.1.0 交付](result.md)。用户要求普通任务完全由 HTCondor 管理，basePack 作为普通提交客户端；背景总预留 9 GiB，剩余显存交给普通作业，单卡最多 4 项并行。本批不修改项目纲领。

本页保留 R6 / 0.2.0 的部署与验收条件。后续 R7 已切换为标准提交字段与 schedd JOB_TRANSFORM，现行状态见 [进度](progress.md)，新条件见 [R7 回执](standard-submit-result.md)。

## 职责与实现

- 普通容量只维护在本机 `C:/condor/config/60_resources.conf`：12 CPU、24576 MiB RAM、4 个共享 GPU 名额、7164 MiB 普通显存。背景总预留为 `9216 MiB`，由 `16380 - 9216` 得到普通额度，不再额外扣原 2048 MiB。
- `GPU_DISCOVERY_EXTRA = -extra -repeat 4` 重复同一物理设备的调度名额；`MACHINE_RESOURCE_GPUMemoryMiB = 7164` 定义通用消耗资源。GPU 作业申请 `request_gpus = 1` 和 `request_GPUMemoryMiB = H`，Condor 自动按申报量匹配、扣减、排队及归还。START 保留原策略，并要求 GPU 作业声明正显存；CPU 作业可无 GPU 字段。
- `GPUMemoryMiB` 是管理员定义的资源名，使用官方扩展机制，不是 basePack 专属节点属性。官方 `GlobalMemoryMb` 保留设备容量原义；`gpus_minimum_memory` 只筛选设备，不能代替累计额度。本机 dry-run 另确认 `request_gpu_memory` 不是提交命令，会警告改用 `gpus_minimum_memory`。
- 删除 TOML 普通预算、`budget-config`、预算 hash 与专属节点匹配。`resources capacity` 只读实际父 slot；准入按每个 slot 的总量判断，当前剩余量用于展示，暂时不足交给 Condor 排队。提交追踪字段只属于作业自身，不参与节点容量或策略。
- embedding 自身额度迁到机器 TOML 的 `[embedding].gpu_memory_mib`，独立服务无需依赖 Condor。它与桌面等常驻程序共同使用背景预留；额度是合作约定，作业声明不提供驱动硬隔离。

## 部署与验证

已普通安装 `basepack-0.2.0-py3-none-any.whl`。旧机器 TOML 与专属片段备份在 `artifacts/native-condor/before/`；空队列下停止旧 broker、迁配置及安装包，再平稳重启 startd、恢复独立 broker。实际父 slot 已核发布 12/24576/4/7164，代码、模板和许可共 22 份与 wheel、系统安装逐字节一致。

| 检查 | 实际结果与证据 |
| --- | --- |
| 普通 wheel 回归 | 14 项通过，覆盖总量/剩余量、CPU 无 GPU 属性、原生显存申请及既有生命周期；`artifacts/native-condor/pytest-installed/` |
| 原生作业同卡并行 | 14299/14300 申报 4000+3000 MiB，矩阵值均 256，真实进展重叠 2.811 秒，AssignedGPUs 与 CUDA_VISIBLE_DEVICES 指向同卡 |
| 显存总量排队 | 14301 占 5000 MiB 时，14302 申请 3000 MiB 连续排队 12 秒；父 slot 仍余 3 个 GPU 名额、2164 MiB；前者结束后后者正确执行 |
| 原生作业通用规则 | 缺显存声明的 GPU14303 未执行；无 GPU 字段的 CPU14304 求和 499500 正确；本组全部清理确认 |
| 4 项并行与第 5 项 | 14305–14308 各申报 1000 MiB，同卡真实进展共同重叠 17.509 秒；14309 在尚余 3164 MiB、GPU 名额为 0 时排队 13.263 秒，释放一项后正确计算 |
| 普通提交客户端与共享模型 | 普通 wheel 从源码目录外提交 CPU14310 得到 499500；GPU14311 与 4×2048 token embedding 联合运行，向量维度/归一化正确，推理期间有 5 个 GPU 正确进展点；取消后共享 worker7484 继续服务 |

原生核心证据：`artifacts/native-condor/acceptance-20261108-120702/summary.json`；4 项边界：`four-20261108-120917/summary-four.json`；普通客户端联合结果：`wrapper-receipt.json`。三组本次作业均已离开队列，取消与清理确认；测试模型及旧 broker 已退出，最终独立 broker8060 无模型驻留，节点资源全部恢复。最终状态保存在同目录 `final-state.json`。

wheel 为 35060 B，SHA256 `e4224f4d708e8b534297205d444e2ca75096e0377857063c09c18ce28437aa88`；原 0.1.0 wheel 与历史证据保留。矩阵实际分配很小，显存验收验证声明记账与队列，没有将每份申报额度全部分配；未进行吞吐性能比较。R6 已完成本机部署与验收。

resources skill 静态校验通过；16份本轮 Markdown UTF-8 与117个本地链接目标检查通过，Git差异格式通过。

## 官方依据

- [执行节点与自定义资源](https://htcondor.readthedocs.io/en/25.x/admin-manual/ep-policy-configuration.html)：`MACHINE_RESOURCE_<name>`、`request_<name>`、父/动态 slot 与资源归还。
- [GPU 发现参数](https://htcondor.readthedocs.io/en/25.x/man-pages/condor_gpu_discovery.html)：`-repeat`、`-divide`；后者按整卡容量切分，不自动扣背景预留。
- [作业资源申请](https://htcondor.readthedocs.io/en/25.x/man-pages/htcondor-jdl.html)：GPU 数量与设备属性筛选、自定义资源申请。

部署与使用维护源为 [管理员说明](../../../experiments/20261106-basepack/docs/administrator.md)、[资源使用](../../../experiments/20261106-basepack/docs/resources.md) 与 [模块说明](../../system/modules/resources.md)。历史 R0–R5 保留当时配置和证据，本批结果不替代其原始回执。
