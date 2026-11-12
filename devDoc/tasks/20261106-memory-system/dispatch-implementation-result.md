# 维护入口、并发与固定派工实施结果

2026-11-12（北京时间）。按用户授权执行[已定计划](task-duration-and-worker-naming-plan.md)，交付0.11.0.dev1。本项目独立客户端原位升级，源码、配置入口、英文prompt、测试与使用文档一起维护；其它项目和共享设施没有升级。

## 已实现的行为

- T2由业务主agent直觉判断经过时间，约十分钟以内保留brief并跳过整个自动maintain，范围明显扩大时重估；显式维护不受门槛限制，子任务不递归维护。brief与应启动维护的失败分别报告，不加入计时器。
- 安装agent显式传入容量与采集来源；ProjectConfig唯一解析`ai.max_concurrent_subagents`/`concurrency_source`。`config set-concurrency`定点补齐或刷新旧项目，保留其它配置；没有猜测宿主默认数或每会话扫描。
- [prompts.py](../../../experiments/20261106-basepack/src/basepack/memory/prompts.py)纯函数生成预算、队伍、名称、模型和权限。maintain默认manual，自动调用显式传automatic；实际可用额未知时标记organization_ceiling。本轮layout及AI设置随现有receipt保存，后续渲染不重算。
- 自动仅第0队；手动按每队1 coord+4 reader取完整队，余量留空，低预算单coord亲读。命名为bp_mem_coord_t/bp_mem_read_tr；coord_0唯一发布，其它coord必须带有界paths并返回最终稿/hash/覆盖，reader不发布。pending-dispatch只缩减未启动清单，新手动满队容量不足时留空，不改已启动名称和授权。
- 独立retrieval-dispatch/retrieval-prompt读取question/scope/content_budget，返回bp_mem_search_s及检索档位，一名worker完成搜索、证据阅读、评分与rank；零席位由主agent执行，不依赖维护回执/control/owner。
- 已交付[配置维护要点](../../../experiments/20261106-basepack/docs/project-config-maintenance.md)，按容量/模型、路径/入口、绑定/来源、数据库/凭据及共享设施变更解释读取和同步责任，安装/升级及生成instructions有条件入口。

## 实际检查

源码全套为444 passed、138 skipped；唯一ACL拒读断言在沙箱令牌下失败，在普通用户上下文单独补测1 passed。跳过项是未提供一次性数据库、真实模型等条件的既有集成项，本次未声称完成这些范围。新增测试覆盖容量0至30及队数上限、低并发、余量、模型/布局冻结、子队限定范围、发布职责、零席位检索、无数据库或凭据的渲染及原有owner合同。

普通wheel从源码目录外以`-I`导入，对配置、入口、prompt、CLI与owner运行226项检查。最终wheel、当前源码和本项目安装逐字节核对；实际版本、52个包文件及hash保存在选留的installed-verification.json。模板替换、UTF-8、相关链接/锚点和git差异另做文档检查。

宿主实际验证四层canonical路径可用，覆盖主agent→coord_0→其它coord→reader所需深度；同父同名再次spawn报`agent path ... already exists`；完成及interrupt后均能通过自有句柄followup。固定的是task_name及canonical路径，昵称/头像等独立展示字段未核。followup保留历史，独立检索不能为了复用名字混入旧查询；无兼容句柄时保留冲突并报告，不自行加后缀。未建立新槽位登记服务。

## 本项目升级与运行

本机有效Codex配置`agents.max_concurrent_threads_per_session=12`，不含主线程；未发现项目覆盖。已写入本项目容量快照和来源。无其它占用且材料充足时，自动为1 coord+4 reader，手动为2 coord+8 reader、余2席；未取得本轮实时额度时仅是组织上限。手动人数和多队权限经算法/渲染验证，没有据此宣称已跑完两支满队的全项目手动维护。

包仍安装在`D:/AgentTools/envs/basepack-client-0.10/`，目录名保留，实际版本0.11.0.dev1。旧维护stop、所有后代结束及owner释放后才升级。原UUID、七张表计数、meta、凭据与launcher摘要在升级和memory init前后相同；AGENTS/instructions自动刷新保留块外字节，随后仅定点更新本机instructions块外的版本说明。brief三条mandatory均fresh。没有迁库、轮换凭据或重启共享服务。

长任务启动时自动维护最初被沙箱对Codex状态库的权限阻止：失败运行已确认无发布并停止释放，随后在普通用户上下文取得所有权。该轮固定名称团队成功发布10个初始来源；停止前另批被MaintenanceStopped拒绝，未发布部分保留待办，没有不确定发布。

新版单coord实际验收只在本次Python配置对象设置C=3，磁盘快照保持12；worker使用保存的零reader布局，证明渲染未按磁盘C重组。复用已结束自有coord_0，亲自prepare/read/author/apply `memory/prompts/retrieval.md`全部1–12行，成功发布1 source、4 members，无缺口或错误；之后停止并释放。该固定回执其余111来源留后续，未将有界验收冒充全量维护完成。

实际以脚本返回的bp_mem_search_0、tier1/gpt-6-luna/max及干净历史派工，完成普通维护结束点/审计触发条件的检索、依据回读、评分与1600字符rank，交付可用答案及缺口；没有取得维护owner。已选留scored，worker的rank原输出在stdout，主agent仅用同一scored重跑纯rank保存证据，未重做检索或评分。

选留证据位于[本轮原证目录](../../../artifacts/runs/20261112-dispatch/)，包含升级前后快照、宿主能力、最终安装核验、检索评分/排序及最终owner=null。原始维护回执和control继续保留在本项目memory/maintenance，临时测试和批次材料在根tmp。本次没有要求或宣称全量手动维护已完成，也未宣称时长门槛已被性能对照证明最优。
