# 一致性审阅与修复进度

2026-11-11（北京时间）。用户要求完整浏览评估近期变化，然后修复，最后维护记忆系统。

## 当前阶段

归档：2026-11-11。本目录的 0.9.1 修复及固定 38 来源维护检查点已验收，见 [评估](assessment.md) 及下文实际范围。基线为干净 main `2cd513b` / 0.9.0；确认六组实现/交接问题和三组文档问题。0.9.1 修复、最终源码与普通 wheel 检查、稳定安装及正式旧依据兼容核验均已通过，修复提交 `eb0b5b0`。检查点备份已完成；全项目知识维护继续由[记忆专项](../../tasks/20261106-memory-system/progress.md)承担。项目纲领不变。

修复分工：maintenance owner 持有 M1–M3、相关 CLI/prompt/skill 和回归；knowledge owner 持有 K1–K3 及回归；contracts owner 更新受影响的现行文档；主 agent 持有跨分支判断、版本、记录与 main 提交。验证 owner 用独立认证数据库检查源码和普通 wheel，不中断共享模型或正式库。各文件一个写入 owner。

## 修复与验证

- M1–M3：机械候选按依据依赖共同发布，后批刷新知识版本；外部依据缺失或版本不符时明确留语义候选。零正文无活动知识只登记来源；清空旧知识仍处理成员/关系。语义 receipt、提示词和 skill 交接项目 ID 及采集/保留原件入口，按同项目、同附件核出处并保留多个真实来源。
- K1–K3：新快照保存路径并区分路径版本；同源旧版本保留原读取资格，跨来源由成员历史证明来源归属。同字节跨路径并发用 source.version 拒绝覆盖。rank 区分版本、范围、图片 locator 及摘要/标题更正；图片写完唯一临时文件后原子发布。
- 新回归先在修前版本得到预期失败，再核修后通过。初轮专项为维护 39、CLI/prompt 42、snapshot 8、selection/images 22；其中包括真实隔离库及未变移源表示的向量复用检查。首轮独立代码审阅未发现确证残留，后续正式知识兼容实调另发现下述 K1 回归，未据专项测试提前升级。
- 初版完整源码 **428 passed、0 skipped，130.90 秒**，从 active src 导入；使用独立认证 18127 数据库、真实共享图文 embedding、原生恢复和本机 Condor policy 工具，不提交真实重任务。最终兼容补验与普通 wheel 结果见下节。
- 文档 owner 已核 16 份 Markdown、280 条本地链接和 62 个锚点；管理员页 16 段 PowerShell 在 7/5.1 解析通过，IPv4、IPv6、默认 HTTP 端口解析通过。版本声明和 lock 的 15 条直接/extra 依赖对应，未改变依赖；当前环境无 uv 命令，改用 tomllib/packaging 核对应及原生 build 隔离构建，未安装新 uv。
- 正式库备份在 `.basepack/memory/backups/consistency-0.9.1-20261111/`，含原生 export、完整七表、原配置/入口/凭据和必要 assets/聊天原件；导出前后记录完全一致。基线为 220 来源、1596 成员、25 节点、198 关系、397 待核，三条 mandatory 保持。

临时修前/修后原证和验证脚本在根 `tmp/20261111-consistency/`；需要长期复核的最终证据在收尾时选留到根 artifacts，不纳入 Git。团队 token/价格与主上下文分项不可核，记为未知。

## 普通安装与正式知识兼容接续

初版 0.9.1 wheel 已构建并隔离普通安装，42 个包文件与源码逐字节相同。首次源码外全套为 417 passed、11 failed，均因新临时测试环境未补齐 source-env 的本地模型测试依赖，原日志保留；仅在本轮 wheel-env 按相同版本补齐，未改系统、稳定客户端或共享服务。

主 agent 随后用新 wheel 只读核全库非退役 member/node/edge 的 1128 个独立 basis，1070 成功、58 失败。稳定 0.9.0 重试这 58 项全部成功，证实 K1 初版收紧了旧 same-source 读取合同。独立复核确认这 58 项全部同源、成员版本已被旧流程重绑定，direct/nested change.previous 都无精确旧版本；只补分组历史查询不足。暂停最终构建与升级后，恢复原同源读取资格，跨来源由 direct/nested 成员历史证明来源关系，不强求旧版本恰有成员 accept。旧无路径快照优先精确版本路径，否则必须有唯一可核来源成员路径；不猜测有歧义的旧位置。

修正后新增四例兼容回归均先红后绿，snapshot 完整组 12 passed；同一生产失败集新源码 **58/58 成功**，包括旧重绑定后未来再次移源的回归。最终源码全套 **432 passed、0 skipped，138.61 秒**，独立终审通过；新 wheel 在独立 `dist/consistency-0.9.1-final/` 构建，源码外全套 **432 passed、0 skipped，148.99 秒**。初版 wheel 与负验记录保留，不作为最终交付。

最终 wheel 为 `basepack-0.9.1-py3-none-any.whl`，92,928 B，SHA256 `1843a2df3630c094775b81d78ded799527230fce8365bc1e8d0d92629c39f3cc`。源码/wheel/新普通验证安装/稳定安装的 42 个包文件集合及字节相同，当前 README 与 wheel metadata 相同。主 agent 再以最终 wheel 实调全部 **1128/1128** 既有独立 basis，均能精确回读；不是只复测 58 项。

