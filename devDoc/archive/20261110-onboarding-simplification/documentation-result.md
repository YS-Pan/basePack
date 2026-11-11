# 接入与产品文档整合结果

2026-11-10。范围：本轮 A/G 与产品、system 文档整合，源码为 0.8.0 工作树；最终源码提交、产品回归与正式迁移状态由主 agent 汇总。免认证候选的产品文档已完整对齐源码，可供最终审查；是否采用该认证方案仍待用户决定，正式实例未升级。

## 已完成

- 根与 active 路线 README 的正文、表格、链接标签与示例自然语言已改为英文；修复根 AGENTS、setup-project、README 及技能调查的受影响英文锚点，保留中文产品文档的真实标题片段。
- 完整独立技能流程集中于 [项目接入](../../../experiments/20261106-basepack/docs/setup-project.md#独立-skills-安装与发现)：按需选择、完整目录复制或已有项目原件 junction、入口及相对引用检查、同名冲突保留、正确入口复用、忽略联接在新检出后重建、宿主实际发现验收。init/core doctor 与独立技能安装责任分开，wheel 合同不变。资源 skill 的文档链接改为公开仓库 URL，复制后不再依赖原层级。
- B 候选文档已移除旧密码用法：launcher 显式回环 bind、unauthenticated 与 allow-origin，新 shell 用固定 Python/绝对配置直接 brief；配置唯一限定显式回环 IP，UUID 防误连。部署动作旁写明实测浏览器简单 POST 可写、CORS 不阻写、本机 root OWNER 权限，未将 loopback 或 UUID 当访问认证。既有库的备份、停写、原 store/UUID、一致切换与回退窗口见项目升级；隔离和浏览器原证见 [认证结果](auth-result.md)。
- C 同步配置无关的 guide/rank/stop、检索统一 `{matches, vector_coverage}`、brief 删冗余字段，以及 state_dir 与 MemberContent/read_member 删除的升级说明。system 图撤下机器 state_dir 决定模型日志位置的失真连线；SCM/Shawl 显式日志路径和项目 jobs_dir 保持。
- E/F 文档说明独立 `memory maintain`：先宿主归属采集和机械小批，再将 `needs_semantic` 的必要变化按来源交 worker；控制文件、原字节快照、实际输入向量复用、未接受范围接续、积压与手动深维护的边界均沿实际接口。
- Codex 文档说明宿主自动提供项目绑定和完整注册根；显式项目 ID 优先，缺失时用 root/worktree/common-dir 与其它注册根排冲突。受管聊天导出、已发布快照消息身份/字节定位、discovered/unresolved/gaps 与语义接受分别可见。可读受支持的 localImage 按 hash 作为独立原图来源保存；真实附件、跨分叉/继承身份及全部聊天覆盖未验，未表述为完整交付。最终 E/F 实证边界见 [记忆结果](memory-result.md)。

## array reconstruct 实际修复与发现

先只读核 `D:/project/20261109 array reconstruct`：两项原件完整，6 个文件 hash 与当前维护源一致，当时没有 `.agents/`。主 agent 按本次执行授权创建 `.agents/skills/{agent-team,file-structure}` junction，指向该项目自己的 `skills/` 原件；只在其 `.gitignore` 加两条精准项，并沿原项目 `devDoc/system/basepack.md` 记录重建合同。外部 `main` 提交为 `931634e`，提交后工作区干净。未默认加入 engineering-judgment。

随后用受支持的 App Server `skills/list(cwds=[外部根], forceReload=true)` 核实际发现：两项名称均返回 `scope=repo`，路径解析至目标项目原件，`errors=[]`。原证为根 `artifacts/runs/20261110-onboarding-simplification/docs-array-skills-list.json`；探针为临时 `docs-array-skills-list.py`，只 initialize/list/close，未新建聊天、未启动推理。

旧技能调查的版本与未修复结论保留当时事实，新增日期接续到当前完成状态。未运行独立技能行为、触发、效果或收益测试。

## 检查与余项

临时静态检查器 `tmp/20261110-onboarding-simplification/docs-check.py` 检查 UTF-8、围栏、两份 README 英文正文和本地 Markdown 路径/标题锚点；当前轮覆盖 15 个文件与 219 个本地链接并通过；相关路径的 git diff --check 通过。源码帮助实测确认 maintain 的 scope/codex-registry/control/timeout/output、init 的三项宿主参数以及无需 config 的 memory guide。只读文档复核未发现阻塞缺陷；已澄清调查历史状态与已有技能入口直接复用的步骤，重建总进度的旧状态交由 root 统一更新。候选认证文档收敛后重跑相同检查通过；旧密码字段只在删除清单与旧实例迁移说明中保留，旧接续 fragment 已无仓内引用。

文件与命令帮助检查仅验证文档和接口匹配，不代替 root 的实际记忆、wheel、数据库恢复与浏览器验收。正式客户端和三个正式库仍按 0.7.1 认证运行，正式切换由独立授权窗口处理。
