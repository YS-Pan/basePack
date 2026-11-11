# engineering-judgment 现成方案与有效性复核

2026 年 11 月 10 日。用户要求在完整框图确定后重新联网检索现成方案和解决问题的概率。本次只做调研；[计划](../plan.md)仍待实施。

## 结论

现成组件覆盖了工程原则、按需读取、验收和复盘；检索范围内未找到既轻量、覆盖完整链，又有直接证据证明能减少本项目防御性写作、编程与流程膨胀的成品。独立 skill 是可试验的干预，不能仅由其形式或逻辑框图推断可靠性。

更强的支持来自具体知识、可操作的案例、真实合同和结果反馈。仅把现有简洁原则重写成 skill，边际收益不明。公开研究衡量的通过率、检查通过比例与代码质量指标，都不是本项目的防复发概率；现阶段不提供没有本地数据依据的百分比。

## 可复用的现成部分

| 来源 | 实际形态、覆盖与缺口 |
| --- | --- |
| [OpenAI Cookbook](https://developers.openai.com/cookbook/examples/codex/iterating-development-workflows-with-codex) | `harness-author` 创建提示词与事后复盘提示词，接近设计、验收、反馈归属的整链；不是提供现成 SKILL.md。可借其维护源判断，不照搬阶段审批。页面为定性工作示例，没有本目标的效果对照。 |
| [Superpowers](https://github.com/obra/superpowers/blob/main/skills/using-superpowers/SKILL.md) | 真实多 skill 套件，覆盖设计、调试和验收。入口要求只要有很小适用可能就调用，含固定流程；与本项目相称开销的目标有张力。不能由它有测试设施推导采用整套有净收益。 |
| [self-improve](https://github.com/szelemeh/skills/blob/main/skills/self-improve/SKILL.md) | 简短复盘 skill，按用户请求定位本轮摩擦的根因并建议修到规则、skill 或文档。接近反馈端，但不负责工程方案本身，也不验证改进效果。 |
| [self-improving-agent 4.0.5](https://github.com/pskoett/self-improving-agent/blob/master/self-improving-agent/SKILL.md) | 真实 OpenClaw skill，记录纠正、复核和提升经验；默认另建 `.learnings/`。不能原样替换本项目现有进度与知识维护源，也未覆盖完整工程取舍。 |

前序已读的 [karpathy-guidelines](https://github.com/multica-ai/andrej-karpathy-skills/blob/main/skills/karpathy-guidelines/SKILL.md)、[simple-engineering](https://github.com/Robot-Inventor/agent-skills/blob/main/skills/simple-engineering/SKILL.md) 和 [avoid-overdefensive-programming](https://github.com/aravelo7/codex-agent-skills/blob/main/skills/avoid-overdefensive-programming/SKILL.md)提供相关原则，没有查到它们对本目标的直接对照数据。[Anthropic skill-creator](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md)可借鉴新旧/有无技能对照及触发检查；评测方法的存在不等于目标技能已经有效。

## 原始研究与外推边界

| 原始来源与版本 | 实际结果 | 对本计划的意义与限制 |
| --- | --- | --- |
| [SkillsBench v4](https://arxiv.org/html/2602.12670v4)，87 任务、18 配置 | 策划技能的平均任务通过率 33.9%→50.5%，+16.6 个百分点；软件工程子集 +11.6 个百分点。三种专用框架配置中，自生成技能低于无技能 8.1–11.5 个百分点 | 具体技能可提供明显收益，但任务经过筛选，包括排除两条件无可测差异的候选；不能当任意新增技能的预期收益，也不能把自生成技能的结果直接套到经用户案例校准的技能。 |
| [SWE-Skills-Bench v2](https://arxiv.org/html/2603.15401v2)，98 技能、980 需求、4 配置、3,920 对实验 | 可执行检查的平均通过比例 76.59%→76.93%，+0.34 个百分点；4 技能显著有益、2 有害、92 未检出显著方向 | 更贴近现有模型已熟悉的工程任务；技能价值是相对当前模型与框架默认行为的边际效应。每技能只有 10 个需求，未显著不等于零；4/98 也不是本技能有效概率。 |
| [Skill Usage in the Wild v1](https://arxiv.org/html/2604.04323v1)，84 任务、3 模型 | 一个 Claude 配置中，强制加载定制技能、自行选择、加入干扰技能时通过率依次为 55.4%、51.2%、43.5% | 对照设置不同于本项目，支持单独验证选择与加载；自动发现不能由 description 存在来证明。 |
| [SlopCodeBench v2](https://arxiv.org/html/2603.24755v2)，36 问题、196 检查点 | 直接测试 anti-slop 与 plan-first 提示。三个模型配置中 anti-slop 降低冗余指标 27.5%–35.6%，但未消除迭代退化，部分严格功能通过率下降 | 与减少过度防御最接近的原始实验；仍衡量代码代理指标，并非安装文档、未知兼容性或本计划的整体效果。减少冗余与保持功能必须分别验。 |
| [Prompt-Induced Waste v4](https://arxiv.org/html/2608.01347v4)，24 个确定性编码任务 | 要求多方案、极度确定等措辞增加部分受测配置的冗余工作，没有相应成功收益；相称效率提示在明确任务上保留有效工作，在小规模歧义任务追加实验中也可能过早结束 | 支持控制指令诱发的工作；测试措辞、模型与小任务有限。简洁与停止条件应结合真实需求，不能替代必要取证。 |

上述效果相互不同并不构成简单矛盾：任务选择、基线能力、技能的专门知识和验收指标不同。它们均未测当前 GPT-6 系列下本技能的长期防复发率。

## 对当前计划的建议

1. **先验证新增内容的价值。** 对照基线保留现行 AGENTS.md、已有 skill、项目契约和正常工具；实验组只增加目标 skill。模型、执行框架和输入保持相同，避免拿有指导与完全无指导作不公平比较。
2. **让案例补充实际判断依据。** 需要说明何种合同或事实使一个限制合理、何种证据只能作样本；不只重复“简单、严谨、避免防御”。基准答案、原修复结论与预期措辞不交给执行者；保留未见情境。
3. **分别观察三个结果。** 多余防御与工作是否减少，必要处理与功能是否保持，以及相关/无关任务是否正确触发。小样本可用于淘汰或修订初版，不足以估算长期概率。
4. **达到证据再决定交付形态。** 有稳定增益才保留独立技能；无增益时精简或合回已有入口。真实失败若源于代码或职责，就修其维护源，不继续堆技能规则。本次不据调研自动改写主计划或实施技能。

工程判断：减少类似已知失误有中等把握，陌生情境的持续收益把握更低；长期杜绝复发缺乏支持。这是定性判断，不是测得概率。当前图中多个判断框仍由 agent 执行，不因拆成节点就获得独立可靠性。

## 实际工作与接续

主 agent 与两个清洁上下文订阅 worker 分查原实现和实证研究，主 agent 共读关键来源及反证；未安装候选、运行目标技能或进行本地行为实验。团队用量与独立分项耗时不可核。调研原文以上述固定版本和原仓库文件定位，后续会变化的仓库内容以实际采用时复核为准。

本次调研材料与计划未入当前项目记忆 scope，沿计划在实施接续时登记并做必要小批；启动发现的其它 changes/pending 交由其所属任务接续，不作为本次调研的结束条件。
