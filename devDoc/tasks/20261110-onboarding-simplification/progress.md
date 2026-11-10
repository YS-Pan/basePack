# 接入、记忆维护与运行简化进度

2026-11-10（北京时间）。状态：0.8.0本地候选已实现并通过普通安装检查；免认证风险选择及正式启用待定。

## 实施接续

执行聊天为 [阅读对话并执行计划](codex://threads/01a1c5dc-af1a-7fa2-87a6-654370d72307)，从 main `08bb5e8`、干净工作区接续。主 agent 完整翻页读取原计划聊天，复用本目录的最终方案。记忆 coordinator 贯通 E/F、C 的记忆接口及 D；配置 owner 负责 B、C 的配置与无配置命令；文档 owner 负责 A/G 及产品说明；验证 owner 负责源码外普通安装与已知调用方审计。主 agent 统一整合、记录版本和提交。

本轮目标版本为 0.8.0。先完成产品与隔离库验证；正式项目数据库切换、共用客户端升级和外部项目写入依计划的实际授权与窗口处理。正式库与共享设施保持运行，不以清空旧积压或全历史聊天入库为结束条件。所有临时实施与验证材料放根 `tmp/20261110-onboarding-simplification/`，需留原证再选入根 artifacts。

## 候选交付与当前待决

[本轮结果](result.md)汇总A–G的实际行为、检查与限定。源码外普通wheel **354 passed，0 skipped**，38个包文件与wheel逐字节一致；最后修复按受影响组复测。实际共享模型已核机械0/1/0输入编码与旧版本回源；旧库隔离恢复和候选接管七表逐字段不变。默认真实采集得到492份来源、6161个正文part，重复492份均零重写；336条全局归属未决及10项采集缺口保留，未对全历史作语义发布。所用设施、wheel与原证沿[安装结果](installation-result.md)维护。

A5已由主agent实际修复array项目的两个发现junction，官方skills/list核实两项均repo作用域、无错误，外部main提交`931634e`，工作区干净。用户当前要求执行A5构成此次可逆修复授权；正式数据库迁移不因此自动启动。两份README英文及产品/system文档已完成相关检查。

浏览器实测发现免认证回环库仍可被跨源简单POST写入，CORS只阻读响应。已向用户提交风险选择，尚未回复；本地候选准确记录原计划实现，不代表正式采用。三个正式项目、共用客户端和机器配置保留原运行合同，未发布或推送候选。下一步先确定认证取舍，再安排逐项目迁移窗口及自有入口更新；远端发布另行授权。

本轮新源码/测试已按git清单登记source_scope，并增加本任务文档目录；67份源码/测试/示例均已登记。稳定0.7.1执行显式scope发现105项来源变化，回执位于`.basepack/memory/maintenance/20261110-implementation-scope-changes.json`，这是发现而非接受。正常低优先级维护另补齐先前已提交change_log的1来源、2成员完整1–7行，search/read及快照核对通过，无节点/边及失效；未将本次全部源码变化或426条历史待核清零。收尾stop返回`stopped=true`；worker此前已完成，随后interrupt句柄返回`not_found`，没有等待中的维护任务。

## 已完成

- 完整读取用户给出的两段讨论，结合当前 main `8fa500d` / 0.7.1 复核差异；纯 text 删除及三项目向量迁移作为已交付基线。
- 主 agent 整合取舍，两名 tier3 协作者分别只读核查技能接入与冗余接口；均实际使用配置指定的 `gpt-6.1-sol / ultra`。已形成[修改计划](plan.md)，覆盖接入发现、可信本机免认证、命令与接口清理、有限编码去重及迁移验收。
- 核实资源 skill 外部复制后文档相对链接失效；init/core doctor、wheel 的现行范围、所有冗余候选及调用方条件均已写入计划。
- 核对 SurrealDB 官方免认证、监听与 CORS 文档和本机 4.0.0 命令帮助。数据库切换、免认证读写与原生恢复尚未实测。

## 检查与边界

首轮仅写计划及进度入口，不修改源码、安装、配置、正式数据库、外部项目或项目纲领。实际完成 UTF-8、相对链接/锚点、围栏和 Git 差异检查；当时未运行产品测试或技能试验。

后台 tier1 维护 worker（`gpt-6-luna / max`）只检查指定来源，未 prepare/apply，随后自行完成。brief 当时显示426项待核知识；主 agent 提醒另行手动维护，但额外按本业务归属限域以及 worker 按 Git/关键词排除 modified 的判断有误。业务收尾为 `.basepack/memory/controls/20261110-plan-onboarding-simplification.json` 发送 stop 并尝试 interrupt，宿主返回 worker 已完成，不能据此声称当时仍有维护运行。正式数据库保持运行。

## 接续调查：modified 与自动维护遗漏

用户质疑后完成[深入调查](research/memory-maintenance-audit.md)：Git干净与记忆modified使用不同基线，原进度文件确有实质内容未入记忆。426为339成员、9节点、78关系，成员涉及32来源；全部426项最后失效均追到旧detected_change，升级未恢复状态。主派工限制与worker过早排除是本次未推进维护的直接原因，现行/遗留文档另有歧义及缺失步骤。

另以普通0.7.1、独立SurrealDB内存库与真实embedding复现：sources-only可使changes归零而旧摘要尚未重核；模拟旧stale后，changes/来源接受/embed均不清语义待核，正确重交成员及依赖能恢复。临时库进程和端口已关闭，正式库只读取证。源码与安装文件一致、纯文件复现、原生小闭环和文档检查通过；未改源码、配置、正式数据或清理426项。修正建议见调查第5节，尚未实施。

接续核对源码量与待核量：2292行只统计产品源码；426项由产品源码75、测试65、文档163、skills26、模板4、依赖声明6条表示及9节点/78关系组成。339条表示分布32来源，层级为32文件摘要、40章节摘要、267原文块；110块原文统一换行后仍可在当前文件完整找到，存在待核后复用机会。详见调查2.1节，不能把记录数当作独立阅读任务数，亦未据此批量恢复状态。

## 接续选型：成熟文本定位积木

用户要求优先成熟库并质疑reanchor后，完成[定位积木调查](research/text-anchoring-libraries.md)。撤回聊天中对reanchor的优先推荐：功能贴合与探针通过不足以证明成熟采用。三名tier3协作者分查Python原语、Hypothesis/Apache、Anchorpoint/Recogito与实际消费项目，主agent整合并复核本期收益。

查到的成熟同类实现以Hypothesis最接近，另有Chromium iOS实际使用的Text Fragments Polyfill、Laws.Africa生产链使用的dom-anchor-text-quote及活跃Recogito标注组件；各自的近似最佳项、DOM/归一化、低频维护或offset-only限制已核实。Hypothesis npm包不是纯文本API，固定release的163行核心已独立构建/导入；Node探针确认精确、上下文移位、重复和改写行为，未引入正式产品。

一期范围为严格机械等价，最终选用标准库re全量literal候选与前后文、现有difflib、bisect和store，零新增定位依赖。regex也有tiktoken/Transformers实际采用，已隔离实测锁定2026.11.8与最新.9；但本期标准库够用，不为选库增加依赖。267项真实回放中正文唯一110、完整上下文唯一86，全部正文命中落完整行边界；re与regex的两类span逐项一致。24项正文仍在而周边已变，匹配数不等于可恢复状态数。3.13实测及Node探针通过，3.14未在本机运行。原证选留根artifacts，对应方案已写入计划E。

本轮选型未改源码、产品依赖、配置或安装。另按现行流程启动的tier1普通自动维护完成了先前计划change_log的1来源、2成员，`invalidated=[]`；hybrid literal检索及read核对原件成功，向量覆盖1193/1193。回执位于 `.basepack/memory/batches/20261110_plan-mechanical-memory-maintenance/applied.json`，control为 `.basepack/memory/controls/20261110-anchoring-library-selection.json`。这是正常发布小批，不是清理原426项；业务收尾stop返回 `stopped=true`，随后尝试interrupt，宿主确认worker此前已完成。正式数据库保持运行。

## 计划制定时的实施顺序

用户要求减少机械问题对agent额度的消耗，已将“脚本优先的增量维护”写成[计划E](plan.md)优先批次：元数据/整文件换行等价零语义派工，脚本定位未变块，agent只读剩余语义变化；复用现有事务、快照、向量输入版本与stop，保留更正/退役及未决范围。匹配回放作为证据，不预先视作可自动恢复数。计划和选型已完成，产品实现及端到端验收待做。

主线先E最小机械闭环，再F默认聊天闭环；A/G和C可独立推进，交叉文件由owner顺序整合。B先做产品改动、隔离验证与既有库恢复，正式切换沿各项目授权和窗口，不阻塞其它批次；D等相关接口稳定后按净收益决定。仓外旧Python调用方、实际宿主发现和免认证浏览器请求行为按各自完成条件核实。

## 本次综合维护：聊天来源与英文README

已完整读取用户指定的[聊天覆盖调查](codex://threads/01a1c568-0e63-7a32-94a4-508ffc4e1156)四个turn，确认默认project全聊天属于原有要求，0.7.1新项目同样缺失采集能力。主agent与两名tier3协作者核当前实现、已有统计、本机Codex schema及官方文档；新增[接口依据](research/codex-chat-ingestion.md)，把默认归属/历史补采、真实prompt与subagent身份、项目局部原文、完整分页、精确回源和增量/stop接续合入F。schema生成与源码复核已做，真实全量读取及聊天入库未做；本轮没有把临时日志解析器装成产品能力。

G明确两份README正文使用英文，并修受影响的安装、技能和构建锚点；其它文档不整体翻译。E补直接派工纠偏、无积压硬阈值及sources-only使旧fresh摘要漏核的反例验收；成熟积木选择保持标准库优先、按真实需求再评Hypothesis。A–D原范围保留，C不再等待B正式迁库。已同步记忆专项与重建入口，并修现行计划中“当前任务变化/积压只提醒”的歧义；产品、README实际翻译与正式迁移均待实施。

本次tier1常规维护另完成已提交的定位选型change_log：1来源、2成员、1有原文依据的decision node，0边，`invalidated=[]`；hybrid literal、read及neighbors已核，向量覆盖1195/1195。回执为 `.basepack/memory/batches/20261110_plan_consolidation/applied.json`，control为 `.basepack/memory/controls/20261110-plan-consolidation.json`。未采集或导入聊天，原426项没有由本次计划维护清除。业务收尾stop返回 `stopped=true`，随后interrupt确认worker此前已完成，正式库保持运行。该常规小批与产品计划交付分开记录。

计划维护的检查限于UTF-8、Markdown/本地路径及锚点、来源/能力边界与Git差异，不重跑产品测试。选留原证归根 `artifacts/runs/20261110-plan-consolidation/`；本次未改源码、依赖、安装、配置、项目纲领或外部项目。

本轮团队 token、费用与主上下文分项不可核，记为未知。未来实施的实际结果另记，不将规划视作交付。
