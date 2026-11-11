# 记忆 worker prompt 与全项目默认维护进度

归档：2026-11-11。0.9.0 英文模板、全项目默认发现、普通安装与限定样例验收已交付。生产待核、未接受来源及真实聊天/附件覆盖沿[记忆系统进度](../../tasks/20261106-memory-system/progress.md)接续；下文计数保留当时检查点。

2026-11-11。状态：实现、普通安装与最终验收完成。用户已明确授权 [计划](plan.md)；起点为干净 main `bd4e43f`、稳定客户端 0.8.1，现已普通安装最终 0.9.0。交付、依据和限制见 [结果](result.md)。下文保留实施与初版验证截面，最终状态以收尾为准。

## 最终收尾

最终 wheel 完整检查 **395 passed、0 skipped**（133.36秒），受影响源码 47 passed；源码/最终 wheel/隔离安装/稳定客户端的 42 个包文件逐字节相同。最终 wheel 在 `dist/memory-0.9.0-final/`，SHA256 `3bdb716795d09db9ca087904e38c920f18c9a2134555906b1e816d1725fd1d12`。与初版相比仅两份英文模板及 RECORD 改变，所有 Python 字节未变；最终完整 wheel 检查重新运行通过。

真实订阅验收先完成四个连续批次，独立核缓存条件、NEW-45 与署名；一份放错保留目录的 Markdown 夹具读出原始 JSONDecodeError，保留而不兼容回退。另一个合法 framed 独立项目两批正文/关系正确，但后验仍发现三来源的元数据/标题行缺口，推翻按来源参与计数的完成声明。由此收紧英文模板的逐 ID/范围完成条件，再以新 control 发布一批按真实全文件范围的摘要，正文依据保留原 ID。最终独立默认预检为 0 机械批、0 语义来源、0 待处理关系、needs_semantic=false；仍实际发现两份本项目捕获，foreign 排除，原件/旧快照/聊天字节定位均核实。该样例为合成项目与线程，不冒充真实宿主聊天完整采集。

生产后台维护在普通升级窗口前 stop 返回 true，两位 reader 中一位已完成、一位已中断，coordinator 已完成；main interrupt 也确认 completed，无活动维护或在途 apply。旧 stale 共恢复 20 成员、1 节点、8 关系，初始 426 降为 **397**；另新增 9 来源、55 成员、3 节点、4 条聊天关系，修正 12 个旧版但 fresh 的成员，退役一条错误关系。新增与恢复分别核证，没有将新来源计成旧积压消除。

最终普通升级后，main 独立核同一 UUID、七表计数、meta、mandatory 内容、397 pending 和 1274/1274 兼容向量与停写 baseline 相同；未作七表所有记录逐字段迁移比较。本项目入口已刷新，新 NoProfile PowerShell 实际 memory brief 返回 3 条 mandatory、397 pending。Codex 用户状态目录权限限制、未决归属/附件缺口和大量未维护候选仍保留。所有 fixture/audit controls 均按各 owner 收尾，隔离 18119 数据库已停止；生产 18080 和共享模型 8765 前后健康均 200。

## 分工与接续

- implementation coordinator 贯通 prompt 渲染、英文模板、全项目发现、CLI/生成入口、包数据和源码回归；其 reader/worker 分工由该 coordinator 持有。
- documentation owner 负责随包 skill、产品与现行 system 说明；validation owner 贯通隔离真实场景、完整源码测试及普通 wheel 验证。
- main 负责接口取舍、版本、开发记录、正式维护生命周期、普通安装、总验收与 main 提交。共享资源、原生产数据库及用户秘密保持各自合同。

实际组织使用宿主订阅 subagent，日常实现档为配置 tier3 `gpt-6.1-sol / ultra`，维护协调为 tier2 `gpt-6.1-terra / ultra`，reader 为 tier1 `gpt-6-luna / max`。真实后端 tokens/费用未知。

本轮后台维护沿当前稳定客户端默认项目范围启动，合并已有候选，不额外限为本业务 change_log。代码交付不以清空原 426 项待核为完成条件；收尾记录实际发布、覆盖和剩余范围。

## 当前发现

0.8.1 默认仅以配置 source_scope 发现新文件；已登记来源与 stale 关系仍全局合并。因此 `--scope` 并非全局排他过滤。本轮补全项目默认发现，区分受管材料与缓存/非支持格式，渲染命令保持无数据库/模型副作用。尚未运行本轮验收，不作安装或数据完成声明。

## 已推进与验证准备

