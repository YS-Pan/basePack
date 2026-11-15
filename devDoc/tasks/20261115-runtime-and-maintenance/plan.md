# cuDNN、E与ongoing最终计划

2026-11-15。用户已选择E，本文整合已定的cuDNN、模型32k、柔性9 GiB和ongoing到期归档，是本任务唯一实施计划。本轮只维护文档，尚未实施代码、配置、服务或新机制。历史候选及案例比较保留在[研究报告](research/d-flexibility-20261115.md)，不构成本轮额外实施项。

## 已定范围与完成边界

| 部分 | 已定行为 | 验证边界 |
| --- | --- | --- |
| embedding | CUDA显式cuDNN；模型32768-token上限，超限报错且不截断 | 核实际kernel、token边界、图文和旧向量兼容，不承诺全部合法输入均能在本机成功 |
| 显存与批次 | 9216 MiB（9 GiB）为柔性运行目标；纯文本初始batch4，含图仍batch1 | 允许偶发超标／OOM；约99%是经验目标，不是上线统计门槛 |
| 协调者E | 稳定发布组合helper及同源薄CLI；其余由agent用现有原子工具／普通Python自由组合 | 保留版本、scope、原子发布和宿主生命周期，只合并确定性往返 |
| ongoing | 项目局部持续整改索引；条目默认7天，发现到期即整目录归档 | 到期不等于完成；不自动续期，无定时任务 |

工具面向能判断和调整操作的AI agent。偶发资源失败直接保留原错，由调用者决定分批、修稿或稍后调用；不为极端情况增加调度层或隐式重试。当前生产仍为math／2048／分配器硬限，新publish能力和ongoing均未启用，现行产品文档在实施时随实际行为同步。

## 一、embedding与柔性资源目标

1. 保留当前Windows、ST／PyTorch、同一模型revision／FP16／前处理／pooling。CUDA显式使用`CUDNN_ATTENTION`，不支持时保留原错；CPU沿现有可用路径。用实际kernel跟踪确认，不以`sdpa`字样代替。
2. 在固定Qwen embedding适配层单处声明官方支持上限**32768 token**，按实际attention_mask计数，包含模板、指令和图片token。不从底座／tokenizer的262144推断embedding支持范围。退役机器配置的独立`max_length=2048`及相关消费者、模板和说明；继续关闭截断，超限在forward前返回422并给原请求索引和实际计数。
3. **文本长度统一按实际token判断，退役64 KiB文本字节硬限制**，避免先拒绝合法32k输入；不另换一个字节阈值。HTTP输入结构和现有图片文件／像素、静态图、请求项数合同保持。这是接受范围放宽，不改变旧输入编码。
4. 将embedding节的`gpu_memory_mib`明确为软目标，当前机器仍取9216 MiB；取消以该值设置`set_per_process_memory_fraction`的硬闸及“CUDA必须先有正硬预算才准启动”的旧要求。模板和管理员说明同步改为可按机器调整的软目标示例，不把9 GiB当通用硬件要求。普通Condor作业仍沿其原资源申报／配额合同。
5. 例如约99%的实际正常使用落在目标以内是初始经验目标，少数长输入／大批次可超标。纯文本先保留batch4，含图沿batch1；不为最坏32k×4全局降batch1，不建设动态批次调度。资源不足时接受显式OOM；若失败变成常态，再调整默认批次／日常预留。
6. 突发请求结束后，若留下超过软目标的未使用缓存，按需用PyTorch释放空闲缓存，使突发占用回落；不逐请求无条件清缓存，也不释放仍在用的张量。沿现有日志／实验回执分别记录可得的allocated、reserved和进程口径，不建设百分位监控系统，也不混算这些指标。
7. 现有`/info`同步呈现所选后端、模型上限和软目标语义。上述运行设置不另造向量身份；沿现有identity／input_revision复用未变输入的旧向量。必要数值对照仍保留，身份相同本身不是兼容证明；仅实际分块／输入改变的条目重新编码。

已有cuDNN证据覆盖10k单条／batch4、混长短批、图片／图文和小型检索排序，32k尚未实测。实施时做代表性batch4、实际32768-token单项、超一token拒绝、超过64 KiB但token合法的文本、混长padding及图片／图文检查；保持CPU既有行为。确认kernel并区分显存口径，极限样例超过9 GiB本身不判失败，也不为证明99%扩大试验。

## 二、E：稳定发布能力，agent自由编排

### 唯一新增的组合能力

