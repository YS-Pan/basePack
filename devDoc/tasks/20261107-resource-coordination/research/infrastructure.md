# 初次共享设施调查

2026 年 11 月 6 日的只读调查，从原重建调研迁入资源任务；下文保持该时点观测。后继环境观测见 [系统环境说明](../../../system/environment.md)，当前实施与认证复核按 [资源计划 R0](../plan.md#r0-复用准备与预算标定)，不能以此历史调查替代当前接入验收。

## AgentTools 当前可复用部分

基础设施 subagent 本轮只读观察 `D:\AgentTools`：顶层有 `models/`、空 `profile/`、`state/`。模型目录保存五套固定版本，逻辑总量约 15.42 GB；并非所有依赖与调度代码均已集中于此。系统 Python 3.13.17 和 169 项依赖闭包是历史部署报告，当前实施前再核实际环境。

五类现有模型为 BGE reranker、E5-large、文字 Qwen3-Embedding-4B、多模态 Qwen3-VL-Embedding-2B、MiniLM。各有版本锁。新项目优先复用所需的一套，不重复安装全部；权重及锁运行状态均不进仓库。

已有 `state/locks/gpu-0.lock` 只服务于遵守同一 OS 文件锁协议的项目 Qwen bridge。锁文件存在不能证明正在占用；它不是全机资源管理器，不约束外部直接 CUDA 程序，也没有 FIFO 队列或统一 CPU/RAM 管理。AgentTools 没有已实现的 agent-run/MCP 统一入口。

本轮 `condor_version` 返回 25.4.0，`condor_status -json` 成功看到本机空闲 slot，16 CPU、约 48 GB RAM、一张 RTX 4060 Ti。`condor_q -json` 返回 `AUTHENTICATE:1005`，当前队列不能核实；读取服务状态也被权限拒绝。旧聊天曾报告 job 14255 退出 0，这是历史提交成功，不能替代当前认证核验。

指定聊天中的精确定位，下面时间已换为北京时间：

- 11 月 4 日 09:40，turn `01a1a436-b689-70a0-9063-c06d3c5b62fe`：GPU 锁、CPU/内存/磁盘协调的实际边界。
- 11 月 4 日 10:29，turn `01a1a464-1fe5-7030-8f0f-85b9d32d5060`：agent-run 未实现与 HTCondor 方案。
- 11 月 4 日 10:57，turn `01a1a47d-b449-7131-afd5-b748ae00f857`：历史轻量提交测试。
- 11 月 4 日 11:02，turn `01a1a482-17d5-7a73-afb2-5d99ad06ecfe`：官方 CLI 与 Python/MCP 接入判断。
- 11 月 3 日 21:14–21:57 的相关用户消息：保留空 profile、复用 pip 缓存、模型集中；实施不应反向补建 packages/profile 管理层。