英文模板、纯渲染模块及默认发现模块已有初版；实际接口为 `memory prompt --receipt ... --control ...`，reader 加 `--role reader --paths ...`，可用 `--tier` 覆盖计算档位。prompt 不提供写文件的 `--output`，调用者可自行保存 stdout。bare maintain 自动分配独有 control 并返回，异步宿主仍应在启动前自行指定 control。角色和源文件格式只由 owning 模块维护。

新增源码、模板和回归六项及本任务目录已登记当前本机 source_scope；0.9 默认 Git 清单交付前仍沿旧接入规则。锁文件离线检查通过。初次未指定 workspace uv cache 的调用遇沙箱 cache 权限错误；改为显式 `tmp/r9-uv-cache` 后成功，未改依赖或静默回退。

验证 owner 已准备独立认证 SurrealDB 与含空格/引号/中文的项目，使用真实共享 embedding，包含 tracked/untracked/ignored/显式纳入来源、历史待核关系及已登记聊天导出；尚待普通 wheel 与真实 prompt 团队运行。

## 源码与普通 wheel 验证

实现分支已交付：两个英文模板、只读渲染 CLI、Git/显式来源发现、旧有受管聊天与附件保留发现、control/worker 完整交接，以及生成入口。角色与 tier 独立，prompt 没有 `--output`，reader 获得实际独有 reading/batch 路径与筛过的回执提示；模板明确父生命周期、跨源共读、唯一发布者、发布后证据检查及持续接批。

受影响源码检查 47 passed；完整源码检查在最终素材/回归完成前为 393 passed/0 skipped。初版普通 wheel 源码外完整检查为 **395 passed/0 skipped**（129.05 秒），启用独立认证库、四项实际共享模型检查和本机 Condor policy 工具；初版源码与 wheel/隔离安装的 42 个包文件逐字节相同。无数据库/凭据/embedding 的 prompt 实调用、原生 PowerShell 引号与无写入检查通过。Git 默认发现实际覆盖 tracked/untracked/显式忽略纳入与旧来源/关系，排除缓存；真实宿主聊天未纳入该隔离验收的声明范围。

初版 wheel 保留在 `experiments/20261106-basepack/dist/memory-0.9.0/basepack-0.9.0-py3-none-any.whl`，SHA256 `c806a97e97c9939e865b9ece262334761bddcdb9d26d5cd5e3d2a2fbea9d854e`；最终 wheel 与补验见收尾。选留非秘密原证在 `artifacts/runs/20261111-memory-worker-prompts/`；没有复制密码、数据库 store 或模型。

真实隔离协调者已按 `worker` 的 tier2 配置执行生成命令，实际派出四位 tier1 reader。首个保留策略批次已发布并由验证 owner 独立核原文/快照：原件与数据库备份继续保留，仅在已接受知识及原始证据备份后可删除缓存，相关关系据此修订。协调者正在接续其余批次，尚未作本轮完整语义验收或正式客户端升级声明。

## 本轮正常后台维护

首次稳定客户端默认 maintain 因 Codex App Server 无法在受限沙箱初始化用户状态目录而失败，原错保留；按相同命令在正常用户上下文作一次针对性升级执行后成功，无 HOME/范围替换。回执 `.basepack/memory/maintenance/d325da336ce9417b8217b4ee5985a86a.json`：22 机械批、113 个复用 chunk、625 个语义来源、87 个待处理关系；聊天发现/采集 129、归属未决 336、缺口 11。采集与上述数量均不冒充语义接受。

维护 coordinator 实际持续推进，先后发布认证调查/正式升级三来源（14 成员、1 跨来源节点）和旧维护调查/0.8.0结果两来源（12 成员、1节点）；检索命中、neighbors 及各节点四条 basis 的精确版本/范围回读均已核。两位 tier1 的独立草案仍在接续；本轮未结束，不将初始 426 待核数量视为已清理。正式维护在共享客户端升级窗口前停止并记录最终状态。

随后已按稳定 ID 重核 embedding 服务/身份/模型及 jobs 的旧成员、节点和关系，并纠正示例仍称默认 text-only/可选 with-vectors 的 fresh 旧摘要及关系。查到的旧说明不当作当前事实，已发布批次均 query/精确 basis 回读；尚缺邻接测试端的条目保留待核。历史聊天批次因候选 2130 tokens 超出 2048 两次编码失败（无 forward、无部分发布），读服务端实际日志后按消息边界拆分才成功，原错及未截断原文保留。一次模板关系批次因 CLI 端依据版本变化被拒绝，未发布，等待稳定后重新共读；一位 reader 后续宿主回合返回 `This agent's turn failed`，未提供更详细原因。

中途只读 brief 为 403 待核（初始 426）、220 来源、1270/1270 兼容向量；这些信号单位不同，当前可用向量齐全不代表积压完成。后台维护尚未结束，最终数字以收尾记录为准。
