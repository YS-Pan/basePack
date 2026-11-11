# 维护计划与 0.9.1 的一致性核查

2026-11-11。按用户要求逐项对照现行源码、测试、角色提示、配置路径及历史调查，直接修订[维护计划](../automatic-maintenance-plan.md)及[目录约定](../../../system/project-data-layout.md)。保留用户 A/B/F、单项目单维护 thread 和清理方向，D/E 不重新纳入。本次只改文档，不实施候选、迁移或清理。

## 已核问题与修订

| 项目 | 核实结果 | 修订 |
| --- | --- | --- |
| A 固定范围与审核 | 已有固定候选回执、来源/依赖分批、当前聊天采集截点，默认没有全库独立审计步骤；prepare 仍读当时文件 | 已有能力改为沿用；新增限于分类、实际执行边界和收尾，不声称所有文件已在任务开始原子冻结 |
| B 已审处置 | 零行来源无活动知识已可机械登记；非空无新增知识/重复来源仍缺持久处置。source_version 的 UPSERT CONTENT 会覆盖旧字段 | 不重复造空来源机制；新处置需同时进入写入、发现和角色完成口径，并验证保存不会丢失 |
| F 粗细层 | 已有 file/section/chunk、全文快照与范围回读，fresh 全范围 file 会计覆盖；coverage_gaps 未变也反复入队，摘要仍需实际原文块支持 | 不新建分层/原文存储；区分已审处置、表示深度、未读缺口与待细化，衔接候选判定。保留精选 chunks 的依据和 mandatory 标记，不预先承诺减少全文阅读 |
| AGENTS 与升级 | _write_project_entry 已替换 AGENTS 托管块；memory init 核库后 _activate 已刷新 instructions，未刷新 AGENTS；成功块外原字节保留未由现测试证明 | 提取已有块替换并接现有 memory init 路径，不造 force-init、不称离线刷新；补边界和原字节验证 |
| G 锁与停止 | control 短时锁只仲裁 stop/提交入场，解锁后才发送 SQL，不是项目 owner 锁；已获准也不证明已提交 | 保留短仲裁，增量为项目所有权；入口补生命周期条件、owner 限制，释放须核实际执行/事务结果。宿主取消对进程/连接的影响先试验 |
| H 路径与清理 | memory/jobs/凭据位置可配置；source_scope 会绕过 ignore，当前 artifacts 也有受管来源；control/采集收据并非全可重建 | 树改为路径示意，保留实际运行/来源引用；只将可重建工作包移向 tmp。runtime.json 不当客户端必备产物，清理不按目录名一刀切 |
| SQL 与基线 | 后续调查已经核 v4.0.0 tag；32 MiB 只测 HTTP 合成事务，WS/SDK未实测。490b1c2 与公开 release 的 15d17b8 实验树完全一致 | 删除“未核 tag”的过时说明；沿用固定基线并说明与 release 等值，容量仍按最终协议核验，未将 32 MiB 变成 WS 必选 |

## 代码与证据入口

- [maintenance.py](../../../../experiments/20261106-basepack/src/basepack/memory/maintenance.py)：单任务短锁、零行登记、语义候选、coverage_gaps 与完整来源覆盖。
- [store.py](../../../../experiments/20261106-basepack/src/basepack/memory/store.py)：prepare 的实时原件、快照写入、mandatory 默认值、提交版本检查与实际执行。
- [project/init.py](../../../../experiments/20261106-basepack/src/basepack/project/init.py)与[memory/cli.py](../../../../experiments/20261106-basepack/src/basepack/memory/cli.py)：已有块更新及 memory init 刷新；[CLI 回归](../../../../experiments/20261106-basepack/tests/test_memory_cli.py)未证明成功刷新时块外所有原字节相同。
- [coordinator](../../../../experiments/20261106-basepack/src/basepack/memory/prompts/coordinator.md)、[reader](../../../../experiments/20261106-basepack/src/basepack/memory/prompts/reader.md)与[skill](../../../../experiments/20261106-basepack/src/basepack/memory/SKILL.md)：固定候选、生命周期、共读及现有表示完成合同。
- [discovery.py](../../../../experiments/20261106-basepack/src/basepack/memory/discovery.py)、[config.py](../../../../experiments/20261106-basepack/src/basepack/project/config.py)及[SQL 调查](sql-request-size-limit.md)：显式来源、实际路径及上游版本证据。

通过 git diff 核验，490b1c2 与 15d17b8 的 experiments/20261106-basepack 完全相同，实验 tree 为 a5650c8383ad91d5cf0afbdfb3aa1cd353954b16；当前源码、测试与依赖声明相对基线无差异。目录未因计划修改切换，正式安装仍为普通 0.9.1。

三个只读分支的逐行记录选留于本机 `artifacts/runs/20261111-plan-consistency/`；原始中间材料在 tmp 同名目录。实际检查为源码/测试阅读、Git 树/差异和文档链接；没有重跑功能测试或进行新的 SQL/WS 性能试验。另按现行入口启动的正常后台维护不视为这些候选功能已实现，其状态沿专项进度记录。
