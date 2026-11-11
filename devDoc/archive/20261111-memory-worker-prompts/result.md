# 记忆 worker prompt 与全项目默认维护结果

2026-11-11。0.9.0 已实现、普通安装并完成实际验收，依据 [计划](plan.md)；过程、失败与后台维护细节见 [进度](progress.md)。

## 交付

- 随 wheel 分发英文 coordinator/reader 模板。`memory prompt --receipt <receipt> --control <control>` 默认 coordinator/tier2，reader 加 `--role reader --paths ...`，可显式覆盖 tier 而不改变职责。路径、档位、模型信息、实际工作/批次文件及回执提示由程序填充。
- 渲染沿现有 JSON 输出，不读密码、不连数据库/embedding，不创建目录、control 或其它状态，也不提供 `--output`。上级发送一条英文启动句和已生成命令，subagent 自己执行并遵循 `prompt`；真实宿主模型在创建时设置。
- `maintain` 默认枚举项目内 Git 已跟踪与非忽略未跟踪文件，合并显式包含、所有已登记/历史未接受范围和可归属的保留聊天/附件；非 Git 使用声明范围。来源发现与语义接受分别报告，格式或绑定缺口不隐藏。`--scope` 保持新文件发现覆盖语义，不冒充排他维护边界。
- 有语义候选才交 tier2 协调者，提供 tier/model/reasoning_effort/render_command；reader 默认 tier1。coordinator 持续接下一批、共读跨源关系、唯一发布并核正文/依据/逐 ID 和范围覆盖，业务结束由宿主 stop 后取消全部后代。特殊场景保留 main 临时英文派工，不增加审批层或后台调度平台。

实现入口为 [CLI](../../../experiments/20261106-basepack/src/basepack/memory/cli.py)、[渲染](../../../experiments/20261106-basepack/src/basepack/memory/prompts.py)、[发现](../../../experiments/20261106-basepack/src/basepack/memory/discovery.py) 与 [英文模板](../../../experiments/20261106-basepack/src/basepack/memory/prompts/)。使用见 [记忆说明](../../../experiments/20261106-basepack/docs/memory.md#自动维护与手动维护)。

## 验收

| 范围 | 实际结果 |
| --- | --- |
| 最终受影响源码 | 47 passed；无新增代码框架 |
| 最终普通 wheel，源码外 | 395 passed、0 skipped，133.36 秒；独立认证库、真实共享模型及本机 Condor policy 检查 |
| 普通安装完整性 | 42 个包文件在源码、最终 wheel、隔离安装、本机稳定客户端之间逐字节相同 |
| 纯 prompt | 无密码/数据库/embedding 时仍渲染；文件哈希不变、不创建 state；空格、中文、引号及字面 `$()` 经原生 PowerShell 验证 |
| 默认来源 | tracked/untracked/显式忽略纳入、历史来源/关系、两份 retained owned captures 真实发现；缓存/foreign 排除，非 Git 和错误边界有对应回归 |
| 真实订阅组织 | 实际 tier2 + 生成命令派 tier1，首样例连续四批核缓存例外、NEW-45 条件及署名；规范捕获样例两批及一批范围补漏，正文、保存的 basis、chat_locations/UTF-8 字节范围均独立核对 |
| 规范样例最终完成 | 再次默认维护预检机械批 0、语义源 0、待处理关系 0、needs_semantic=false；五来源与原快照不改，foreign 原字节保持 |
| 生命周期 | 本轮生产 control、三轮 fixture control 及验证 audit controls 收尾；所有 reader 结束或中断；隔离 18119 停止，生产 18080 与共享 8765 前后健康 200 |

首个样例一份普通 Markdown 被验证脚本放入要求 framed 格式的保留目录，read 按合同报告 JSONDecodeError；未修改原件或给产品加兼容回退，该负夹具单独保留。规范捕获样例首次“5/5”仅证明来源参与，独立预检仍发现三来源的标题/框架范围未覆盖。因此只修改两份英文模板，明确逐 ID/范围与真实全文件摘要的完成条件，再真实接续补齐；最终完整 wheel 检查重新运行通过。没有把框架头冒充用户正文或直接清除待核状态。

## 本机普通安装与生产维护

稳定 Python 为 `D:/AgentTools/envs/basepack-client/Scripts/python.exe`（3.13.17）。最终 wheel 位于 active 工程 `dist/memory-0.9.0-final/basepack-0.9.0-py3-none-any.whl`，SHA256 `3bdb716795d09db9ca087904e38c920f18c9a2134555906b1e816d1725fd1d12`；旧 0.8.1 和初版 0.9.0 wheel 均保留。

停写后比较 UUID、七表计数、meta、mandatory 内容、pending 和兼容向量均不变；安装没有写知识表，不冒充七表所有记录逐字段比较。本项目已刷新生成入口，删除本机旧逐文件登记门槛；新 NoProfile PowerShell 实际 brief 为 3 mandatory、397 pending。未改其它项目自有入口或扩大为其 0.9.0 功能验收。

本业务期间的正常后台维护沿旧稳定客户端默认范围持续推进，并按保存依据验收，恢复 20 个旧 stale 成员、1 节点、8 关系，原 426 降至 397；新增表示、修正旧 fresh 内容与旧待核恢复分别记录。升级窗口前 stop，再取消/确认结束所有子任务，不能用 stop 成功代替实际生命周期记录。

## 原证、限制与余项

选留非秘密原证在根 `artifacts/runs/20261111-memory-worker-prompts/`：最终包哈希/差异及 395 项日志、纯渲染检查、原始负夹具、独立范围审计与补漏证据、`production-final-installation.json` 和最后一次新 shell stdout。未保存生产凭据、store 或模型。进程、原文及快照条件与各次失败均在对应回执，不回填早期验证结果。

397 个生产待核对象、大量未接受来源、336 条聊天归属未决及 11 个采集缺口仍需后续任务接续；规范捕获验证使用合成项目/线程，不宣称真实宿主全历史或附件已覆盖。Codex App Server 的受限沙箱用户状态目录权限限制仍在，本次按实际权限错误在正常用户上下文执行成功。真实后端 tokens/费用未知，不作维护成本或全局召回收益声明。没有远端推送或 Release。
