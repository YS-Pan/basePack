# cuDNN、协调者流程与持续整改计划

2026-11-15，讨论稿。用户要求先讨论并制定计划，不实施。本轮只保存计划与入口；以下命令名是拟议接口，当前产品不提供。源码、prompt、AGENTS、机器配置、共享服务和记忆发布流程均未改。

## 目标、已定方向与待选项

| 项目 | 本轮确定的方向 | 待确定／待验证 |
| --- | --- | --- |
| embedding | CUDA 采用 cuDNN attention，取消人为 2k 限制，按模型官方 32k 上限明确拒绝超限，不截断 | 32k 的真实负载验收、批次与部署参数 |
| 协调者 | 减少确定性步骤的模型往返、重复正文和短轮询，保留必要语义工作 | 下列 A–D 的组合由用户选择 |
| 持续整改 | 在正常任务接触相关材料时识别并处理分散的小问题 | 推荐下述 ongoing 目录和触发合同，尚未启用 |

不以协调者／reader 的固定 token 比例作为目标。已有调查中协调者兼任作者、整合、发布和恢复，缓存输入反复累计；要减少的是可定位的无效往返和上下文负担。模型档位暂不作为本轮改变对象。

## 一、embedding：cuDNN 与模型上限

### 拟议行为

- 保留现有 Windows、Sentence Transformers、PyTorch 和同一模型 revision／FP16／前处理／pooling。CUDA 显式选择 `CUDNN_ATTENTION`；CPU 保留原有可用路径。CUDA 后端不支持时保留原始错误，不静默转回高显存 math。
- 实际上下文上限为 **32768 token**，包含模板、指令和图片 token。在固定 Qwen embedding 适配层单处声明官方支持上限；不从底座 `max_position_embeddings=262144` 推断。退役机器配置中独立的 `max_length=2048` 及其现行说明，按实际 attention_mask 在 forward 前执行模型上限检查。
- 继续关闭截断，保留原请求顺序的超限索引与实际 token 数。tokenizer 的配置值／warning 不代替服务拒绝；不通过截断掩盖来源分块问题。
- 初次开放完整 32k 时，建议请求内推理先用 **batch1**，保留现有 9 GiB 显存预算和普通 Condor 池分界。单次 HTTP 请求仍可容纳多项，逐项编码；不把 32k×4 作为本轮承诺，也不先建设动态批次调度器。
- 文本字节、图片文件／像素等请求限制独立于 token 上限。实施时核对现有 64 KiB 文本限制是否妨碍目标输入，明确保留或调整的请求边界；不宣称改了 token 上限就取消全部输入限制。
- `/info` 可直接呈现实际设备、attention 路径和支持上下文，避免用户从 `sdpa` 字样猜后端。运行设置不另造向量身份；旧输入未变时，沿当前 identity／input_revision 合同复用旧向量，必要数值检查不以 identity 相同替代。

### 证据与实施后的完成条件

已测 cuDNN 的 10k 单条／batch4 张量峰约 4.49／6.02 GiB，后者 reserved 约 6.74 GiB。22 组文本／2k／图片／图文配对最低余弦约 0.9999889；6 查询×16 候选的新查询接旧索引及全新向量组合，完整排序均一致。这些是局部工程证据，生产仍是 math／2048／batch4，32k 尚未实测。

实施时按顺序：

1. 在唯一源码适配层接 cuDNN、模型上限及相关配置／文档，保持 CPU 行为；只为改变的行为补必要回归。
2. 隔离资源作业核实际 32768-token 输入、超一 token 的 forward 前拒绝、混长 padding、图片／图文和既有数值兼容。跟踪实际 kernel，逐 case 重置显存峰值，区分 allocated／reserved／进程总量。
3. 32k batch1 在预算内通过后，再构建普通 wheel、排空共享请求并按既有管理员流程部署。核普通安装、共享健康、实际后端、上限诊断、旧索引查询及资源归还；必要时可按旧 wheel／配置回退。

若目标负载不通过，保留真实错误并重估批次／预算，不把 10k 成功外推成 32k 已可用，不擅自扩大 GPU 占用。仅换 kernel／拒绝阈值不安排全量重算；改变分块或实际输入的条目单独重编码。

## 二、协调者：四个可组合的实现选项

当前成功链包含：作者完成 → 必要共读／跨稿整合 → freeze → 文件 hash → apply → 手记台账 → 下批 prepare／render。`freeze` 已有结构校验；`apply` 已有 batch 身份、规范化 hash、幂等回执、版本检查与原子发布。组合层复用这些能力，不能再造一套发布合同。

