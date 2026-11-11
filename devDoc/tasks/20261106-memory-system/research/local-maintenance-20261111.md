# C：现有局部维护与相关知识判断

2026-11-11。回应用户对[成本方案 C](maintenance-options-20261111.md)的疑问：现行 0.9.1 已有图数据库，也已做部分局部维护，不应将这些基础能力重复包装成新功能。本文只读源码及既有回归，未运行测试或修改实现。

## 已实现的“相关”

| 判断依据 | 现有行为与边界 |
| --- | --- |
| 原文版本与位置 | 来源按原始字节 SHA-256 识别版本；行比较仅归一化 CRLF/LF。非 stale、无依赖 basis 的旧块在 equal 行范围、唯一定位且标题/父上下文满足条件时可复用，不是单凭文字相同就全部复用 |
| 层级及证据 | 以已记录的 parent 和 evidence/basis 找到依赖某块的摘要或表示；受影响集合可沿父级和成员依据继续扩展 |
| 已有图关系 | SurrealDB 的 node、semantic 原生关系及成员端点、保存的依据，用于取得相关节点/边与维护已知依赖；机械来源按证据闭合共同发布 |
| 向量输入 | 同成员的编码输入版本与 embedding identity 一致且向量存在时复用；不等于任何文本位置变化都无需编码 |

实现依据：[content.py](../../../../experiments/20261106-basepack/src/basepack/memory/content.py) 的版本与 line_changes；[maintenance.py](../../../../experiments/20261106-basepack/src/basepack/memory/maintenance.py) 的机械复用、来源依赖组与语义候选；[store.py](../../../../experiments/20261106-basepack/src/basepack/memory/store.py) 的 prepare、_affected/_expand_affected、basis、RELATE 和 neighbors；[candidate_vectors.py](../../../../experiments/20261106-basepack/src/basepack/memory/candidate_vectors.py) 的向量复用。

原件变化本身不立即撤回已发布知识；退役、更正等按实际合同处理依赖失效。不能把局部维护解释成任何源变化都立即 stale。既有回归见[test_memory_maintenance.py](../../../../experiments/20261106-basepack/tests/test_memory_maintenance.py)与[test_memory_anchoring.py](../../../../experiments/20261106-basepack/tests/test_memory_anchoring.py)。

## 仍然需要 AI 判断的部分

新增一条要求时，旧块可以不变，但文件摘要是否要改、新要求是否与另一文件冲突，需要理解含义。即使两份材料原先没有边，新内容也可能建立新关联；沿已有边只能找到已记录关系，不能保证发现尚未建出的边。

prepare 仍可交付整份新旧原文及既有邻域，AI 共读后决定语义边界、摘要和有依据关系；程序没有保证所有语义影响都能自动收敛成“只读变动几行”。因此 C 当前作为已有能力保留和说明，本轮不另立语义影响分析或全图调度改造。
