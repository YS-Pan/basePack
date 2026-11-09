# 旧项目多层次能力核查

2026 年 11 月 9 日只读核查 `D:/project/20261024 doc system`。**已有原文分段定位、语义事实回源、图展开和增量恢复的局部实现；在下述范围未找到文件/章节/段落各层独立摘要向量、跨层父子检索及其完整验收。** 旧实现可提供薄接口和事故依据，不构成本项目交付。

## 核查范围与当前入口

现行产品源码为 [20261102 context](<D:/project/20261024 doc system/20261102 context/pyproject.toml>)，版本 0.8.10；根 `.context-memory/contextctl.py` 调用固定安装副本。本轮没有核维护源与安装副本逐文件一致，也不改变旧任务的活动状态。

定向检查 Context、`20261025 atlas/atlas`、`20261026 lightgraph/src`、`20261027 trial/src` 的源码、README/SPEC、依赖声明，以及必要小测试/回执。搜索 `hierarch`、`parent_id`、`section_id`、`paragraph_id`、`summary_vector`、`summary_embedding`、`multi.level`、summary/parent/children/level、摘要/多层/层级，再读取命中上下文；未扫描数据库、模型、环境或大型运行树。以下是明确范围内的发现，不声称穷尽全部历史文件。

## Context 代码已有什么

| 能力 | 直接证据与边界 |
| --- | --- |
| 结构单元与分段身份 | [segmentation.py](<D:/project/20261024 doc system/20261102 context/src/context_memory/segmentation.py>) 第 20–104、170–193 行：识别 heading/paragraph/table/code 等，按内容、结构路径、重复序号生成 unit/segment ID，复用未变单元并处理相邻边界变化；不是每个章节均有独立聚合身份 |
| 原文分段与语义事实共索引 | [engine.py](<D:/project/20261024 doc system/20261102 context/src/context_memory/engine.py>) 第 819–877 行：segment 写为 normalized-original note，已审事实另写 reviewed-semantics note，带 identity/fact_version、支持来源及原证引文；不是自动生成各层摘要的向量树 |
| 章节路径并不等于章节节点 | [test_segmentation.py](<D:/project/20261024 doc system/20261102 context/tests/test_segmentation.py>) 第 51–55 行：含三个 section 的短文保留为一个 segment，只保存三个 structure_paths；不能把这些路径当作三层分别可检索 |
| 事实与原生块回原文 | engine.py 第 844–859、1389–1422、1551–1598 行与 [delivery.py](<D:/project/20261024 doc system/20261102 context/src/context_memory/delivery.py>) 第 19–34 行：封存精确块映射，按 source_id/version/span/quote 回源，核原始字节及历史/当前有效性，去重精确引用；非唯一/变换文本回父证据，不猜原文位置 |
| 图检索与候选去重 | engine.py 第 1469–1519 行与 [native_public.py](<D:/project/20261024 doc system/20261102 context/src/context_memory/native_public.py>) 第 122–163、198–222 行：原生文字/向量/hybrid 候选按 native type:id 去重，再从种子展开已审关系；未见文件摘要→章节→段落的父子路由或跨表示内容覆盖去重 |
| 变更与恢复 | engine.py 第 95–142、1278–1289 行：来源内容/规范化 hash、metadata_version、语义 needs_review 和冻结 release 恢复；模型/结构/映射也有各自版本。没有三层祖先摘要依赖更新的代码或专项验收证据 |

尤其需要保留区分：旧系统同时检索原文 note 与语义 note，说明它已有多种内容表示；但语义事实不是文件/章节摘要，source→units→segments→native chunks 的加工链也不等于每层各有检索向量和图节点。

## 退役路线与运行证据

- **Atlas 0.1.0：** [query.py](<D:/project/20261024 doc system/20261025 atlas/atlas/query.py>) 第 96–117、782–814 行对 summary、terms、topics 做词法评分并生成有界导航摘要；SPEC 明确查询不调用模型，未见摘要 embedding。
- **LightGraph 0.1.0：** [README](<D:/project/20261024 doc system/20261026 lightgraph/README.md>) 第 26–29、47 行描述固定原文块、claims、跨来源关系和导航摘要；“摘要已实现”不是各层摘要向量的证据。
- **trial 0.2.2：** [core.py](<D:/project/20261024 doc system/20261027 trial/src/lightgraph/core.py>) 第 301–316、648–669 行将 claims/实体/关系/原文块交给 LightRAG，从图命中事实及一跳关系补回 evidence chunks 并去重；是事实图回源，不是文件/章节父子展开。
- **code-simple map：** [required_reading.py](<D:/project/20261024 doc system/20261102 context/src/context_memory/required_reading.py>) 是确定性必读依赖遍历，不打开模型/索引；不能算层级向量检索。

[分段工程总结](<D:/project/20261024 doc system/20261102 context/evidence/storage-upgrade/segments/SUMMARY.txt>) 与相邻 `fixture-final.txt` 保存真实 BM parser/chunker、精确映射和更新失效的工程记录；总结明确不提供正式召回/答案质量结论，结构 fallback 不代表 agent 已读全源。[根安装增量回执](<D:/project/20261024 doc system/20261102 context/evidence/storage-upgrade/root-installed/acceptance/PHASE-increment.json>) 和相邻 health 回执记录旧实例的增量、删除/恢复及新进程查询，不是三层方案的行为验收。本轮仅读原证，没有重新运行测试或加载旧库。

[research-history.md](<D:/project/20261024 doc system/docs/research-history.md>) 第 1286–1291 行把结构父子块和多表示放入未来 V2 比较，并明确该轮只交付计划、未发起运行。不能由历史规划补记为当前已有功能。

## 本项目如何使用

P0 可借鉴精确来源/版本/范围回源、事实 identity 与版本分离、未变片段复用及引用去重，优先复用所选底座的原生能力后再补实际缺口。旧代码的 identity 含内容/结构路径，不能直接承诺新要求中的跨改名/移动稳定成员；原文、摘要和表示输入版本仍按 [现行合同](../plan.md#项目知识与恢复) 独立验证。

不继承旧私有 VL 协议、模型身份、Basic Memory 适配状态机、数据库、任务状态、业务授权或验收结论。多层摘要、各层向量、跨层候选与局部依赖维护仍须按 [P0–P5](../plan.md#阶段与完成条件) 交付；有需要时只提取经核对的薄机制，不从旧项目搬整套运行流程。
