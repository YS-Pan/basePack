# D/I：知识版本与访问交付实现

2026-11-12。源码分支已实现；普通安装、真实业务采用与发布检查由[本任务](plan.md)主 agent 汇总。本分支没有修改生产数据库、启动维护或提交 Git。

## 已实现合同

统一知识图保留 `member`、`node`、`semantic`，新增 `knowledge_version` 保存可寻址的知识版本。SurrealDB 同步 event 在 `knowledge_revision` 变化或记录删除时保存实际前后记录，省略派生 embedding；与业务修改同事务，失败一起回滚。这样覆盖接受、更正、退役、来源删除及隐式关系失效，不依赖作者手写每条旧边的保存语句。原文、图片仍由原来的 `source_version` 和 assets 保存。

新成员的 `parent_version`、关系的 `endpoint_versions.in/out` 保存稳定 ID 加精确 `knowledge_revision`。关系默认绑定本批接受或当前受 expected 保护的版本；作者可显式提供已保留的历史端点。`conditions`、`claim_type` 可用于成员及节点，关系继续保留条件。程序不根据日期、文本相似或权重推断替代。

`knowledge(id, knowledge_revision=...)` 回读摘要、节点或关系的实际版本；`read(..., knowledge_revision=...)` 同时回读其对应原证。`history(id)` 汇集当前、归档和旧 `change.previous` 中有证据的版本，并给出当前版本、该目标最近二十次交付及交付总数。缺少的存量前像不补造，`coverage.complete=false`。历史 neighbors 按端点版本展开；当前记录与归档去重后参与，未留版本 pin 的旧边和子节点另放 `unpinned_edges`、`unpinned_children`，不能当作已证明的精确历史端点。

## 实际交付与权重

宿主在真正交付后调用 `record_delivery(delivery_id, items, context=...)`；`items` 只包含本次实际交付的 `{id, knowledge_revision}`。内部 search、read、neighbors、rank 不推进访问事件。材料单位为独立 member、node、semantic 版本；依据、父子和图邻居不共享强化。修改、位置移动或状态失效产生新知识版本后均从基线开始，不做内容等价继承，避免旧版交付误奖新版，也省去隐含的等价判断合同。

稳定 `delivery_id` 的清单归一化排序去重。相同 ID、相同清单返回已有回执；同 ID、不同清单报错。非空事件原子推进项目全局序号 G，再强化清单版本；空结果保存幂等回执但不推进 G，因为没有实际知识交付可作为本轮调权事实。已有项目数据目录内的独立短锁串行本机调用，数据库事务保证全有或全无；不占语义维护 owner。响应丢失先检查同一 ID 的回执，不盲投。事务已提交但回执读取失败也明确报告结果未知并要求沿用该 ID 恢复。

每个新版本基线为 1，出生事件为当时 G；未留出生记录的旧存量统一按安装基线 0 计算。event 首次保存缺档前像时同样使用 0，避免 G 推进后首次改写使旧版权重无交付复活；不事后推断当年的出生事件，init 也不扫描全图补历史。命中次数 h、最近命中事件 A；从未命中时 A 为出生事件。稳定度 `S=8×(1+h)`，本次候选权重 `w=1/(1+(G-A)/S)`；实际命中令 h 加一、A=新 G，权重恢复为 1。线性增加稳定度让多次交付更耐后续事件下降；8 是可解释的初始半衰事件数，没有模型调用或经过时间输入。未选中的全项目版本随相同 G 精确懒算，不逐轮写全库，也不局限于本次候选或 scope。

`access_hints(items)` 保持材料、顺序和原有分数，仅补 `record_type`、`access_weight`、`access_hits`、`access_event`、`access_stability`、`access_current_event`。search/vector/hybrid、knowledge/read 和 neighbors 的观察输出携带这些线索。该辅助读取只校验身份形状；查询结果本身不证明身份存在，实际交付仍严格核实所指版本。现有 tier1 同次综合评分，rank 不追加脚本权重；CLI、宿主交付确认与 prompt 由检索入口分支接入。

## 启动读取的相关改动

`brief` 只直接读已发布 mandatory、已有 file/section/image 概况和已知缺口；不调用搜索、模型状态、embedding 或原件扫描。`vector_coverage` 明示 `not_checked`。mandatory 的 `stale` 保留发布态含义；另用已登记 source 与该条自身、直接 basis 所保存 source_version 的 revision 比较，提供 `known_unsynced`、`sync_evidence` 及独立计数。登记版本相等仍声明原件未经检查，不把未发现变化写成现行正确性保证。C 分支四项原生回归已通过。

## 实际验证与边界

- 源码解释器核实为 `tmp/basepack-dev/Scripts/python.exe`，import 指向本路线 `src/basepack/`。
- 独立 SurrealDB 4.0.0 内存服务 18191 与随机数据库执行新回归：精确摘要/原文、条件与关系端点、隐式失效及退役中间版本、事务回滚、存量有证与无证缺口、旧版交付不强化新版或父摘要、向量完全不变、空清单和幂等冲突、并发不同及相同 ID、丢响应回执恢复、旧存量改写不复活。十一项新回归及既有 wrong-project 安装回归共十二项通过（14.19s）；懒计算与逐事件全量递推对照。服务已关闭，18191 不再监听。
- 既有 store、历史原证、ID、原生事务、向量覆盖共九十三项首轮为九十通过、一项缺少真实模型设施而 skip、两项失败。两项分别是测试清理未覆盖新表、parent pin 在缺失父节点时提前 KeyError；已修复，包含两项及新回归/向量覆盖的二十项针对性重跑全部通过。
- 存量未保存的历史知识、关系端点和精确历史路径仍可能缺失；原生导入不触发事件。新 schema 不声称恢复这些缺口，不新增当前理解层，也不触发全库语义审计。
- 最终宿主实际交付清单、业务问题采用质量及普通 wheel 安装由主分支验收；仅渲染命令或测试表成功不等于宿主已派工或正确采用材料。

原生 event 的同事务边界参见 [SurrealDB event 合同](https://surrealdb.com/docs/reference/query-language/statements/define/event)。核心文件为 [store.py](../../../experiments/20261106-basepack/src/basepack/memory/store.py)、[schema](../../../experiments/20261106-basepack/src/basepack/memory/schema.surql)、[history.py](../../../experiments/20261106-basepack/src/basepack/memory/history.py)、[access.py](../../../experiments/20261106-basepack/src/basepack/memory/access.py)；永久新回归在 [test_memory_history_access.py](../../../experiments/20261106-basepack/tests/test_memory_history_access.py)。