稳定客户端已普通 no-deps 升级为 0.9.1，项目本机入口的版本说明更新，新 NoProfile PowerShell 按实际 memory 围栏执行 brief，通过三条 mandatory 与 397 pending。正式七表全部记录与备份逐表 digest 完全一致，项目 UUID、mandatory 及 1274/1274 兼容向量保持。配置/凭据、数据库与共享服务保留原实例；未写外部项目。选留非秘密原证在根 `artifacts/runs/20261111-consistency-review/`，秘密和原生 export 仍只在本项目忽略备份目录。

## 修复后记忆维护

已刷新宿主完整项目注册清单（本项目绑定及 36 个其它本地项目根），普通 0.9.1 在正常用户上下文执行默认全项目 maintain。回执 `.basepack/memory/maintenance/53771a8479a3412ca3c96eea5a61a4f0.json`：12 个机械批次、64 个复用块；838 个发现来源，无文件格式缺口；658 个语义候选来源、78 个待处理关系。Codex 发现 134 个明确所属聊天，保留范围 545 个来源，336 个全局归属未决与 9 个采集缺口继续显式保留。发现/采集均不等于已接受。

Codex 卡住并由用户重启。接续时核 main 干净、稳定版本 0.9.1、原回执及数据库仍在；brief 为 222 来源、397 pending、三条 current mandatory 和 1274/1274 兼容向量。原 coordinator 停在 pending_init，没有工作产物或语义提交。已 stop 原 `20261111-consistency-review.control` 并 interrupt 原句柄；新 coordinator 沿同一固定 receipt、使用 `20261111-consistency-resume.control` 接续，不重复采集。优先清单为本轮 38 个变更来源及关联旧知识。

### 最终语义验收

| 范围 | 实际结果 |
| --- | --- |
| 本轮 38 个优先来源 | 全部有完整范围及原文依据；uv.lock 全文解析，使用 6 个有意义片段与全文摘要，不机械生成 113 个行切片 |
| receipt 的 337 个旧 member | 327 更新为 active fresh、10 显式退役；逐 ID 回源，未以新增摘要代替旧知识处置 |
| 初始 8 node + 46 edge | 46 重写、4 退役、4 有证据保留原 fresh basis；54 项均独立验收 |
| 依赖扩展与端点 | 无本轮新增、仍活动的 stale 关系；全量 fresh edge 的 missing/retired/stale 端点问题为 0 |
| 额外范围 | 5 个来源仅接受 14 个局部表示，不计整源完成 |
| 启动与索引 | 三条 mandatory 原文保持，mandatory_pending=0；1694/1694 兼容向量、待编码 0；原子发布/旧快照两项实际检索与 read 通过 |

另从 185 个有界、非优先旧文本来源用固定 seed 随机取一对，共读旧 0.4.0 交付与当前资源指南，发现并接受一条有依据的新关系：历史 300 秒空闲退出不能替代当前服务常驻、timeout 仅结束等待的合同。两侧保存的版本和范围独立回读通过；不推断切换版本或当前运行实况。

维护中纠正了历史“待实施”摘要被当当前状态、prompt 计算路径被误述为创建目录、以及当前测试源码被用作旧执行结果依据等问题。独立验证还发现 environment 当前资源入口残留“上节 0.9.0”指向；已改源为“本页最新安装记录”，重交受影响块与摘要，原历史实测条件不变。历史 94+1、旧客户端 3 fail/1 pass 原证仍可回读和检索，不将退役跨版本关系解释成否定历史事实。

原错误均保留：1,118,652-byte SQL 遇 HTTP 413 后按来源/依赖拆成小批；误填 config 路径在读配置时失败；GPU 证据旧行移动及 init.py 内容改变被依据校验拒绝；旧 expected 被版本检查拒绝。失败批未计接受，重新 prepare、共读后才提交，没有静默回退。日常 reader 使用 tier1；复杂 store/history 按实际困难显式升 tier3，协调者为 tier2。

### 收尾与明确余项

两份 control 已 stop；新 coordinator 及全部 reader 已结束并经 interrupt 句柄确认，旧 pending_init 句柄已发取消且其旧 control 持续为 stopped。正式库与共享服务保留运行。维护后备份在 `.basepack/memory/backups/consistency-0.9.1-20261111-after-maintenance/`，含原生 export、七表记录、配置/凭据和必要 assets/聊天原件；导出前后全记录相同，UUID 和 mandatory 保持。

最终为 235 个已登记来源、1773 member、25 node、199 semantic、3305 change；全库 pending **397 → 100**。固定 receipt 中还有 620 个原候选不在本轮完整接受声明内，336 项归属未决与 9 项采集 gap 保留；本轮 capture 没有真实 managed_attachment location，未宣称真实附件 locator 闭环已验。向量齐全不代表这些来源或全历史聊天已完成语义接受。

独立完整报告、逐 ID/关系审计、实际检索和原文证据选留在根 `artifacts/runs/20261111-consistency-review/memory/`；完整批次与原件仍在本项目 `.basepack/memory/`。本段收尾补写发生在固定语义检查点后，由下一轮正常变化发现接续，不反复采集当前聊天或为收尾数字自循环维护。

收尾 4 份 Markdown 的 UTF-8、围栏、61 条本地链接与差异检查通过；最终 wheel hash 与源码/稳定安装的 42 个包文件仍一致。此阶段只有文档和记忆变化，没有重复运行无关功能测试。

剩余历史待核、原候选及真实附件验证沿 [记忆系统进度](../../tasks/20261106-memory-system/progress.md) 和其后维护回执接续。本目录只结案上述已验收修复与有限维护检查点；此前在 100 项待核处停止是主 agent 自行收窄范围，未获用户同意，也不是系统上限。全项目知识维护目标仍在进行。
