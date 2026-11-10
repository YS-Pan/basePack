# 新机反馈与扩库后续的整合分析

2026-11-10。用户总体认同两份[防御性评审](new-machine-defensive-review.original.md)和[CPU向量需求](cpu-vector-requirements.original.md)，并追加持续追新、日常使用免研究实验及tier1/tier2分工要求。两份原稿从 `tmp/20261110 remove defensive/` 原样选留，原文件保留。实施统一从[整改计划](../plan.md)接续，本页只保留采用理由、反证和源码入口。

## 采用与更正

| 主题 | 核对结果及计划采用方式 |
| --- | --- |
| 防御性写作 | 硬件型号/驱动实测、作者未测范围进入日期化开发记录；使用文档交付能力条件、步骤、成功判据和错误处理。评审中“未验收等于宣布不可用”是对阅读体验的归纳，原文未实际禁止其它型号；仍应消除这种伪门槛。 |
| 操作边界 | 等待超时不会结束推理、共享显存峰值、恢复集合等会影响用户动作，继续保留。一次向量成功可作该功能冒烟，不能证明共享GPU任意并存峰值；管理员按实际负载配置预算，用户不重做开发研究。 |
| Python 3.14 | 外部报告在3.13/3.14同为148通过/10失败/43跳过，报告将10项归因为缺embedding extras；3.14文字闭环通过，安装被requires-python挡住。当前pyproject确为`>=3.13,<3.14`。整改解除轻客户端无故门槛并正常安装验证，extras的固定依赖单独核对；不把该报告转写成全功能套件通过。 |
| Condor GPU默认0 | jobs/client.py的GPU字段在纯CPU池是合法可选字段；tests/test_jobs.py已有CPU-only回归。不能按评审把所有`.get(...,0)`改为必需索引；依据MachineResources区分无GPU与真实缺字段。 |
| 提交反查 | client.submit只有查到本次token的ClassAd才取得实际job ID，查不到抛错；恢复有实际用途，保留原始异常且避免二次提交。无需为已取得的job ID新增unverified状态。当前取首个匹配，唯一性和反查失败时保留两层原错按实际路径处理。 |
| 资源预检 | `_check_request`比较本机父slot的total，不是available；测试已有剩余0仍提交的情形。因此评审所谓“并发空闲不足被拒绝”不是已证实故障。去掉重复总量门槛的依据是让Condor负责匹配/准入、减少提交依赖，而非该错误归因。 |
| 清理、时间及超时 | 空PID集进入cleanup确认、max(0)抹平负时间、按英文reason猜超时均有源码路径；按实际原生/回执证据修正并保留回归。无启动与已启动缺回执分开，避免增加一套自造作业状态机。 |
| doctor与CPU | 评审建议缺nvidia-smi即失败适用于要求CUDA的路径；新CPU需求下，缺NVIDIA是合法环境。doctor检查所选后端及模型，CPU/CUDA真实推理由各自短命令验通。 |

上述为源码/现有测试核对，未在本轮重跑新机、Condor或模型设施。评审的P0/P1标签不直接作为全部整改项的阻断级别。

## 原扩库聊天的最新状态及原因

[制定项目记忆覆盖扩展计划](codex://threads/01a1c3bf-8ccd-7983-ba24-0c2e9e2571c4)已结案于`9cd7df2`。重新读取到结案和用户补充，结果以[扩库回执](../../20261106-memory-system/project-coverage-result.md)为准：207来源，三组18/20、20/20、20/20；退役源码修复未安装；完整性、初次地图和原评测限制均有单独记录。

新增的关键问题是摘要可在来源hash正确时夹带来源外的后续事实，版本/许可表述可能滞后，地图按旧入口/历史排列会漏现行前提。它们需要有依据的摘要及启动内容修正，不能用增加来源或分数代替。原评测两次污染、坏审计partial、可能泄盲继续保留，后续定向启动探针不回填原评分。

本次耗时放大来自正式库追新与同材料研究副本归一被串在一起；追新本身是正常使用需求。将研究从使用链移出，并按来源接受、合并变化、局部处理冲突，可以同时允许用户编辑和扩库推进。完成时报告接受版本与残留变化，避免要求动态项目某一时刻全库清零。

## 持续追新的现有能力与最小缺口

当前实现已有prepare同时交付原件、旧source_version、邻域和expected（`memory/store.py:128`），apply核目标/依据知识版本和来源revision并在事务内接受（`:276`），embed按输入revision复用/提交（`memory/vectors.py:14`）。源码可直接支撑按来源小批追新；关系两端需要共读时仍在同一批核据，原件被编辑不要求全项目冻结。

`changes`在事务外读取状态/计算受影响集合，再按ID无条件标stale（`store.py:242`、`:545`），需要交错回归核“旧检测在新接受之后落地”的风险。文件系统与数据库也不存在跨系统原子提交，接受后来源变化检查与关键原件回读仍有作用。检索过滤数据库stale不等于自行检测任意原件变化；热源明确待核，其它current来源继续服务。

[SurrealDB事务说明](https://surrealdb.com/docs/learn/querying/concepts-and-guides/transactions)支持用短事务、版本条件/冲突检测保护接受结果；本项目SurrealKV不按支持serializable的其它引擎来假定能力。[LlamaIndex ingestion实现](https://github.com/run-llama/llama_index/blob/main/llama-index-core/llama_index/core/ingestion/pipeline.py)按ref_doc_id/doc_id和hash决定重处理或跳过，可借鉴按来源增量的粒度；这不是引入该框架或替换现有底座的建议。冲突之后由读取者更新语义依据，不用数据库重试去重放旧判断。

## 模型分工

纲领71–80行已有同读智能分块/边、tier2协调与最多四位tier1、可选批审。原扩库handoff及reader回执显示该组织已实际运行；协调者共读和修正不表示全项未实施。当前项目配置tier1为`gpt-6-luna/max`、tier2为`gpt-6.1-terra/ultra`；底层真实后端身份没有独立证据。Qwen3-VL-Embedding-2B是向量编码器，不是这些智能理解角色。

专项入口存在偏差：随包 `src/basepack/memory/SKILL.md:105` 的广维护仍指向日常默认tier3。计划只修该分发指令和实际派工优先级，不重写通用agent-team的日常默认，也不改项目纲领。

## CPU与排序的一致性设计

当前编码器和服务均强制CUDA（`embedding/qwen3_vl.py:37`、`embedding/service.py:32`）；identity包含FP16/pooling等语义（`embedding/identity.py:9`）。新项目默认text，brief的related直接走文字search（`memory/store.py:517`）；vector查询只要求存在一条兼容向量且仅按distance截K（`memory/vectors.py:71`）。CPU、新默认入口、完整性状态和稳定排序需一起整改。

[PyTorch复现说明](https://docs.pytorch.org/docs/2.15/notes/randomness.html)指出CPU/GPU执行即使相同随机种子仍可能不同。由此推断：同模型/维度/精度、相似度取整或同分按ID，均不足以保证任意近同分及K边界完全同序。计划保留用户的四组合一致目标，把数值规范、跨设备identity和必要规范计算作为开发期设计；先用小样找到可达方案及成本，再做该能力验收。不能凭少量平均误差就合并identity，也不能把设备选择或text回退隐藏起来。
