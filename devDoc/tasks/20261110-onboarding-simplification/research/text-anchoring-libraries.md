# 文本重定位积木选型

2026-11-10（北京时间）。为[计划E](../plan.md#e脚本优先的增量维护优先实施)补充库选型。用户要求优先成熟项目、减少自行实现，随后指出 reanchor 缺少使用与维护证据。本轮重新核查官方源码、发行包及实际消费项目，并运行隔离探针；产品功能仍待实施。

## 结论与选择

撤回此前聊天中对 **reanchor** 的优先推荐。它的接口贴合需求，但当前规模、发行历史和独立采用证据不足，不能把“功能探针通过”写成“成熟可靠”。成熟度同时看真实采用、维护与发行、可复用接口及本项目合同，star 只作辅助信号。

**同类成熟实现首看 Hypothesis；本期严格机械定位优先复用 Python 标准库。** 两者承担不同工作：前者能在正文改写后寻找最可能的锚点；本期先处理字节/换行等价和未变原文定位，用 `re`、现有 `difflib.SequenceMatcher`、`bisect` 足够，无需另装完整锚定引擎。只编写现有维护流程所需的范围、依据与发布胶水，不自研近似搜索、编辑距离、候选打分或通用锚定框架。

## 查到的成熟同类项目

以下是当日官方页面/registry 快照；下载量含 CI 等自动请求，不等于用户数。较低的 star 可以与真实产品采用并存，也不代表接口满足严格原文合同。

| 项目 | 成熟度证据 | 能直接复用什么、还缺什么 | 本次取舍 |
| --- | --- | --- | --- |
| [Hypothesis client](https://github.com/hypothesis/client) | 744 stars，持续维护；官方于2025年[披露超过8000万条标注](https://web.hypothes.is/blog/what-we-learned-from-80-million-annotations-and-why-it-matters/)。当前核对release/npm 1.1769.0，2026-10-15 | 纯字符串 `matchQuote(text, quote, {prefix,suffix,hint})`，内部先列所有exact，没有exact才近似搜索，再按上下文与旧位置排序；最终仅返一个最佳项。正文修改、重复无上下文也可能成功，结果不证明唯一性或知识有效 | **最接近的成熟实现**；确需改写后候选建议时，优先复用其固定release核心 |
| [GoogleChromeLabs Text Fragments Polyfill](https://github.com/GoogleChromeLabs/text-fragments-polyfill) | 127 stars，6.7.0 / 2025-11-10；官方明确用于 Chromium iOS 和 Link to Text Fragment 扩展 | 有独立公开模块、prefix/suffix搜索，返回0/1/2个DOM Range，2表示有歧义；采用DOM、词边界、NFKD/小写/去音标/空白归一语义 | 成熟浏览器积木；适合以后浏览器复核/分享链接，当前原始源码定位不引入DOM映射 |
| [dom-anchor-text-quote](https://github.com/tilgovi/dom-anchor-text-quote) / [Laws.Africa fork](https://github.com/laws-africa/dom-anchor-text-quote) | 原包35 stars、4.0.2 / 2017-02-10，近30天下载40,877；fork 5.0.0 / 2022-07-15，当前 [indigo-akn](https://github.com/laws-africa/indigo-akn/blob/main/package.json) 仍依赖并调用它。[Laws.Africa](https://laws.africa/resources/)说明 Kenya Law 使用 Indigo | 有公开offset API，Node可用 `{textContent: text}` 调用，无需浏览器。使用DMP，返回单个近似候选，没有strict唯一性模式；UTF-16坐标 | 有生产使用、低频维护的直接安装选项；当前 Hypothesis 核心更值得作为近似候选底座。不能把Hypothesis当前维护状态算到这个旧独立包上 |
| [Recogito Text Annotator](https://github.com/recogito/text-annotator-js) | 106 stars，4.3.7 / 2026-10-12；[DeepTutor实际调用](https://github.com/HKUDS/DeepTutor/blob/main/web/components/reading/TextUnitView.tsx)，[波恩大学部署Studio](https://www.hrz.uni-bonn.de/en/all-services/web-documentation-tools/recogito-studio)，[官方架构](https://recogitostudio.org/reference/client-architecture/)确认组件链路 | 活跃DOM标注UI，能捕获quote/context/offset；[revive实现](https://github.com/recogito/text-annotator-js/blob/main/packages/text-annotator/src/utils/annotation/revive-annotation.ts)按offset恢复，没有quote重寻 | 浏览器标注可选；当前后台重定位不选。旧RecogitoJS已弃用归档 |

Hypothesis 是 BSD-2-Clause 项目，部分 annotator 组件另列 MIT；Text Fragments 是 Apache-2.0；quote 库为 MIT，当前 Recogito 为 BSD-3-Clause。仅核对上游声明，实际分发时保留相应原许可。

### Hypothesis 的具体接法

官方 `hypothesis@1.1769.0` npm包是完整浏览器bundle，入口为 `build/boot.js`，没有独立导出 `matchQuote`；不存在已核实的官方 `@hypothesis/anchoring` 包。可交付的最小复用方式是固定 [release commit a7b7400](https://github.com/hypothesis/client/tree/a7b7400d0d706d4357ec37c2a3610b25dcca89d5)，提取不改算法的 [163行核心](https://github.com/hypothesis/client/blob/a7b7400d0d706d4357ec37c2a3610b25dcca89d5/src/annotator/anchoring/match-quote.ts)与上游测试，锁其产品实际使用的 `approx-string-match@2.0.0`，构建JS并附薄的Node JSON调用入口。无需Hypothesis服务、DOM或运行时TypeScript。

本轮已将该核心去类型构建为约5KB的JS并成功导入；已有Node v24.22.1实际跑过中文/emoji/CRLF、重复与改写探针。它属于**复用成熟源码**，需要本项目审阅内部API升级，并处理UTF-16与Python字符/原字节坐标。要从最终接口取得全体候选或歧义，需要修改提取源码；单纯适配不能声称已经具备这些能力。

本期暂不引入它，是因为strict机械定位仍需全量exact、上下文/范围和依赖状态判定，Hypothesis的近似排序尚无本期工作可替代。若后续真实使用需要正文改写后的候选建议，再按上述方式验证收益；不因其语言是JavaScript而排除，也不自行重写一套相似度排序。

## 一期实际使用的积木

| 责任 | 复用能力 | basePack所需胶水 |
| --- | --- | --- |
| 原件与比较视图 | 现有 `content.py` 原字节/快照；仅比较视图做CRLF→LF | 保留真实hash、原件和原始换行；依完整行映射回原件 |
| 全部精确位置与前后文消歧 | 标准库 [`re.escape`、`finditer`、lookahead、捕获组span](https://docs.python.org/3.13/library/re.html) | 从旧snapshot取得quote与紧邻上下文；保留0/1/多候选，核完整行边界 |
| 行差异、旧/新未变区间 | 已有 [`difflib.SequenceMatcher`](https://docs.python.org/3.13/library/difflib.html) | 把差异与现有成员、父级范围关联；映射和旧位置只是位置证据 |
| 字符span转行号 | 标准库 `bisect` 与行起点表 | 使用明确的半开字符区间与1-based完整行号 |
| 状态与发布 | 现有store、source_version、expected/apply、向量identity与stop | 判断哪些知识依赖仍有效、生成原有批次、保留未决语义；不新增队列/后台平台 |

精确候选的核心可直接用标准API表达；quote按契约非空，prefix/suffix按原文保存。正向lookahead使查找不消耗正文，重叠命中也能全部返回；原文经escape后没有用户正则语义。

```python
import re

exact_pattern = r"(?=(?P<quote>" + re.escape(quote) + r"))"
context_pattern = (r"(?=" + re.escape(prefix)
                   + r"(?P<quote>" + re.escape(quote) + r")"
                   + re.escape(suffix) + r")")
exact_spans = [m.span("quote") for m in re.finditer(exact_pattern, text)]
context_spans = [m.span("quote") for m in re.finditer(context_pattern, text)]
```

这段是精确匹配原语组合，不是完整维护功能。上下文匹配是定位证据；移动到别的标题、外部条件变化或先前更正仍由计划E的语义/历史合同处理。完整context未命中时仍保留exact候选，避免把周边编辑误称为正文消失。

第三方 [`regex`](https://github.com/mrabarnett/mrab-regex) 也已核查：608 stars，发行历史可追到2010年，被 [tiktoken](https://github.com/openai/tiktoken/blob/main/pyproject.toml) 和 [Transformers](https://github.com/huggingface/transformers/blob/main/setup.py) 实际依赖。项目锁中已有2026.11.8，本轮隔离安装该版与最新.9均通过探针。但一期没有fuzzy/grapheme等额外需求，标准库即可，不把传递依赖变成新增客户端依赖。以后若单纯需要编辑距离候选，可评估直接用它；与Hypothesis近似排序择需采用，不先堆两套。

## 淘汰与未引入项

- [reanchor](https://github.com/microbluey/reanchor)：0 stars、0 forks，0.1至0.3发行集中2026-08-27至28，PyPI Beta；严格参数下探针可用，但缺少成熟采用证据。只留比较原证，撤下主选。
- [Anchorpoint](https://github.com/mscarey/anchorpoint)：0.9.0仍活跃，但exact固定IGNORECASE、上下文宽松空白，`ana`/`banana`漏掉重叠歧义；还使用Atmosphere许可。要满足本合同需在外层重做定位检查，未选。
- [Apache Annotator](https://incubator.apache.org/projects/annotator.html)：有接近strict的全匹配selector，但已于2025-08退休；不作新默认依赖。
- DMP、RapidFuzz、fuzzysearch均运行了API探针；近似匹配可以把“禁止”改“允许”仍报成功，且不提供本项目的上下文/依据有效性。现有difflib已能提供本期差异，不追加重复积木。
- [pyahocorasick](https://github.com/WojciechMula/pyahocorasick) 2.3.1是成熟的多pattern exact扫描器，约1.1k stars、无基本运行依赖；一次文件查大量quote确有瓶颈时再引入，本期267项不能单凭数量证明需要优化。

## 实际检查、原证与限制

Windows / CPython 3.13.17：Anchorpoint 14例；DMP/RapidFuzz API探针及DMP上游28测试；regex 2026.11.8/.9与pyahocorasick隔离探针通过；Hypothesis当前/旧quote库在Node v24.22.1运行探针通过。验证覆盖字面元字符、重复/重叠、上下文、中文/emoji/CRLF、坐标单位和正文改写。3.14只核上游CI或发行wheel，未在本机执行。

选留267个历史待核chunk、32个旧source_version作只读回放。仅CRLF→LF比较视图下，110个正文各有一个完整匹配，157个没有；110个均落完整行边界。加保存的完整literal prefix/suffix后86个仍唯一，另外24个正文仍在、完整周边已有变化。标准库re与regex 2026.11.8的正文及上下文span列表均267/267逐项一致，`aaa`/`aaaa`重叠探针亦通过。110与86都只是匹配证据，不是可恢复fresh数、节约额度或产品验收。

调查和探针未改产品代码、依赖、安装或配置。按现行流程另有一个正常自动维护小批实际发布了先前计划change_log的1来源、2成员；原426项没有被本轮选型清除，该维护与定位探针分开记录在[进度](../progress.md)。

选留原证位于根 `artifacts/runs/20261110-anchoring-libraries/`：各分支review、官方metadata/关键源码、探针与结果，以及267项selector和回放结果。未保留虚拟环境、node_modules或大体积上游工程；脚本中的tmp路径记录当时运行条件，重跑需按报告恢复临时依赖。团队用量与总费用不可取得，记为未知。
