# yadof 的 Windows HTCondor 使用经验

2026 年 11 月 8 日。按用户指定，三名 subagent 分查旧项目 `D:/project/20260414 yadof/20260822 modular/20260822 yadof/` 的管理员材料、开发历史、源码与测试；主 agent 复读关键事故及后继修正。实际目录名为 `dev_doc/`、`admin_tool/`。本次只读，未运行旧测试、Condor、HFSS 或配置工具，未修改旧项目或复用其业务授权。

## 优先入口

- [管理员索引](<D:/project/20260414 yadof/20260822 modular/20260822 yadof/admin_tool/admin_doc/htcondor/README.md>)：区分当前指南、早期调查和 archive。
- [Windows 调试指南](<D:/project/20260414 yadof/20260822 modular/20260822 yadof/admin_tool/admin_doc/htcondor/windows_pool_debug.md>)：提交形态、账户、环境、scratch、产物和排查顺序。
- [7/13 HFSS 控制实验](<D:/project/20260414 yadof/20260822 modular/20260822 yadof/admin_tool/admin_doc/htcondor/20260713_hfss_fix_experiments.md>)：最终根因与真实作业结果，取代 7/9–7/12 的未决猜测。
- [pool 工具说明](<D:/project/20260414 yadof/20260822 modular/20260822 yadof/admin_tool/htcondor_pool/README.md>)：当前旧部署的 slot、资源单位及 starter 配置。

## 容易误用的行为

| 经验与证据 | 对 basePack 的含义 |
| --- | --- |
| **线程环境不是只由提交者设置。** 7/13 的 HFSS 2024.1 profile 08 在 starter 注入 `OMP_THREAD_LIMIT=2` 时崩溃；仅从 worker 的 `STARTER_NUM_THREADS_ENV_VARS` 排除此项即可通过。提交空值又被填成 2，全部改成 1 也不是修复。[成功与控制矩阵](<D:/project/20260414 yadof/20260822 modular/20260822 yadof/admin_tool/admin_doc/htcondor/20260713_hfss_fix_experiments.md:30>) | R0 查看实际 slot 和最终线程环境，不能把提交字符串当作最终环境。HFSS 排除项是特定兼容修复，不作为所有负载的默认配置。 |
| **不同 submit 字段有不同引用规则。** 7/22 真实 input-transfer hold 来自带空格 AEDT 文件名外围的双引号；当前适配器保留空格原文、拒绝逗号/换行。environment 的整串引用、变量分隔与 transfer list 又不同。[事故](<D:/project/20260414 yadof/20260822 modular/20260822 yadof/dev_doc/change_records/20260722_193000_condor-matchmaking-diagnostics.md:13>)、[字段合同](<D:/project/20260414 yadof/20260822 modular/20260822 yadof/dev_doc/blueprints/20_files/src/yadof/evaluate_manager/condor_runner.py.md:54>) | R2 分别实现 executable、arguments、environment 和文件列表编码；普通 shell 引用不能当作所有字段的通解。旧适配器没有通用 arguments 编码器可直接提取。 |
| **内存、磁盘裸数单位不同。** 旧资源模块内部采用 memory MiB、disk KiB，写出显式 MB/KB；pool 工具的两项参数虽都叫 MB，写 DISK 前乘 1024。[资源解析](<D:/project/20260414 yadof/20260822 modular/20260822 yadof/src/yadof/evaluate_manager/resource_requests.py:26>)、[机器配置转换](<D:/project/20260414 yadof/20260822 modular/20260822 yadof/admin_tool/htcondor_pool/htcondor_pool.ps1:618>) | 公共资源声明采用明确单位，边界只转换一次；request_disk 还需涵盖实际 scratch/输入/输出需求，不能只照抄数字。 |
| **一个 slot 不一定串行。** 当前旧工具配置一个 partitionable 父 slot，再按请求分 dynamic slots；`request_cpus` 也不等于应用绑核或自动设置 solver 参数。[slot 配置](<D:/project/20260414 yadof/20260822 modular/20260822 yadof/admin_tool/htcondor_pool/htcondor_pool.ps1:607>)、[CPU 解释](<D:/project/20260414 yadof/20260822 modular/20260822 yadof/admin_tool/admin_doc/htcondor/20260712_official_docs_deep_dive.md:234>) | R0 核父/动态 slot 的实际资源；普通 GPU 作业的排队靠 GPU 分配，不靠误解 NUM_SLOTS。应用仍按约定控制自己的并行。 |
| **pool 可查、提交凭据成功、实际运行身份相互独立。** `condor_store_cred` 成功不证明任务作为 owner 运行；旧多工作站政策为 slot user + load_profile，不能自动继承为本项目的账户政策。[指南](<D:/project/20260414 yadof/20260822 modular/20260822 yadof/admin_tool/admin_doc/htcondor/windows_pool_debug.md:34>) | R0 由 payload 实测身份、解释器、cwd、profile/temp、文件和 endpoint 访问。slot profile 的可用性不能当作跨任务应用设置持久化。 |
| **执行目录、提交 staging 与回传目录不是同一个概念。** 缺省输出发现不扫描子目录；显式输出清单中的缺件会导致 hold。yadof 最终要求成功/失败均产出 flat rawData.zip 和 metadata；这是应用合同，不是通用任务格式。[当前指南](<D:/project/20260414 yadof/20260822 modular/20260822 yadof/admin_tool/admin_doc/htcondor/windows_pool_debug.md:101>)、[最终传输决策](<D:/project/20260414 yadof/20260822 modular/20260822 yadof/dev_doc/change_records/20260722_205523_restore-dev-doc-and-flat-condor-rawdata-transport.md:27>) | R2 明确文件访问/回传方式，验证嵌套输出与失败诊断可取回；模型和环境不作为任务 payload 复制。完成事件也不能代替应用退出码与有效结果。 |
| **时限与清理不能由一个调度字段证明。** 7/24 记录过四个任务超执行预算数小时仍被等待，遂补提交侧有界等待；实际执行段从 execute event 开始，提交时刻还包含排队/传输。旧代码即使 condor_rm 失败也可返回 timeout。[真实事故](<D:/project/20260414 yadof/20260822 modular/20260822 yadof/dev_doc/change_records/20260724_092211_submit-side-distributed-job-timeout.md:5>)、[回收实现](<D:/project/20260414 yadof/20260822 modular/20260822 yadof/src/yadof/evaluate_manager/condor_runner.py:1500>) | 本工具分别定义排队、执行、观察期限，并验证客户端不会无限等；报告 timeout 与确认进程树已回收是两项结果，清理失败必须保留。 |

