# 0.17 实施结果与验收边界

2026-11-17：N0—N4 源码与配套文档已接入，普通隔离 wheel 已完成真实共享设施闭环；随后新增的 brief 加权稿正在重建与定点验证。正式迁库及本项目显式维护尚未执行，稳定客户端／库仍为 0.16，共享 embedding 服务为 0.15；不能以分支检查或先前 wheel 宣布 N0—N5 全部完成。实际安装位置与库状态由 [部署合同](../../system/deployment.md) 维护，本次切换及恢复事实另见 [执行记录](execution.md)。本轮未推送或发行，GitHub 最新发行仍为 0.16.0。

## 已接入的合同

- N0：独立采集有自己的观察回执与失败，维护明确消费 collection 或 retained；scope 限制实际工作集，包含范围内已登记删除源。长单行支持精确字符定位，prepare 固定实际原件／知识版本。
- N1：作者提交 hash 固定的 prepare 引用及语义选择，程序编译 UUID、版本依赖闭包与 private，沿单 publisher、原子 frozen/apply 和未知提交恢复发布。共享图写目标有唯一 owner，人数按实际工作与容量启用。
- N2—N3：每个首次交付事实（含空交付）推进 J，仅非空推进 C，同 ID 重试幂等；共交付 KL-NMF、逐锚点 Gaussian 和 H/R 增量投影已接线。重训全史重放，不换算旧权重；低权重保留原件、历史、图／索引和训练 ID。
- N4：请求级身份、基础锚点先固定、原证回读、一次评分、纯 rank 和程序生成回执连成一条链，主任务实收后才登记交付。brief 使用有界跨来源／图候选、组内 Gaussian 区间优先及跨组交错，选中项披露模型／游标／区间、计数和遗漏，mandatory 独立。UTC 日只轮换无持久状态的展示采样，不改变 J/C、hits 或年龄，低权重无硬过滤。

产品流程见 [项目记忆](../../../experiments/20261106-basepack/docs/memory.md)，0.16 旧库的离线桥接与切换顺序见 [升级到 0.17](../../../experiments/20261106-basepack/docs/setup-project.md#升级到-017)。rank 8、epsilon .001、beta .2、strength 8 是本次工程初值，未声称效果最优。

## 已观察到的分支检查

分支原证目前在根 `tmp/20261117-implementation/`，主任务交付前选留需要长期复核的部分。本表只记录已返回的实际结果，不将分支通过相加为最终整合通过。

| 范围 | 实际结果与边界 |
| --- | --- |
| CLI、布局与阶段接续 | 191 passed；覆盖独立 collect、明确来源选择、scope 含删除源、弹性人数、固定身份及 stage 当前容量。见 `integration-tests.md` |
| 知识编译与来源 | 采集／内容／发现等 42 passed；隔离 DB 首轮的两项失败修正后 targeted 回归通过，最终提案／发布／private／历史端点／locator 19 passed。见 `knowledge-result.md` |
| 行为与精确版本访问 | 数值及投影 8 passed，历史／访问 10 passed；使用独立内存 SurrealDB，验证 J/C、重试、unknown、首次接受、重放与晚到请求。见 `behavior-result.md` |
| 检索闭环 | 最新 pipeline／selection／startup_overview 回归 31 passed；隔离真实 DB/CLI 闭环 1 passed，B 降至低权重仍能基础召回、再实交付刷新。embedding 使用确定性测试替身；它不是真实共享模型验收。早期分支记录见 `retrieval-result.md` |
| brief 最新加权稿 | 纯逻辑 6 passed，独立实库只读／冷 map 可找回 1 passed；默认 limit 6 时最多精算 48 个候选，总上限 96。仍读取既有概要／投影，不作常数成本或完整覆盖承诺；该稿晚于下行普通 wheel |
| 普通 wheel 与真实共享设施 | 独立 wheel-env 普通安装 `0.17.0[behavior]`，包内 65 文件字节 hash 全一致；源码外新项目完成 49 checks／40 个真实 CLI 步骤，owner=null 且临时 namespace 已删。该 wheel 尚未包含最新 brief 加权稿，不能代替最终重建包验证；见 `normal-wheel-result.md` |
| 配套入口与文档 | `test_project_entry.py` 17 passed；21 份文件的 309 个本地链接／锚点通过（模板链接按目标项目入口解析），最小示例 AST 有效，相关 `git diff --check` 通过。远程 URL 未作为本地检查的一部分 |

普通 wheel 验收使用真实 0.15 Qwen3-VL 共享后端：CUDA0／FP16／cuDNN，实际 worker PID 31000，文本和图片均为 2048 维且 identity 一致。固定 prepare→publish→精确 CRLF 文本及图像 hash 回读／history／neighbors→检索确认→真实 KL-NMF→J=4/C=3 完成。此前两轮失败是验收脚本对 LF 及初始 J=0 的期待错误，修正脚本后在新项目重新通过，未据此改产品。首次模型 import／训练耗时 40.416 秒；该观察不构成性能优化或长期效果证明。

行为测试的最初 fixture 曾使用正式 endpoint 下独立随机 namespace/database，schema 调用超时且结果未明；未进入测试函数或知识／交付写入，可能遗留一个隔离测试库。后续列出的成功均改用独立内存服务；该事件及正式服务恢复由主任务核实，不能把超时当成功或自行清理不明目标。

## 尚待主任务补齐

1. 全产品整合回归、最新 brief／marker 稿的最终 wheel 重建与定点安装验证、生成入口实际刷新；先前普通安装原证按其包 hash 和实际内容保留。
2. 停写后的新鲜导出、独立物理库逐字段桥接／恢复，finalize 内部 verify 通过后显式写 marker 3，再由新客户端 init，正式库与客户端同步切换；保留旧库／wheel 和完整私有恢复链，模型工件一并覆盖。
3. 真实共享 embedding 下的读写／检索及本项目显式维护：按用户本次要求，先取约 100 条候选作为实际使用样本，观察正常作者→发布与实际检索；发现明显偏差先修实现并补必要回归，再做一批，往复验证。100 是本次样本规模，不是产品硬预算或额外语义审计／正式 benchmark；全授权范围仍分批推进。每批实际处置、接受版本、缺口和剩余边界沿 [执行记录](execution.md)／[进度](progress.md) 保存，最终确认父 stop、发布终态及 release。

大规模 N/K/V 的 Gaussian 成本、长期主动发现质量、全部聊天／附件覆盖和参数优劣没有由这些有限检查证明，继续沿真实使用反馈维护。正式结果返回后更新本页和部署事实；计划图保持其 17 日方案身份。