新增一个稳定Python发布helper及调用同一实现的薄`memory publish` CLI，内部复用现有freeze／validate／apply，保持单一事务实现源。支持首次从完成稿发布，以及接续已有固定frozen两种明确入口。以下参数名为实现示意，功能边界已定：

```text
memory publish --completed completed.json --output frozen.json --control owner.control --result result.json
memory publish --frozen frozen.json --control owner.control --result result.json
```

完成稿输入只需有序的path／文件hash／assignment引用，Python可直接传列表；不建立持久的作者状态库。完成事实由作者对**具体assignment**的显式交付和已有owned handle建立，不要求整个聊天或host turn结束，也不从文件出现推断交稿。

首次发布顺序：核完成稿hash → 按原顺序／scope调用freeze和既有校验 → 独占保存固定frozen → 调用原apply → 返回紧凑结果并保存详细回执。文件字节SHA与apply规范化batch hash分开命名。数据库batch receipt继续是发布权威，本地结果是投影；不另维护一份全项目完成台账。

### 灵活性与失败处理

- prepare／read／neighbors／render及原freeze／apply继续直接可用。已知下一步时，agent可在同一次host exec用普通Python顺序或条件组合；需要看结果才能决定时就返回agent，不预填未来assignment或hold状态。
- 一个明确就绪的稿可以发布；多稿由publisher决定有序合组，冲突后也可改为拆组。多次发布各自原子，不承诺整个组合脚本原子成功。
- 格式、覆盖、证据和语义分块修订回原作者；跨scope／关系判断由publisher或指定作者共读处理。协调者仍可亲自承担有界作者工作。发布结果中的invalidated保留为事实，agent可按需直接查当前状态，不自动转成返工队列。
- 相同frozen的接续／结果核定保持原batch_id与UUID；来源或作者稿确实改变时，经当前prepare／必要阅读产生新path／hash，再新freeze。这两个流程明确区分。
- 输入变化、版本拒绝和其它失败保留原错及受影响位置。未知提交沿既有marker／owner合同处理，保留固定稿，不盲目重投或自动release；本地回执写失败不重新生成新batch。没有明确处理办法的异常直接抛出，不新增通用错误分类或自动恢复器。
- 实际spawn／followup／wait／cancel仍由宿主工具完成，沿fixed layout和已有名额。用紧凑完成回报与宿主事件等待减少无变化轮询，普通成功批仍在作者生成与程序提交后结束。

本轮不实施完整cycle／runner／状态机、B的prepare-dispatch新接口、C的draft-check新接口或F的自动诊断包；原作者修稿、按需查询和自由组合是沿用既有能力，不因此新增一套机制。历史比较见[案例分析](research/d-flexibility-20261115.md)。

## 三、ongoing：随任务触发，到期归档

```text
devDoc/tasks/ongoing/
  README.md                          主题、expires_at投影、匹配职责／路径、状态、链接
  YYYYMMDD-short-topic/plan.md        时间元数据、缘由、客观命中、范围、验证及结束条件
```

每主题只维护一份短计划。主题头是时间字段的维护源，使用带时区的ISO 8601 `created_at`与`expires_at`；默认实际创建后7天（168小时），可明确指定其他有限期限。时间从条目实际创建起算，不从本规划日期起算；本轮不提前创建条目。

未来AGENTS增加一条短指针：

> 修改代码、配置或开发文档时，本任务读一次持续整改索引，发现到期项先归档，再按已确定的工作范围选择有效主题；遇到具体命中时，按主题边界顺手修复或记录。

在本来就需要的阅读、修改与验证中按主题信号核对当前范围，必要时核直接调用方／消费者／相邻测试和文档，完成局部完整修复。以一个明确问题和可独立验证为边界，不设会留下半迁移的文件数硬上限。复杂调查、公共合同改变、数据迁移或生产部署转普通任务，沿现有授权处理。

到期及记录合同：