## 后继修正与适用边界

- **解释器形态不是平台定律。** yadof 7/9 撤销“Python 作 executable”的旧建议，改为传输并直跑 workflow.py，依赖执行机文件关联及 ACL；同日 smoke 还遇到未配置关联的 worker。basePack 的显式系统 Python 仍须实测，明确 `transfer_executable`，不把已安装解释器连同大环境传进 scratch。[后继决定](<D:/project/20260414 yadof/20260822 modular/20260822 yadof/dev_doc/change_records/20260709_173000_htcondor-direct-workflow-submit.md:8>)
- **重试不是已有的原生保证。** 7/17 的旧安装将 native resource-retry 设置报 unused，实际改成 yadof 删除旧 cluster、增加额度、从头提交新 cluster；8/15 恢复 native 的 TODO 是过时而未执行即归档。本工具不继承该重试状态机，需按安装版本验证实际接受的原生设置。[当时修复](<D:/project/20260414 yadof/20260822 modular/20260822 yadof/dev_doc/change_records/20260717_193325_move-resource-retries-into-yadof.md:5>)、[归档原因](<D:/project/20260414 yadof/20260822 modular/20260822 yadof/dev_doc/change_records/20260815_170021_add-recording-consistency-guard-and-retire-stale-todos.md:22>)
- **7/22 中间方案已撤回。** 当日 19:30 的 launcher/runtime zip 在 20:55 被撤销；保留该记录中的真实引号和 no-match 事故，不继承后来废弃的 worker 包装。暂时无匹配时可用原生 better-analyze 提供等待原因，不自动把排队判失败。[最终决定](<D:/project/20260414 yadof/20260822 modular/20260822 yadof/dev_doc/change_records/20260722_205523_restore-dev-doc-and-flat-condor-rawdata-transport.md:27>)

主 agent 于本次另核 [HTCondor 作业环境](https://htcondor.readthedocs.io/en/25.0/users-manual/env-of-job.html) 与 [submit 参考](https://htcondor.readthedocs.io/en/25.0/man-pages/condor_submit.html)：手册支持自动线程变量、请求单位、可执行文件传输及输出发现/缺件 hold 等通用机制；HFSS 崩溃、空值重注入和超时事故来自旧项目实测，不能由手册推成所有版本和负载的现状。

覆盖的是按主题选读的指南、变更、实现及测试，不是旧项目全量审计；未重跑原始 jobs/temp 中的实验，也未核当前机器有效配置。本工具的实际验收仍按 [R0–R5](../plan.md) 执行；详细运行证据留在原项目，不复制旧运行树。
