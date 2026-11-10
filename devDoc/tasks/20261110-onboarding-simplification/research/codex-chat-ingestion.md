# Codex聊天来源缺口与接入依据

2026-11-10（北京时间）。本次为[计划F](../plan.md#f默认纳入所属codex项目的聊天)核定范围和入口，尚未实现采集器或导入聊天。

## 用户要求与已核缺口

完整读取[统计项目代码与记忆线程](codex://threads/01a1c568-0e63-7a32-94a4-508ffc4e1156)四个turn，分页 `hasMore=false`。其中确认：用户2026-11-04已明确要求默认纳入所属project所有thread，尤其用户prompt，subagent内容相对不重要；0.7.1没有聊天采集配置、读取或持续同步入口，新项目也受影响。不能把“缺少聊天采集配置”解释成用户尚未填某个已有开关。

该聊天用普通安装版初始化空项目，得到 `source_scope=[]`，没有聊天采集入口；本轮复读保留的 `tmp/20261110-project-audit/new-project-facts.json`，未重复初始化。`source_scope`目前仅声明文件/目录，批次 `context.chat/turn/root_chat`仅为审计留痕。当前项目文件覆盖与Codex聊天覆盖分别验收；文件来源全部已读、pending为0或向量齐全，都不能证明聊天已采集。

统计中主聊天、附着分支、subagent、审批记录有不同身份。人类prompt统计已排除注入和继承副本，并保留人类重复发送；这个目标需进入采集合同，不能按 `role=user` 或正文去重。原统计读取的两族消息ID并不相同，不能未经验证就混成产品canonical ID。

## 可复用接口与实际验证边界

按OpenAI Docs核对[官方App Server文档](https://learn.chatgpt.com/docs/app-server)，并用本机 `codex-cli 0.167.0-alpha.3.2` 的 `app-server generate-json-schema`导出schema。只运行版本、帮助与schema生成，没有启动App Server、推理或修改业务聊天。CLI有写arg0临时目录的权限WARNING，但上述命令exit 0；它不代表实际读线程成功。

- `thread/list`可分页，active与archived分别请求；需显式选择来源与提供者，默认sourceKinds范围不等于整个project。当前schema没有projectId列表过滤参数，Thread却有projectId；按项目筛选不能只用exact cwd漏掉同project其它worktree。
- `thread/turns/list`支持 `itemsView=full`，`thread/items/list`支持消息分页；`thread/read`的默认summary或宿主工具截断输出不足以证明正文完整。支持字段、分页和真实可取得范围仍须以本机接口闭环验收。
- Thread包含projectId、cwd、forkedFromId、parentThreadId、sessionId等信息；部分字段可缺失，path注明UNSTABLE。schema没有临时统计使用的 `attached_thread_parent_id`；附着分支归属不能直接照搬内部SQLite列。
- UserMessage有id、可选clientId、content；hookPrompt另分类型，但没有原始日志中的完整provenance结构。系统注入隔离、分叉/继承消息身份、parts与附件均需真实对照。`useStateDbOnly`可避免thread/list默认的日志扫描/元数据修复，但不单凭这个参数宣称整个宿主进程绝无写入。

因此F优先采用Codex现有读取协议和标准JSON/进程能力，不把临时SQLite/WAL/rollout脚本产品化，也不预建多宿主平台。项目绑定、真实分页、正文与身份先验；不满足时保留明确缺口，不以标题/摘要替代。

## 与现有记忆流程衔接

选择每chat稳定的项目局部UTF-8受管原文，再显式传给changes/prepare。它是带角色/ID边界的确定性投影视图：原样正文及其身份必须可无歧义还原，hash属于导出文件；它不是Codex原始日志副本。正文含分隔头、多parts或无末尾换行时也要保持。映射随来源版本保存，旧依据不依赖聊天日后仍可访问。

继续使用source/source_version、member/node/semantic、expected/apply与现有向量identity，不增加聊天专属知识库。collector只更新原件，不能sources-only接受后把“已抓到”冒充“已理解”；部分发布、stop、失败后的语义余项由E沿已有成员、依据和coverage_gaps继续发现。采集与发布共用任务control，已准入提交与stop的边界沿现行合同；查询仍纯读。受管原文与映射纳入项目备份恢复，Git和发行包不含聊天。

## 原证与余项

选留原证：根 `artifacts/runs/20261110-plan-consolidation/`，包括聊天阅读回执、分支复核、必要的本机schema、0.7.1空项目事实及既有统计规则。完整schema与试探材料仍在 `tmp/20261110-plan-consolidation/`；未复制本机完整Codex数据库或全部聊天。

本次实际完成聊天阅读、源码/存储合同复核、官方文档与本机schema核对；没有运行全量线程读取或入库，没有证明跨分叉去重、附件取得或默认接入已可用。F的完成条件负责收束这些未知；本轮交付是可执行的修改计划。