- `now >= expires_at`即失效；下次正常读取索引发现时处理，不设定时任务。索引显示到期时间投影，创建或明确改期时同步；只核到期候选的元数据与未完摘要，不全读所有正文。
- agent确认到期后，直接把整个主题目录移入现有`devDoc/archive/`，保留原时间并注明归档时间、原因与未完范围；核源／目标冲突，不覆盖既有归档，移除活动索引项并修复直接引用。
- 未完成则标“到期归档，未完成”。普通编辑、命中或一次修复不续期，也不复制新条目绕过期限；明确改期仍保留原created_at。重新启动依据新的需求决定。
- 用户撤销、合同替代或有边界目标真正完成也可归档，分别说明原因。经记忆检索得到的旧主题同样核期限／活动状态，归档内容只作历史参考。
- 无命中不写检查报告；具体处置沿当前任务progress／结果、现有change_log和Git保存，主题不复制事件台账。无所属任务沿总进度登记，记忆疑点仍走memory feedback。
- 当前指令明确禁止文档写入／移动时，只提示到期待归档，已失效主题不再执行；正常允许文档维护时按上述规则直接归档。主题的实际整改始终服从用户本次允许的修改范围。

首批只建两个主题：清理失用的应用层重复控制／无独立职责的回退；补齐现行入口与已完成切换的一致性。它们有已修实例支撑，不预设当前仍普遍有缺陷。保留历史原证、恢复材料和真实协议身份。机制先在本项目使用，不新增通用skill或全仓扫描。

## 实施顺序与必要检查

1. **embedding源码与合同：** 接入cuDNN、统一模型token边界、退役64 KiB和分配器硬闸，同步必要测试、模板和说明。复用现有检查，补上述实际改变行为的回归，按实际资源申报做有限隔离标定。
2. **共享服务部署：** 完成功能和代表性负载检查后构建普通wheel，排空请求并按既有管理员流程部署；核普通安装、健康、实际后端、上限诊断、旧索引查询和资源归还。报告真实资源失败，不宣称全部合法输入都保证成功；保留旧wheel／配置回退入口。
3. **E能力与调用指引：** 实现同源helper／薄CLI，简化协调者prompt和使用文档。只补新增组合、hash核对、首次／固定稿接续及回执投影失败的必要回归，复用现有scope／版本／幂等／owner检查；普通安装验证真实最短发布及直接原子工具仍可用。
4. **ongoing文档机制：** 创建短索引和有期限主题，更新AGENTS与documentation的归属／到期规则。检查有效／到期两个示例、整目录归档路径和引用即可，不搭测试框架或另开agent实验。
5. **逐项交付：** 每个完整改动按既有main提交约定，结果记录实际检查与余项；相关system／产品说明只随已实现行为更新。部署不自动触发一次全项目维护，收益沿后续真实使用观察，不预报token比例。

模型上限、柔性目标、E职责、ongoing时限均已确定；剩余是具体实现与有限负载验证，不是待用户再选方案。当前未实施，不修改项目纲领、不迁移数据库、不全量重算旧向量，也不把计划完成记为功能交付。

## 一致性维护与依据

本轮已清除“待选E”、未选B/C/D/F的实施接口及完整cycle流程；区分assignment完成与整个聊天结束、真实修稿新freeze与相同frozen接续；明确退役会先挡住合法32k的64 KiB限制、处理正硬预算旧准入措辞，并统一过期不等于完成、规划日期不等于条目创建时间。

沿上轮已完成的跨历史检索与实时聊天回读，本轮只定点核计划、现行源码及相关入口，没有追加历史审计或产品执行。已做文档UTF-8、链接／锚点、示例和差异检查。当前源码／产品说明中的旧运行值是尚未实施的现状，实施时按上列步骤同步，不提前改写为已交付。

- [cuDNN与向量兼容证据](../20261106-memory-system/research/efficient-attention-20261115.md)：已测范围和未验32k；[模型卡](https://huggingface.co/Qwen/Qwen3-VL-Embedding-2B#model-overview)的官方32k。
- [协调者token调查](../20261106-memory-system/research/coordinator-token-overhead-20261115.md)与[真实维护案例分析](research/d-flexibility-20261115.md)：E的取舍和必要的临场判断；研究稿中的其它候选仅为历史比较。
- [编码器](../../../experiments/20261106-basepack/src/basepack/embedding/qwen3_vl.py)、[身份](../../../experiments/20261106-basepack/src/basepack/embedding/identity.py)、[CLI](../../../experiments/20261106-basepack/src/basepack/memory/cli.py)、[发布](../../../experiments/20261106-basepack/src/basepack/memory/store.py)与[owner](../../../experiments/20261106-basepack/src/basepack/memory/owner.py)是实施时的对应维护源。
- [文档约定](../../documentation.md)、[file-structure](../../../skills/file-structure/SKILL.md)及用户点名旧项目的toDo合同支持ongoing归属和期限设计；本计划不继承旧项目业务状态或全量加载要求。
