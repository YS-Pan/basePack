# Mandatory 版本信号与证据冲突接续

2026-11-12。对应[计划 C](plan.md#c先让现行前提可靠进入启动)。外部阵列项目仅作只读取证；本次恢复与发布只在隔离小样本执行，不代替其项目的实际 mandatory 修正。

## 原证与归因

选留 `artifacts/runs/20261112-usage-rectification/array-011-final-verification.json` 中，纲领的 `registered_source_revision_matches_current=true`；但 `array-old-mandatory-brief.json` 仍交付 ``member:`core-215d0628a802-file` ``，知识版本 `9991c2b2251246acb86baceb0989f447`，来源版本前缀 `803cafe9`，正文仍为“本次只迁移”，且 `stale=false`、`mandatory_pending_count=0`。读包中的纲领当前来源版本前缀为 `8f012620`。来源登记已推进和旧知识仍已发布可以同时成立。

实际修正错误为 `Evidence source revision mismatch for devDoc/archive/20261110-migration/basepack-test-findings.md`。选留 `array-011-maintenance-summary.json` 明确 `mandatory_correction_published=false`、`failed_batch_not_published=true`。这是保留摘要中的原错，没有独立完整 traceback，不能把它称为本次捕获的原始 stderr。

外部 `tmp/basepack-maintenance/d610b34a88e945ea88427e0646d1a8a4/014fa97890a64a59a2b0320bd31e2e30/` 的 `batch-charter.json`、`reading.json` 和 `reading-charter-refresh.json` 均包含旧 findings 成员的 expected：``member:`core-b57feccdea81-file` `` → `461d037411694441b627f46c18fb36a5`。两次读包的该成员均仅在 neighborhood，以 `stale=false`、旧接受范围 1–162 和旧 source revision 返回；两次 `sources` 都没有报错 findings 文件的当前原文。草稿重写节点实际引用该旧 evidence，却只重接受纲领成员。因此不是已证实的 expected 遗漏，也没有证据可归因为升级中的并发变化。

上述三个外部 JSON 本次仅只读检查，未访问外部数据库。旧 evidence 在升级前已失配的离线 hash 比较沿选留 [prepare-conflict.md](../../../artifacts/runs/20261112-usage-rectification/prepare-conflict.md)，本次没有重复该项备份比较。此前调查及范围见[观察 U4](research/observations.md#u4fresh-mandatory-仍陈述旧迁移范围)；完整原位置/hash 清单在选留目录的 `manifest.json`。

## 状态合同与最小实现

- **发布态：** `stale=false` 只表示这条已发布知识未被显式失效；`mandatory_pending_count` 继续统计该标记。来源登记、向量兼容及 source hash 相同都不能充当作者已理解并接受当前语义的证明。
- **已知版本不同：** brief 用已登记 source metadata，与 mandatory 自身接受来源版本及直接 basis 的保存来源版本比较；单列 `known_unsynced`、`sync_evidence` 和 `mandatory_known_unsynced_count`。basis 比较必须沿其保存的 `source_version`，不能用已经更新的当前 evidence 成员替换它。
- **未知：** brief 不读取业务原件；登记版本相同仅表示没有观察到版本差异。`sync_evidence.note` 明说原件未检查，保留 `change_check` 的发现边界，不给“已同步／现行”的语义承诺。
- **维护候选：** 继续使用既有版本比较、语义回执和未覆盖范围。隔离样本核来源只登记推进后，旧 mandatory 保持可读，`changes --deep` 可无变化，维护仍按知识的旧 source version 留出语义候选；不增平行任务表。

冲突后的最短接续：把错误中的**证据文件路径**显式加入下一轮 prepare，阅读当前原文与保存的旧依据，重接受该 evidence 及需要改写的目标。同批发布，或先发布 evidence 再重新 prepare 依赖。只刷新纲领，或只扩 prepare 但继续复用旧 evidence，均不能完成恢复；expected 与原子发布保护继续保留。

## 隔离回归

新增 [test_memory_mandatory_sync.py](../../../experiments/20261106-basepack/tests/test_memory_mandatory_sync.py)，复用已有确定性 embedding 替身及维护 fixture，真实 SurrealDB 4.0.0 内存引擎位于独立端口 18192，不连接正式项目库。覆盖：

1. 新原文只推进 source 登记，旧 mandatory 知识版本保持；来源 deep 检查已匹配，但语义回执仍包含旧 mandatory 与未覆盖新原文。
2. findings 已在 prepare 之前改变；目标单独 prepare 两次均带旧 evidence/正确 expected，却没有证据当前原文，两次提交均拒绝。显式扩 prepare 但不重接受 evidence 仍拒绝；重读并重接受后交付新 mandatory，旧来源快照保留，旧 expected 草稿继续拒绝。各拒绝点前后比较全部持久表，包括本轮新增知识版本、访问状态及交付记录，均无部分发布。
3. 未发现原件变更时，brief 不调用原件读取，已知差异为 false，但状态保持未知，不宣称新鲜。
4. evidence 已独立重接受后，mandatory 的旧 basis 仍按保存 source version 报已知差异，防止当前 evidence 掩盖旧接受依据。

本轮源码入口 `tmp/basepack-dev/Scripts/python.exe` 已核 `basepack.__file__` 指向 active 源码。最终四项在独立内存库实际执行 **4 passed、0 skipped，10.26 秒**；单独冲突恢复项另为 **1 passed，5.45 秒**。日志选留 `artifacts/runs/20261112-usage-rectification/mandatory-sync/`。开发环境复用已有依赖，不宣称本次按 lock 全量重装；测试调用出现宿主已有 pytest-asyncio 配置弃用警告，不影响四项行为验收。临时数据库由同一 shell 持有，测试结束已停止。

集成后的 read.member 增加动态访问线索，prepare.neighborhood 仍返回保存知识；冲突回归按知识字段投影比较旧 evidence，保留全部持久表不变断言。四项 C 与十一项历史／访问回归在同一隔离内存库联合执行 **15 passed、0 skipped，26.46 秒**，输出为上述选留目录的 `pytest-integrated.log`。

外部实际 mandatory 修正仍未发布，由其项目任务依授权接续；本结果不宣称全库语义候选审计或科学业务验收完成。