| 选项 | 具体改变 | 主要减少的负担 | 相对成本 |
| --- | --- | --- | --- |
| A：一次发布 | 完成稿清单交给一个命令，连续验文件 hash、freeze、保存固定 batch、apply、输出紧凑回执 | 每批 freeze／hash／apply／台账之间原本分开的约四次调用，成功路径合为一次模型往返 | 小 |
| B：一轮派工包 | 协调者一次给出多个明确 assignment，脚本准备各 reading 包并生成派工清单；正文直接交 reader，协调者拿短索引 | 逐份 prepare／render、重复读取完整 receipt、reading 包后再读相同原文件 | 中 |
| C：作者负责检查与修稿 | 作者交付路径／hash／覆盖；可机械判断的格式检查共用现有规则，作者范围内的错误包直接回原 reader | 协调者代修作者稿、接入大段 traceback／正文，再转述给 reader | 小至中 |
| D：完成事件驱动一轮推进 | 宿主有完成／需处理事件时，一次脚本组合已获语义允许的发布、修订包和已决定的下轮准备 | 短 wait、重复状态汇总，以及每个小步骤唤醒一次协调者 | 中至大 |

### A：最小改动，独立可做

拟议调用：

```text
memory publish --completed completed.json --output frozen.json --control owner.control --result result.json
memory publish --frozen frozen.json --control owner.control --result result.json
```

第一种用于首次冻结并发布，第二种只使用已有固定 batch 接续。完成稿清单保存作者／assignment／路径／文件 hash；完成事实来自宿主已结束的作者事件及 owned handle，文件存在本身不构成交稿。

脚本保存冻结文件后才进入发布副作用；stdout 返回 batch 身份、状态、必要错误和明细位置。文件字节 SHA 与 apply 内部规范化 hash 分开命名。数据库中的 batch receipt 是发布权威，本地结果文件是投影；提交成功但本地回执写失败时，可按原 batch 核定并恢复投影，不能因此重新 freeze 或重投新 batch。

### B：减少协调者反复装载正文

```text
memory prepare-dispatch --receipt fixed.json --control owner.control --assignments assignments.json --output round.json
```

每个 assignment 的来源范围、reader slot 和需要共读的依赖由 agent 明确决定。脚本批量调用现有 prepare、写各自 reading 包并调用现有纯 prompt 渲染；原 prompt 渲染函数不新增隐式数据库访问。外层索引只含路径／版本、scope、private 标记、包位置、精确 task_name／model／effort 和原始错误。

reader 直接使用准备包，依合同补读必要依据；准备后发生变更仍由发布版本检查拒绝。协调者需要原文判断关系时按需共读，不把“减少重复读取”变成禁止阅读。

**脚本不能代替宿主派出订阅 agent。** 清单是待派工，宿主仍须实际 spawn／followup，保留已启动名称、名额、handle 与生命周期。不要通过新增 LLM API、数据库任务队列或调度服务规避这个边界。

### C：错误回原作者，发布权保持

共用结构规则，而不是再运行一遍完整 apply 或增加模型审稿。可选 `draft-check` 从 freeze 提取共用形状检查，输出最小错误定位及完整原错文件；不调用 embedding、不认定语义合格、不提交临时 UUID。

格式、原作者证据／覆盖、语义切块等修订回原 reader，重新 prepare 后生成新路径与 hash。跨稿 expected 冲突、重复 source、关系两端或结论冲突，仍由协调者共读整合。脚本不自动改 expected、接受 stale evidence 或机械截短原文。

### D：更完整的一轮推进，可后置

```text
memory cycle --receipt fixed.json --control owner.control --completed events.json --assignments next.json --output cycle.json
```

复用 A/B 的函数，输入仅包含宿主确认的完成事件及 agent 已决定的后续 assignment，返回 `published / repair / dispatch / unresolved` 短索引。多个批次各自原子发布，整轮并非一个事务。

先可只调整完成回传与宿主等待协议：无新事件不重复装载全队状态，不为等齐一波而延误异常或空闲 slot。不用阻塞 Python 轮询替代宿主可取消生命周期；完整 cycle 在 A/B 的价值和恢复路径清楚后再选。

### 建议选择与共同完成条件

建议先选 **A+B+C**；D 先用宿主完成事件改善等待，完整 cycle 暂后置。若希望最小改动，可先仅 A，再按真实日志决定 B/C。暂不更换协调者模型，不添加一层 LLM 发布员，也不强制协调者／reader 用量达到某个比例。

所有选项保留：单 owner／control、唯一 publisher、作者 scope、语义关系两端共读、原文与知识版本检查、实际向量准备、private 边界、原始异常、未知发布保留所有权，以及 stop 后已获准发布结束才 release。错误局限于受影响批；无关已确认成功不返工。反馈只有在 agent 明确判断 outcome／依据后才能结案，发布成功不自动清空反馈。

所选实现只做对应必要回归：跨稿引用与身份不变、固定 batch 幂等、冻结后中断、数据库已提交但本地回执失败、局部版本冲突、stop 前后 admission 和未知结果恢复。普通维护由作者生成与程序提交闭环结束，不新增发布后逐项语义审计。

效果沿后续真实维护日志核对：协调者模型事件／上下文、全队 token 分项、原始错误和返工、有效覆盖、停止响应及耗时分别记录。不预报节省百分比，不为证明省 token 另开全项目维护或本机模型质量对照；真实收益继续由用户使用反馈判断。

## 三、随任务进行的持续整改

### 推荐的最小结构与触发

```text
devDoc/tasks/ongoing/
  README.md                          短索引：主题、匹配职责／路径、状态、链接
  YYYYMMDD-short-topic/plan.md        缘由、客观命中、边界、验证及结束条件
```

