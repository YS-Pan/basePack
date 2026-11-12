# 使用整改实施进度

2026-11-12（北京时间）。用户授权执行[计划](plan.md)，以最终口径及 A–I 为范围。主 agent 负责接口决定、分支集成、普通安装、真实使用验收和 main 提交；独立“当前理解”层继续排除，外部阵列项目只读，不继承其维护授权。

## 当前交付

源码、普通wheel和本项目稳定客户端均为 **0.12.0.dev1**。全套623 passed/1 skipped，跳过的反馈恢复文件补齐专用CLI环境变量后8 passed；另有真实中文/空格路径检索、两个干净tier1委托、访问线索限定对照和11表原生恢复。详见[验收结果](acceptance-result.md)。本任务本轮实施完成，保留下列部署和长期使用接续，不将积压归零作为结案条件。

| 范围 | 已交付 | 证据 |
| --- | --- | --- |
| A/B/G | scope路径合同、每任务直接brief、默认retrieve、真实宿主委托及最终manifest协议，评分失败如实报告 | [检索结果](retrieval-result.md)及实际验收 |
| C | 独立已知不同步信号、证据冲突接续与拒绝不部分发布；真实副本mandatory已更正 | [mandatory结果](mandatory-result.md) |
| D/I | 精确知识历史、统一图固定端点、幂等交付、无时钟的全项目懒权重，rank不二次调权 | [历史/访问结果](history-access-result.md)及11表恢复 |
| E | 正确区分现行目标/授权/旧基线/工作假设，承接大离散/弱模态/K4，不从头重跑 | [业务对照](acceptance-result.md) |
| F/H | 冻结输入定位token超限，错误正文/候选定位/422源码；按变化边界恢复和普通安装 | [编码结果](encoding-result.md)、[配置维护](../../../experiments/20261106-basepack/docs/project-config-maintenance.md#按变化边界准备恢复集合) |

首版参数是稳定度8×(1+hits)，不是现实校准或收益保证。有/无访问线索的17候选单对照均正确采用关键前提；随机评分差异不能证明因果或净成本收益。团队token/费用未知。直接文件与worker总读取不具等价计量条件，保留观察但不宣称全面提速。

## 分支职责与实施起点

- A/B/G：`retrieval_entry` 实施检索范围、任务入口、真实宿主交付协议及相应模板/使用文档。
- C：`mandatory_conflict` 复现旧 mandatory 与证据版本冲突；已确认登记版本和已接受版本必须分开显示，不能把 fresh 当作已同步。
- D/I：`history_access` 协调知识版本回读、统一图关系及纯访问状态；共享 store/schema 由其统一集成。
- F：`encoding_failure` 定点调查冻结八源输入和共享服务原错，准备必要修复；当前目录拒绝已有边界及回归，复用。
- H/E：主 agent 准备按变化边界升级、隔离恢复及真实任务对照。开发环境位于根 tmp/basepack-dev，由 F 分支统一准备。

分支按项目 tier3 / gpt-6.1-sol / ultra 启动，子任务按实际难度解析配置。用量和费用目前未知，不将派工数量作为效果。

## 数据及默认合同（实施决定）

知识历史与交付均引用 `id + knowledge_revision`。新语义版本访问状态从基线开始，首版不推断版本等价、不继承旧热度。访问记账是独立短事务，不取得语义维护 owner；相同 delivery_id 和清单重试幂等，清单变化报错。空交付记录回执但不推进全项目事件；内部 search/read/rank 不记交付。宿主实际收到 worker 内容后确认清单，渲染命令和生成排名文件不当作已送达。公式及数值沿 D/I 实现结果记录，tier1 参考访问线索给一次综合分，rank 纯排序/去重/预算。

## 自用观察与接续

0.11.0.dev1 的启动 brief 正常。自动维护首轮在 Codex 状态库 SQLite/arg0 沙箱权限处失败，owner 无发布；已 stop/release。正常用户上下文以全新 control 重开成功，原错误保留。当前自有 control 为 `.basepack/memory/maintenance/usage-rectification-01a1d01b-user.control`，回执为 `.basepack/memory/maintenance/4b91364f321f4307a9386bc93f08c069.json`，协调者 `/root/bp_mem_coord_0`，固定 0 队/4 reader。已完成采集不等于语义接受，聊天存在原始覆盖缺口；业务结束时按 owner 实况收尾，不为维护积压延长任务。

## 收尾与后续

本机稳定解释器保留原0.10目录名，实际安装0.12；55包文件与源码/wheel一致，原八表字段、配置/UUID/凭据不变。恢复集合位于 `.basepack/memory/backups/usage-0.12.0.dev1-20261112/`，原证选留根 `artifacts/runs/20261112-usage-rectification/`。本轮不清理原件或研究artifacts。

自动维护成功52/107来源（51 initial、1 existing-change），余55源、一条重复ID反馈pending。`publisher-chat-20.json`在0.11客户端/0.5服务下HTTP500、未发布且未重试；同一时点服务日志显示2523token超过2048，未取得请求uid，不能声称逐候选精确关联。它与F冻结八源为不同失败样本。已有知识的ID碰撞结构已修，产品重复ID入口检查仍待处理。协调者及reader已结束/中断，stopped且publications=[]后release，最终owner=null。逐源版本、冻结快照与原错选留 `artifacts/runs/20261112-usage-rectification/maintenance/`。

剩余部署/使用边界：共享embedding仍为0.5，服务端422和请求索引须管理员后续安装服务包才生效；外部阵列正式库的旧mandatory及16个超限几何块仍由其任务修正/拆分后重新提交，本轮只读。存量未保存历史/旧端点仍有缺口；未来真实质量、成本和默认参数效果按使用反馈维护。未公开发布，未运行默认全库语义审计。
