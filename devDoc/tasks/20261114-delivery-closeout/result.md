# 0.13.0.dev1工程交付

2026-11-14（北京时间）。按[原计划](plan.md)完成本轮工程实现、普通安装、本项目UUID库切换和共享服务更新。源码及本项目客户端、共享embedding服务均为0.13.0.dev1。公开Release仍须按计划获得授权；独立三工具沿各自项目接续，未在本轮改写其源码或发布状态。

## 产品变化与检查

| 范围 | 结果 | 实际依据 |
| --- | --- | --- |
| 检索调用/覆盖 | 状态和历史问题触发完整检索；freshness脚本一次返回新增、可能变化、正文已核覆盖和未知，worker按相关性补读 | 105项入口/prompt/新鲜度回归；同端点/同时间正文变化、采集后新聊天及AIGC后续发布数据流；实际宿主检索交付另记录下文 |
| 统一身份 | 新对象由freeze分配UUID，跨草稿位置引用有独立作用域；更新复用UUID与expected；冻结批次重放幂等 | 真实库新建/更新、冲突拒绝、重复来源/成员拒绝、HTTP和事务旧库拒绝且无写入；未保留旧协议/别名 |
| Condor | 删除PID回执/确认和客户端重复作业计时，保留原生策略、argv和提交恢复；观察到期不取消 | 62项相关回归；14393.0参数作业成功，14394.0观察到期仍运行，取消后实际进入history |
| 安装与入口 | 普通wheel从源码外导入；本项目切换并刷新AGENTS/instructions；新增薄安装skill被宿主发现 | 57个安装文件与源码/wheel一致，3条mandatory保留，AGENTS块外字节不变；skills/list返回basepack-setup、scope=repo、errors=[] |
| 共享服务 | 管理员更新0.5→0.13并重启原Shawl/SCM服务，模型/配置/identity与59项原依赖版本保持 | 图文均200、2048维、与基线余弦约1；超限422且原索引[1]、token数[21,2321,21]，空输入422；旧服务树已结束 |

最终源码全套在正常用户上下文 **618 passed、0 skipped，314.10秒**。使用独立18150数据库进程、实际共享模型及原生导出恢复；先前执行上下文中的ACL疑点在该轮通过。全套减少的旧用例是已退役的PID确认/客户端倒计时断言，不以跳过维持通过。源码外普通wheel另完成新建、回读、检索、更新、冻结重放和冲突无部分写入。首次临时smoke脚本的Windows换行与更新source字段错误已修正后通过，未据此修改产品合同。

## 成员离线迁移

停写前已结束自有automatic，owner=null。原生新鲜导出为342,005,980字节，恢复集合2400个文件共729,910,006字节（后续工具/报告另计），保存旧0.12 wheel、配置/凭据、入口、受管原文/图片及身份回执。正式恢复集合在`.basepack/memory/backups/delivery-0.13.0.dev1-20261114/`，不提交或公开。

冻结6513个成员映射并重算2785个相关派生键；只转换结构化身份，文本、图片、来源和向量输入保留。将同一导出还原到独立18153源进程，转换结果导入独立18152物理store；全部记录、schema、事件、索引、当前图端点逐项等价。迁前/后表数为：meta590、source1308、source_version1658、member6513、node80、semantic227、change11296、knowledge_version2839、access_state20、delivery3、feedback6。

随后用旧客户端对闭合目标核2个文本、2张图片、2个历史版本和2组邻接，已有3条delivery重放均duplicate，访问序号和状态不变。验证完成后才设置身份版本2；新客户端在隔离端点读取通过，再同时切换库/客户端。现用物理库是`.basepack/memory/store-0.13`，原serve.ps1仍监听18080。旧store保留恢复且不启动；项目UUID、凭据、源/知识版本和向量identity未换。

正常wheel没有迁移入口。离线脚本、旧执行wheel、说明及哈希清单作为恢复资料选留于`artifacts/runs/20261114-delivery-closeout/migration-tools/`及上述备份的`migration/tools/`；可审阅发行附件为`experiments/20261106-basepack/dist/basepack-member-identity-v2-tools.zip`。工具面向本次已核的SurrealDB4原生导出和十一表知识/访问schema；更老schema不自动转换，须在所属项目先准备相应升级及恢复。旧批次、旧语义回执和未确认交付不得重放到新库，需重新prepare；本次已确认的delivery按迁后等价清单验证。映射只留恢复，不供日常查询。

## 实际检索与反馈

已从新安装客户端实际派出tier1 / gpt-6-luna / max检索worker，使用请求`3988d87038834a83ab5a1b3d8621e58c`。当前等待完整结果和精确清单，尚未写成已交付或确认访问。本轮反馈结案状态在该结果收妥后补齐。

## 运行与分发边界

共享服务管理员更新于14:53:19开始、14:54:31完成；模型冷启动约66秒。服务仍Manual/LocalSystem，原Shawl定义和GPU配置保持，未扩验CPU、新机、最大负载或长期驻留。正常图文和错误定位是本次功能依据，不以SCM Running代替验收。

自动维护run为`5f60a0276a9d46c7aef4734f47b2d64e`：编辑中的cli.py变化使预检机械提交被拒，没有语义派工，已stop、确认publications为空并release。该次启动不记为维护完成；采集和前序机械变化留原回执，积压及新材料沿后续正常维护接续。独立18150/18153测试进程已结束，正式18080和共享服务保持运行。开发早期在旧正式进程下创建的同服隔离测试库只存在于已退役旧store，未导入新正式库，不把namespace隔离等同物理隔离。

用户继续收集收益、长期质量/成本、协作效果和新机部署反馈；本轮不组织这些评测，也未启动语义审计。团队按项目映射使用根agent、4个实现/准备分支（身份分支含3个worker）和实际tier1检索。总token/费用、主agent上下文/往返计量及完整团队耗时未由宿主提供，记为未知。

主要原证在`artifacts/runs/20261114-delivery-closeout/`：`verified.json`、`read-verification.json`、`installation-verification.json`、`wheel-flow.json`、`pytest-final.log`、`skills-list.json`及`condor/`、`service/`。数据库恢复export/映射/凭据仍在配置指定memory目录。发行wheel SHA256为`df7f34299a2af62401180cc77a76734a4d33b0f387398794a835db67c527c9d9`，恢复工具zip及校验清单与wheel同在dist。