复用 tasks 的持续目标子类，不新增顶层 archive 或另一套维护服务。每主题一份短计划即可；主题退休时连同目录整体归入现有 devDoc/archive。一次小修完成不等于持续主题结束，也不按年龄自动过期。

未来 AGENTS 只增加一条指针，候选文字：

> 修改代码、配置或开发文档时，本任务读一次持续整改索引，按已确定的工作范围选择相关主题；遇到具体命中时，按主题边界顺手修复或记录。

按主任务读一次索引，必要主题随子任务 brief 交接。在本来就需要的阅读与验证中，按主题的客观信号核对当前范围；发现可证明的问题，再核直接调用方、消费者和相邻测试／文档，作局部完整修复。用户要求只读、讨论或不实施时，这个机制不增加修改授权。

### 范围、记录与退出

- 不为找命中而全仓扫描，不要求每轮收尾比较所有主题；无命中不写“已检查无问题”的记录或汇报。
- 以一个明确问题、当前职责和可独立验证的完整修复为边界，不硬设一至两个文件上限而留下半迁移。需要独立调查、改变公共合同、数据迁移、生产部署或跨项目动作时，记录后转普通任务，沿既有授权处理。
- 具体发现与处置只沿当前任务 progress／结果及现有 change_log／Git 保存。主题文档不复制每次事件台账；无所属任务沿总进度登记，后续只有新证据／状态变化才重报。
- 一次命中以修复和相称验证完成为止；持续主题在用户撤销、合同替代或有边界目标真正完成时归档。没有命中次数、行数下降或额外审计的验收指标。
- 记忆返回／漏检的知识疑点继续走 `memory feedback-report`；本机制承接源码／配置／现行文档的整改目标，不另造与记忆反馈竞争的问题队列。

首批建议两个主题：①清理已失用的应用层重复控制／无独立职责的回退；②补齐现行入口与已完成切换的一致性。依据是本项目已处理的 Condor 重复计时／PID 确认、UUID／旧协议切换及退役试验入口，不宣称当前仍普遍有这些缺陷。历史原证、恢复材料、真实协议字段和仍有效的旧命名不因看似过时被改写。

当前先做项目局部机制，不新增通用 skill。若以后实际跨项目复用，再考虑把通用布局／触发方式并入 file-structure，保留项目主题与状态在本项目。

## 拟议实施顺序与本轮结束

1. 用户选择协调者选项组合，并确认持续整改的目录／触发方案；以上是具体可评审稿，尚非实施指令。
2. 优先完成 embedding 的隔离实现与32k验收，再部署共享服务；同步相关源码、必要测试、模板／现行说明和实际机器配置。
3. 完成所选协调者确定性接口及短 prompt，按局部合同验证后普通安装。部署不自动触发一次全项目维护。
4. 启用 ongoing 短索引、首批主题、AGENTS 单条指针及 documentation 的归属说明；只启用机制，不借机全仓整改。

每个完整修改按既有 main 提交约定交付。实施结果另记录实际检查与余项，不把本讨论稿、探针成功或节点数量当作功能交付。

本轮只读核对当前源码、既有 token／显存调查、旧 auto 合同，并保存此讨论稿；跨历史检索已完成原证阅读、评分与 rank，7项入选。freshness 沿既有 Codex 状态库权限问题未取得全局回执／逐聊天截止点，不作全历史现行性结论；相关当前入口与源码已直接核读。未运行 GPU、产品测试、部署或自动记忆维护。计划检查只核 UTF-8、链接／锚点与 Git 差异。

## 依据

- [协调者 token 调查](../20261106-memory-system/research/coordinator-token-overhead-20261115.md)：职责、约四步发布案例、重复正文、短 wait、版本返工与用量口径。
- [cuDNN 及兼容实测](../20261106-memory-system/research/efficient-attention-20261115.md)：实际 kernel、10k负载、向量／排序对照与未验范围；[Qwen 官方模型卡](https://huggingface.co/Qwen/Qwen3-VL-Embedding-2B#model-overview)标注32k。
- [freeze CLI](../../../experiments/20261106-basepack/src/basepack/memory/cli.py)、[发布实现](../../../experiments/20261106-basepack/src/basepack/memory/store.py)、[owner](../../../experiments/20261106-basepack/src/basepack/memory/owner.py)、[派工渲染](../../../experiments/20261106-basepack/src/basepack/memory/prompts.py)及其 coordinator／reader prompt 是现行职责依据。
- [文档维护约定](../../documentation.md)、[file-structure](../../../skills/file-structure/SKILL.md)与[0.13交付](../20261114-delivery-closeout/result.md)支持目录、记录与既有整改先例。
- 用户点名的旧项目 `dev_doc/toDo/auto` 四份主题及 `dev_doc/skill/toDo.md`、`dev_doc/README.md`：仅借鉴客观触发与局部完整修复，不继承旧业务授权、全量加载或年龄过期规则。本机只读方案草稿选留于 `artifacts/runs/20261115-runtime-planning/`；本计划是后续讨论的唯一维护源。
