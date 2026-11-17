# 连续相似度加权遗忘：依据、反证与实施选择

后续用户澄清已接受长期未用方向退出记忆；正ε的长期影响现作为目标，线性核继续为模糊边界默认推荐。实际退出/回收与防重建合同见[目标架构](../target-architecture.md#从连续降权到实际遗忘)，三种核和处置方式见[选项](../forgetting-options.md)。本页保留先前取证和数学边界，不把它写成实际数据淘汰。

2026-11-17。本轮先补联网论文和固定源码调研，再修订[目标架构](../target-architecture.md)与[计划](../plan.md)。当前运行的0.16仍是全局访问权重；下述连续规则没有实施或业务收益证据。

## 聊天覆盖与研究问题

已分页读取[指定聊天](codex://threads/01a1def8-56df-7483-bbe9-6db99e409d00)全部27轮的用户消息、答复与进度，沿引用核现行计划、研究和已交付结果；关键算法工具记录定点回读，没有重新扫描本机历史日志。前面的论文调研主要回答行为表示、聚类和多兴趣问题。最后一轮确实有kernel/ACT-R相关联网搜索和余弦文档回读，但只交付一个小算术例子，未形成持久遗忘机制的系统原证比较，不能说它完全没有联网，也不能把此前25篇归档都算作新规则的验证。

本轮分认知记忆、核方法和开源实现三组取证，检索包括 similarity-based interference、retrieval-induced forgetting、ACT-R spreading activation、MINERVA、temporal context、kernel accumulated features、event-time fading。判断标准是：相似度是否改变持久状态、谁推进时钟、未命中是否受抑制、命中怎样强化、能否精确惰性累计、需要哪些业务证据。没有在所核来源中找到与整套候选合同同构的成熟算法；这是本轮范围内的结果，不是不存在其他先例的断言。

## 学术机制：哪些相近，哪些不能代替

| 原始来源 | 实际机制及可借鉴点 | 与本项目候选的区别 |
| --- | --- | --- |
| [Anderson & Schooler，1991，Reflections of the Environment in Memory](https://users.cs.northwestern.edu/~paritosh/papers/KIP/AndersonSchooler1991ReflectionsOfEnvironmentOnMemory.pdf) | 过去使用的频率和近因预测未来需要；ACT-R类base-level以过去使用痕迹的幂律和表达激活 | 支持从历史使用预测未来需要，不提供“相似未交付项永久加龄”的公式 |
| [Anderson & Reder，1999，The Fan Effect](https://www.cmu.edu/dietrich/psychology/memorylab/publications/99_jra_lmr_2.pdf) | 当前线索的关联扩散受fan影响；通用线索连接越多，单条关联支持越弱 | 当前激活/竞争不同于持久遗忘；不能把通用材料与多用途任务直接当成可靠路由 |
| [Hintzman，1986，MINERVA 2](https://legacy.cs.indiana.edu/~port/HDphonol/Hintzman.scheme.abstrtn.mem.1986.pdf) | 线索与各痕迹的特征匹配产生连续激活，再汇合为echo；其匹配激活使用三次幂 | 相似度主要参与本次召回；不是非负行为余弦，也不是未命中项的机会年龄 |
| [Howard & Kahana，2002，Temporal Context Model](https://memory.psych.upenn.edu/files/pubs/HowaKaha02.pdf) | 连续上下文漂移及上下文恢复解释序列记忆；常见递推为新旧上下文混合并归一 | 改变当前检索线索，不等同于给全库每项保存持久抑制量；连续表示也不自动保证任务隔离 |
| [Anderson、Bjork & Bjork，1994，Remembering Can Cause Forgetting](https://memorycontrol.net/abb1994.pdf) | 选择性提取可影响相关而未练习项目的后续回忆，提出retrieval-induced forgetting问题 | 人类实验的选择性提取、竞争及测试条件，不等于agent交付/预算；不能据此断言所有未选项都应降权 |
| [Anderson、Green & McCulloch，2000，Similarity and Inhibition](https://memorycontrol.net/agm2000.pdf) | 区分目标—竞争者相似性与竞争者之间相似性；实验中前者可减轻、消除甚至逆转遗忘，后者可增加遗忘（pp.1141–1144机制及后续实验） | **直接反对把“越相似就必然越应遗忘”当通则**；共同交付尤其可能编码互补与共享特征 |
| [Oberauer等，2012，SOB-CS](https://doi.org/10.3758/s13423-012-0272-4) | 干扰、项目—位置绑定及对无关内容的移除构成工作记忆模型 | 提醒区分干扰与时间流逝；不验证长期资料库的行为向量、交付事件或所拟曲线 |
| [Rendle等，2009，BPR](https://cvg.cit.tum.de/_media/teaching/ws2012/ml2012/download/rendle2009.pdf) | 配对排名下，固定用户向量与正项时，未观察负项分数越高，负梯度越强（§3.2、4.1–4.3） | 是相关未观察项负更新的局部直接先例；训练采样、非线性梯度与改变向量，不是每次交付的固定核增龄、正基线或命中归零 |
| [Kivinen等，2004，NORMA](https://alex.smola.org/papers/2004/KivSmoWil04.pdf) | 以损失梯度乘核函数更新预测函数，另统一收缩旧项（式7–12） | 支持按相似性传播有符号更新的数学部件；符号来自误差，未使用本身不是监督信号 |
| [Vinagre & Jorge，2012，推荐遗忘](https://link.springer.com/article/10.1007/s13173-012-0077-3) | 新会话驱动共现及缓存相似度统一乘α，再补当前共现对（§3–4、Algorithm 4） | 直接提供行为共现＋事件遗忘先例，但衰减率不依赖当前材料相似度，不等于本项目完整规则 |
| [Katharopoulos等，2020，Transformers are RNNs](https://proceedings.mlr.press/v119/katharopoulos20a.html) | 式10–12、18–19利用有限维特征的内积和可结合性，将历史贡献编译为累计状态 | 能借鉴累计特征的代数结构；论文研究注意力，不证明本项目遗忘方向、强度或检索收益 |

ACT-R类公式可写为`B_i=log Σ_j(t−t_ij)^(-d)`、`A_i=B_i+Σ_j W_j S_ji+其它匹配项`，不能只看见相似度和衰减就视为同一算法。1998年[An Integrated Theory of List Memory](https://doi.org/10.1006/jmla.1997.2553)的p.344脚注3还明确讨论intervening events可能比clock time更关键；本轮原出版PDF获取受限，相关脚注经作者上传全文核读，未据此展开整篇结论。因而“ACT-R必依赖日历、本方案首创事件时间”也不是成立的区分。

数学背景另见[Kernel Mean Embedding综述](https://arxiv.org/abs/1605.09522v4)和[Random Features](https://pages.cs.wisc.edu/~brecht/papers/07.rah.rec.nips.pdf)。前者的经验特征均值、后者的近似核映射有各自任务；都没有直接提出这里的未命中增龄政策。本方案的线性核本来就是有限维精确映射，先加随机特征没有必要。

几个容易混淆的公式可直接对照：BPR负项更新为`Δh_j=−η·sigmoid(x_uj−x_ui)·w_u`（略正则）；NORMA为`f_next=(1−ηλ)f−η·loss_derivative·k(x,·)`。它们确有相关负更新部件，不能一概降为泛类比，也不能把会变的误差/向量写成固定相似软计数。[Hu等2008](https://yifanhu.net/PUB/cf.pdf)的缺失零目标及低置信是训练目标，不是每次真实交付的ε；[TD资格迹](https://proceedings.mlr.press/v32/seijen14.html)的折扣向量累计负责分配当前误差，[Parzen核计数](https://doi.org/10.1214/aoms/1177704472)负责密度估计，同样没有规定未交付惩罚。完整规则属于本项目组合，不能声称首创或直接继承这些方法的有效性。

## 开源项目：复用组件，不继承未验证的效果

以下是核过的源码截点，并非要求安装这些版本或声称它们均为最新版。

| 项目与固定源码 | 可确认行为 | 决定 |
| --- | --- | --- |
| [pyactr，0faecf3，base-level与spreading](https://github.com/jakdot/pyactr/blob/0faecf3bbfa6fa5e53a298ee25dabf03377a045a/pyactr/utilities.py#L423-L560)、[retrieve](https://github.com/jakdot/pyactr/blob/0faecf3bbfa6fa5e53a298ee25dabf03377a045a/pyactr/declarative.py#L183-L259) | 用历史出现时间计算base-level，再加当前buffer关联激活和匹配；候选落选不导致持久抑制写入 | 借频率/近因、上下文与通用fan分开表达，不引入认知模拟器 |
| [py-fsrs 6.3.3，e40a5a7，retrievability](https://github.com/open-spaced-repetition/py-fsrs/blob/e40a5a74799a12c9b15e01559a9b2c9f6be7a648/fsrs/scheduler.py#L210-L271) | `R=(1+F·days/S)^(-p)`；显式四档复习评分更新单卡，其他卡片没有相似度抑制 | 借强度与当前可访问度分开；FSRS的S以90%保留天数定义，不能移植为本项目事件强度或召回概率 |
| [River DBSTREAM，e31b2b4，update/cleanup](https://github.com/online-ml/river/blob/e31b2b49eb0f9032e78e8301202ccd175aa080e3/river/cluster/dbstream.py#L177-L277) | 每输入推进事件钟；命中簇补算`W·2^(-λΔt)+1`，清理时计算未命中簇质量；距离阈值决定匹配，Gaussian仅移动命中簇中心 | 借事件钟＋最后更新点的惰性结构，不借统一衰减率、自动删簇或聚类状态 |
| [scikit-learn 1.7.2，25dee60，KL目标/稀疏重建](https://github.com/scikit-learn/scikit-learn/blob/25dee604bae18205b01548348388baf7a1cdfe0e/sklearn/decomposition/_nmf.py#L136-L210)、[核近似](https://scikit-learn.org/1.7/modules/kernel_approximation.html) | 稀疏KL-NMF仍计零项重建贡献；公开NMF/normalize/dot可用；随机傅里叶近似可有带符号误差 | 复用公开数值API；交付、年龄、unknown、幂等、版本及重放由basePack维护，不依赖库私有函数 |

因此没有必要为此安装推荐平台、认知架构或流聚类库。成熟求解器能减少数值实现负担；新规则的业务含义仍须本项目负责。

## 对新规则的判断与修正

**保留连续路线作为下一阶段待实现的访问策略；称为相似度加权的交付机会年龄，视作工程启发式。** 它表达“相近用途活动经过但此版本未再交付”，不是学习到该材料错误、无用或已经曝光。所有公式与状态的唯一维护源在[目标架构](../target-architecture.md#连续机会年龄与惰性投影)。

| 原候选缺口 | 本次决定及后果 |
| --- | --- |
| 最后答复已建议连续路线，正文仍要求稀疏门控/局部钟 | 撤出类别、成员系数和局部钟主线；原0.16全局规则保留为对照 |
| 正ε与“纯A永不影响B”矛盾 | `0<ε<1`仍使正交B逐步老化；验收计算速率和边界，撤掉绝对隔离承诺；ε=0/1仅作边界对照 |
| 一个年龄/强度却沿用多用途独立访问的说法 | 同一材料在A命中会刷新它的整体年龄，强度也跨用途累计；本路线主动接受这一简化，不再宣称用途独立 |
| 单位q不明确，混合任务可能被再归一放大 | q取独立锚点单位向量的凸加权和，不再次L2归一；是相似度的份额平均，不能再称其为与一个单位query的余弦 |
| unknown被当成相似度零/小权重 | 缺失锚点质量保留为unknown；用累计缺失质量给年龄/提示区间，已知下界不冒充精确值；冷启动仍走基础检索 |
| 每材料保存M在最后命中的整条向量 | 固定空间只需最后命中的点积标量、事件位置及缺失质量基准；不建N×N矩阵或历史前缀向量表 |
| 取消类别后仍说rank自动发现任务数 | r只定表示容量，运行时没有类别数；数据不足保持unknown，自动容量选择未实现、也未选定最优r |
| 对数压缩被当成无代价防偏置 | 默认改为频率忠实的`n_b/d_b`；在无正则及篮子行因子自由的KL目标下可严格聚合相同篮子，见架构条件；不自动降低高频业务贡献 |
| 固定尺度被当成固定几何 | NMF仍可能有同重建、不同余弦的非唯一解；固定训练合同并核邻域稳定性，模型变更后重放，不把归一化当语义唯一性证明 |

非线性核可以另行研究，但不是免费替换：RBF对远处也有正尾；一般精确计算需保留历史锚点，有限随机特征只是近似；对近似分数逐项截负会破坏原来的线性等价。`max`混合锚点也不能一般压成一个q。当前选择有限维非负线性核，是为了明确语义和可维护性，不是已经证明它最优。

## 验证证据与限制

本轮独立算术脚本对19材料、6维、2,000次尝试中的1,623次非空事件验证逐项累计和惰性上下界一致，最大绝对误差`3.34e-13`，377次空交付不推进年龄。KL齐次性检查误差`7.11e-15`。另构造两组完全相同的NMF重建，在列定标＋行归一后余弦仍为0.8与0.40825；混合/通用锚点也确有偏向。这些是合成反例和代数检查，不是生产训练或检索验收。脚本及结果选留于`artifacts/runs/20261117-similarity-research/`。

必要实现回归应覆盖长段A→B、混合/通用锚点、互补材料因预算落选、重复交付粒度、冷启动、版本变化及在途模型切换；分别固定模型测规则、固定规则测表示。不新增正式agent团队对照或参数竞赛，长期质量/成本沿已定真实使用反馈维护。

新增论文原文沿原聊天授权存入私有来源，可选：`private/sources/similarity-forgetting-20261117/README.md`（项目根相对路径）；既有核方法原件在同级`behavior-literature-20261117/`。保存/校验不等于逐页全文已读；实际新增17篇候选中14篇PDF保存成功，共27,850,195字节；Hintzman1986、List Memory1998及Vinagre–Jorge2012的下载因TLS/证书链或404失败，保留获取缺口。扫描/全文取回受限的读取深度以本页和选留研究记录为准，私有manifest记录获取及校验。公开结论、书目和固定代码链接保持自足；本轮未安装依赖、运行作者训练、迁库、修改产品或恢复外部维护。
