# 接入闭环与运行简化进度

2026-11-10（北京时间）。状态：计划已制定，产品修改与迁移待实施。

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

## 下一步

用户要求减少机械问题对agent额度的消耗，已将“脚本优先的增量维护”写成[计划E](plan.md)优先批次：元数据/整文件换行等价零语义派工，脚本定位未变块，agent只读剩余语义变化；复用现有事务、快照、向量输入版本与stop，保留更正/退役及未决范围。匹配回放作为证据，不预先视作可自动恢复数。计划和选型已完成，产品实现及端到端验收待做。

按E → A → B → C → D接续；A的独立准备可并行。密码删除先做隔离验证与既有库恢复，再安排共用客户端和逐项目切换。仓外旧Python调用方、实际宿主发现和免认证浏览器请求行为按各自完成条件核实。

本轮团队 token、费用与主上下文分项不可核，记为未知。未来实施的实际结果另记，不将规划视作交付。
