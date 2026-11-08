# R7：标准提交与站点策略交付

2026-11-08，R7 已完成本机部署、原生与普通客户端真实验收，接续 [R6](native-condor.md)，按 [R7 计划](standard-submit-plan.md) 执行。现行状态统一维护在 [进度](progress.md)。

## 实现与部署

普通用户只填写官方 `request_gpus = 1` 与 `gpus_minimum_memory = 3000 MB`。basePack 0.3.0 将既有 `JobSpec.gpu_memory_mib` 转为上述标准字段；源码的提交、capacity 和 GPU 准入已移除内部资源名。capacity 从 `MachineResources` 发现有总量和剩余数量的额外资源，按原名与原生单位展示；CPU/RAM 仍按标准总容量提前准入。

Condor 配置维护源是 [60_resources.conf](../../../examples/condor/60_resources.conf) 与 [70_job_transforms.conf](../../../examples/condor/70_job_transforms.conf)。本机安装在 `C:/condor/config/`，主配置已加载。60 保留 12 CPU / 24576 MiB RAM、同卡 4 个共享令牌和 7164 MiB 普通显存池，背景总预留 9216 MiB；额度只在这里定义。70 使用原生 `JOB_TRANSFORM` 生成内部 `RequestGPUMemoryMiB`，显式向原 `Requirements` 追加资源条件，保留 `RequireGPUs`、架构、系统和传输约束。既有 transform 与 submit requirement 名单按原生宏追加。

本站接受提交时可解析为正数的显存申报，按 MiB 向上取整记账；缺属性时预订整个池。显式零、负值、undefined、无法解析的动态表达式、超池以及多 GPU 请求由原生提交拒绝规则处理，错误仅要求用户理解官方参数。官方显存字段仍筛选设备容量；累计预订是本站约定，4 个名额不代表 4 张物理卡，也不提供显存硬隔离。

切换时先在 schedd 添加临时提交闸门，真实提交确认暂停，核队列为空；备份旧 wheel、60 配置和机器 TOML 到 `artifacts/standard-submit/before/`。旧 broker8060 退出后普通安装 0.3.0，成对部署 60/70 并重载 schedd，再移除闸门并恢复独立 broker18524。slot 容量和定义未改变，未重启 startd。回滚脚本与备份均在该证据目录，回滚须暂停、排空、停止 broker，并成对恢复旧包与配置。

## 原型问题与修正

- 原离线探针输出正确但退出 1 已复现；最小 `SET Probe 1` 也返回 1。与安装版相同的 GitSHA `6c530282` 源码中，[ApplyTransforms 第688行](https://github.com/htcondor/htcondor/blob/6c530282/src/condor_tools/transform_ads.cpp#L688) 为释放广告成功返回 1，[DoTransforms 第767行](https://github.com/htcondor/htcondor/blob/6c530282/src/condor_tools/transform_ads.cpp#L767) 传给 main，第516行直接作为退出码。保留原始非零退出、源码及结构断言；未将该调用记为“退出成功”，也未修改 Condor 安装。
- 首次服务器验收发现 `TARGET` 在该版提交规则中不能正确定位作业。对应 [schedd 第18501行](https://github.com/htcondor/htcondor/blob/6c530282/src/condor_schedd.V6/schedd.cpp#L18501) 以 `SCHEDD` / `JOB` 别名求值；改为显式 `JOB` 后，官方参数拒绝与正常提交均实测正确。失败回执留在 `acceptance-20261108-r7/`，最终回执为 `acceptance-r7-v2/`。
- 用 `unresolved` 区分属性缺失和已存在但求值为 undefined 的表达式，后者不能走整池默认分支。Windows 广告的 `MachineResources` 包含 Swap 却不发布数量，capacity 只展示实际同时发布总量与剩余量的额外资源，相关回归已保留。

## 实际检查

| 场景 | 实际结果 |
| --- | --- |
| 官方字段与原筛选 | 原生 CLI14319 与 Python CLI14320 自动获得 3000 MiB 内部申请，CUDA 矩阵值均256，分配到同卡；14321 保留不满足的 `RequireGPUs`，未执行后取消 |
| 四项同卡及第五项 | 14322–14325 各1000 MiB，共同正确进展重叠16.163秒；14326在尚余3164 MiB、GPU令牌为0时连续排队11.756秒，释放一项后正确执行 |
| 显存总额不足 | 14327占5000 MiB，14328申请3000 MiB时，尚余3个令牌但仅2164 MiB，连续排队11.752秒；释放后正确计算 |
| 默认整池与CPU | 14329省略显存，内部申请7164 MiB；14330仍有3个令牌时因显存为0排队7.481秒；CPU14331无GPU属性正常求和499500；取消14329后14330正确执行 |
| 非法申报 | 零、负值、动态表达式、7165 MiB及2 GPU全部在提交时拒绝，消息使用 `gpus_minimum_memory` 或 `request_gpus` |
| 普通 wheel | 0.3.0系统site-packages安装，22份代码/模板/许可与源码及wheel逐字节一致；源码回归与源码外安装回归均22项通过，含2项原生配置离线回归 |
| 普通客户端与 embedding | 从源码外 `D:/AgentTools` 调用安装包；CPU14332求和499500、GPU14333矩阵256正确并确认清理；GPU14334与4×2048 token embedding联合，2048维归一化向量正确，推理期间6个正确CUDA进展点，取消后同worker21732继续服务 |

原生14319–14331与普通客户端14332–14334均已离开队列，取消和进程清理单独确认，节点资源恢复12/24576/4/7164。证据目录为 `artifacts/standard-submit/acceptance-r7-v2/`，包含转换后ClassAd、事件、进展、正确结果、排队观察及最终清理；联合回执为 `wrapper-receipt.json`。验证同worker继续服务后，显式释放测试worker21732与broker18524，恢复作业树外broker43200，无模型驻留；最终 `final-state.json` 确认队列为空、闸门已移除、加载规则和样例配置一致。

原生小矩阵只验证记账与调度，没有分配申报的全部显存或测吞吐。联合向量测试的PyTorch峰值reserved为8160018432字节，仅是本进程指标，不能代替全卡峰值或硬隔离验证。R0–R6的背景预算标定与生命周期回执仍保留原适用条件。

系统 Python 为既有3.13；Condor附带Python绑定仅有cp39二进制，实际导入原错保存在 `bindings-probe.txt`。本轮Python原生提交指不导入basePack、经subprocess调用官方CLI，未宣称验证bindings API。受限上下文的SSPI原错保留；真实提交、部署和验收使用正常用户上下文，未修改认证政策。

当前wheel为 `dist/basepack-0.3.0-py3-none-any.whl`，35193 B，SHA256 `ee19d7ec94be4abc933f58854b62c5129ebf2763db6d42cd95033f40df4ee26a`。部署回执、wheel逐文件检查及离线原型分别在 `deployment.json`、`wheel-receipt.json`、`offline-receipt.json`。

14份本轮Markdown的UTF-8、代码围栏与107个本地链接目标检查通过，resources skill静态校验与Git差异格式检查通过。本轮分工为客户端/回归、原生验收脚本和使用文档三项，主agent负责配置、真实部署验收与整合；宿主未提供主上下文、团队token及精确往返统计，记为未知。

使用流程见 [资源使用](../../../docs/resources.md)，站点映射、升级和回滚见 [管理员说明](../../../docs/administrator.md)。代码、使用/管理员说明、resources skill、配置样例和本回执已交付。R0–R6历史材料保留当时条件；不扩展到记忆数据库、多物理GPU、MPS或远端发布。
