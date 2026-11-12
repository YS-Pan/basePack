# 使用调查：观察、归因与证据

2026-11-12（北京时间）。对象为聊天[“梳理 GitHub 发布剩余工作”](codex://threads/01a1cdb6-cd05-7310-bc84-f139afd74ce4)，cwd 为 `D:/project/20261109 array reconstruct`。该聊天从 0.10.0.dev1 升级至 0.11.0.dev1；本仓当前源码及本机客户端为 0.11.0.dev1。整改动作和验收仅在[计划](../plan.md)维护。

## 调查范围与保留物

通过 Codex read_thread 分五页读取主聊天十轮，最旧页 `hasMore=false`；再完整读取检索子聊天 `01a1ce27-b7e2-7223-a87d-ee8e551d35a4` 两轮。主聊天前九轮主要查看消息、命令及文件变动，未取得所有工具原始输出；具体失败以选留原证和子聊天实际输出补核。没有审计外部全库或执行其科学实验。

外部入口：

- [BP-T01–T28 问题记录](<D:/project/20261109 array reconstruct/devDoc/archive/20261110-migration/basepack-test-findings.md>)，重点 BP-T27/BP-T28。
- [0.11 升级结果](<D:/project/20261109 array reconstruct/devDoc/archive/20261112-basepack-011-upgrade/result.md>)、[0.10 升级结果](<D:/project/20261109 array reconstruct/devDoc/archive/20261112-basepack-upgrade/result.md>)、[当前接入说明](<D:/project/20261109 array reconstruct/devDoc/system/basepack.md>)。

必要原证选留到根 [artifacts/runs/20261112-usage-rectification/](../../../../artifacts/runs/20261112-usage-rectification/)（Git 忽略）：外部问题/升级文档快照、反馈与旧 mandatory brief、编码失败 trace 和冻结 batch、维护收尾状态，以及本轮 read_thread 选取的命令/输出与文件 hash 清单。文件名及原位置见其中 `manifest.json`；这是本机复核材料，跨机器仍可据本文的聊天、版本和源码定位接续。

## 核心发现

### U1：scope 的请求含义与程序行为不清楚

0.11 的两次独立检索都先以描述性 scope 搜不到。失败子聊天的 `retrieval-prompt` 输出把“当前计划 … 及所引历史虚拟实验结果、弱模态、K4 编码结果”直接写进 `search --scope`；随后三次查询都为 `matches=[]`、过滤范围向量数为 0。去掉 scope 后能找到对应证据。

当前 [prompts.py](../../../../experiments/20261106-basepack/src/basepack/memory/prompts.py) 的 `render_retrieval_prompt` 只校验 scope 是字符串，再直接渲染参数；[store.py](../../../../experiments/20261106-basepack/src/basepack/memory/store.py) 与 [vectors.py](../../../../experiments/20261106-basepack/src/basepack/memory/vectors.py) 实际按路径前缀过滤。skill/请求文档未写清该区别。因此外部结果中的“不作为产品错误”归因需要纠正：存在接口说明/生成命令合同缺口，不能只责怪 worker。

### U2：同一任务按 shell 重复 brief

十轮主聊天中有 **41 条包含 `memory brief` 的命令记录**，不是完整调用计费统计。0.11 后的科学验收问答一轮有 6 条，最后约 5 分 43 秒的计划文档修改一轮有 4 条；其中多次结果只保存到变量或 Out-Null。没有依据估算重复调用的实际价格。

当前生成源 [memory-enabled.md](../../../../experiments/20261106-basepack/src/basepack/project/templates/memory-enabled.md) 第 5、17 行要求“每个新的 PowerShell 进程执行整段”“新进程重新执行整段”，整段包含 brief。该文字可直接诱发重复，不应只归为调用方不节约。任务级 brief 与进程级参数初始化需分开；收尾动作也不应因为又一次 brief 失败而无法执行。

### U3：跨历史发现和已读信息整合均有遗漏

BP-T27 记录了前几轮只 brief、文件阅读和普通代码核查，没有完整检索 worker；主聊天调用记录吻合。用户随后提醒“之前要求按真实数据风格修改假设”，worker 才找到后续原话和已执行的大离散实验。

反证是调用方此前已看过大离散结果，回答也提过大误差失败；因此既有检索触发不足，也有阅读后的整合问题。原样本没有证明向量引擎漏召回。用户再提醒旧成果后，计划从初版改为承接弱模态、大离散和 K4 的增量路线，说明“找到文件”尚未充分转成“正确规划”。

### U4：fresh mandatory 仍陈述旧迁移范围

0.11 的升级收尾记录显示纲领修正批次被 `Evidence source revision mismatch for devDoc/archive/20261110-migration/basepack-test-findings.md` 拒绝。它指向证据文件，不能误写为纲领文件版本冲突；当前选留 summary 有原错，未找到独立失败 batch 的完整 trace。

后续 `tmp/acceptance-information-20261112/final-brief.json` 和检索子聊天的真实 brief 均保留同一条 `member:\`core-215d0628a802-file\``，修订 `9991c2b2251246acb86baceb0989f447`，正文为“2026-11-10 当前纲领：本次只迁移，不调整算法、不开展新科学实验或 GitHub 发布……”，但显示 `stale=false`、`mandatory_pending_count=0`。业务文件此时已有 active 研究计划。升级结果同时报告纲领来源登记 hash 匹配当前文件。

进一步核对外部草稿、两次 prepare 与升级前备份：使用的 findings 摘要在升级前已与原件不匹配；expected 并未缺失，但两次读包都没有把 findings 的当前原文放入 `sources`，只有旧 evidence/expected。因此不是已证实的维护中并发变更，也不是单纯刷新纲领即可修复。应显式加入报错证据路径，重读并重新接受相关依据，保留版本保护。

当前 `store.py` 明确保留旧发布态，`maintenance.py` 按每个成员自己的快照处理；已有测试覆盖 source 最新、旧 summary 待维护、旧 mandatory 仍 `stale=false` 的组合。因此该 fresh 标签不证明当前原件已接受。外部语义候选有无遗漏仍待定点复现；眼前已证实的是旧修正未完成及接续用错读包范围，不能改判为已证实的失效算法缺陷。

### U5：“缺乏遗忘机制”是产品需求，已有 retired 不等于闭环

用户明确登记 BP-T28，要求在外部项目搁置、将来由 basePack 修改。本次请求授权调查和制订整改计划，未实施退休/删除。

已有 `retired` 排除普通 brief/search，已知 ID 和保存 source_version 仍可回读；corrections 保存旧值。缺的是“仍真实的历史”与“撤销项”的持久区分、可发现的历史检索入口、替代条件及维护沿用。只搬到 archive 不改变召回；只去 mandatory 仍会普通搜索命中；单纯退役全部历史会损失历史发现能力。

旧 0.1 dB／1° 同时存在于真实代码默认、历史成功条件、用户否定该假设的原话中。已核检索摘要对后两者有条件说明，**没有找到把旧参数无条件称为现行科学目标的条目**。因此不能把本次回答偏差全部归为错误记忆，也不能按日期/目录批量清除旧实验。

### U6：检索 worker 找到原文，但未完成评分与 rank

0.11 的 `bp_mem_search_1` / tier1 / gpt-6-luna / max 最终自述 `TextEncoder is not defined`，`scored.json` 未写、rank 未运行；主 agent 随后依据原文完成问答。底层写文件失败工具项未在 read_thread 返回中展示，不能将 TextEncoder 定为 basePack Python 错误。worker 结尾开头写“检索已成功”与完整委托未完成也应区分。

本轮实际反馈 `feedback:ddbec3efd5cb4a6e8181a638c3f884a4` 为 pending；软件版本写入 issue，`observed_revision=null`。此前主 agent 误用 `memory feedback` 子命令、无 target 的 observed-revision，纠正后成功。需要修正提示和例子，不能通过伪造知识版本绕过参数合同。

### U7：HTTP500 发生在候选编码，未证明根因

0.10 冻结 batch 为 8 sources、36 members、5 nodes。原 trace 为 `apply → encode_candidates → client.embed → urllib HTTP500`，失败收尾 `registered_failed_source_count=0`、`published=false`。冻结 batch SHA256 为 `51916ea0264ea396fc3f98a52193f67f9f35b2d15318a974be1900157d7a9aa6`；trace 为 `1782fd0c08c624b356d8c7c00152e270a78c3becb4ebdca3feea59a488dc4bfb`。

尚未读取对应服务日志或复现，不能说是容量、内容、模型或数据库问题。0.11 其它批次成功也不证明这 8 源样本已解决。保留实际不部分发布的保障，后续先查因。

## 已有能力、历史问题与优先级反证

- BP-T22 的 0.6.2 目录输入错误是事实，当前版是否仍有同症状需定点核对；不以历史标签直接判现版缺陷。
- BP-T26 的 HTTP413 已有原生 WebSocket 事务分消息，以及本仓旧超限批次成功记录，见[维护改造结果](../../20261106-memory-system/maintenance-implementation-result.md)。不重复设计手工分批。
- 密码文件自动读取和新 shell 访问已经交付；不再添加密码环境桥。init/core doctor 的静态范围、Git 索引权限、旧聊天读取上限等依其实际所有者处理。
- 0.11 升级前后八表字段和 90 项旧 basis 保持、实际原子发布及 owner 释放是有效反证；不证明语义内容现行，也不证明所有积压完成。
- BP-T27 初始反馈文件是 pending，0.11 收尾投影已为 resolved；没有完整处置响应，不能把 resolved 当产品修复验收。BP-T28 与新增检索反馈在各自最新留存状态仍 pending，未查询当前外部库。
- 有界自动维护按业务结束停止是既定合同；不同截点积压数量不能直接比较吞吐。团队总 token/费用未知。一次升级为入口/配置变动逐份复制 3,121 份 artifacts、约 1.13 GB，是可评估的流程成本，尚未证明复制不必要。

## 本轮自用观察与限制

本仓 brief 正常。本轮长任务自动 maintain 先在沙箱中被 Codex 状态库 SQLite/arg0 权限阻止，原 owner 无 publications；stop/release 后用全新 control 在获准普通用户上下文重新启动，完成机械预检并按返回布局实际派协调者。该现象与外部宿主限制同类，记录为接续可操作性问题，不归为数据库损坏。

本轮未修改外部项目及其知识库、共享服务或项目纲领；没有执行产品修复和全库审计。临时调查分支与精选原证的路径在本任务材料中保留；自动维护最终实际范围和所有权收尾见本次 change_log。
