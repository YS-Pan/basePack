# 安装与已知调用方核验

2026-11-10。0.8.0 本地候选 wheel 已完成普通安装与全套 354 项回归，新项目、旧库恢复、真实共享编码及聊天来源闭环均通过。本验证分支没有升级稳定客户端、停止正式数据库或改写外部项目；主 agent 的 A5 外部技能发现接入另见提交 `931634e`。正式采用免认证候选、升级与发布仍由用户决定。

## 已知仓外调用方

范围沿上次[正式安装记录](../20261110-rectification/installation-result.md)及其 `preparation.json`：`D:/project/20261109 array reconstruct`、`D:/project/trifles/20261109 ppt memsys`。只读检查业务源码及 `.basepack/` 下未归档 Python，不扫描其它磁盘位置、历史备份或大型产物。

| 项目 | Python 范围 | 待删接口依赖 | 仍需迁移的入口 |
| --- | --- | --- | --- |
| array reconstruct | 71 份业务源码；2 份记忆迁移批脚本 | 未发现 `include_coverage`、`read_member`、`MemberContent`、`state_dir` 或密码 API；批脚本只导入保留的 `read_source` | 配置及生成 instructions；自有 `devDoc/system/basepack.md` 的密码说明和 `.basepack/instructions.md` 末尾手写密码提醒 |
| ppt memsys | 无业务 Python；3 份记忆 intake/job 脚本 | 未发现上述依赖 | 配置及生成 instructions；`scripts/basepack.ps1` 仍可选读取 `password.txt` 并设置密码环境变量 |

共享机器配置仍含旧 `[shared].state_dir`，本轮未改该文件。以上结果支持删除已查范围中无人消费的 Python 接口，不代表未知仓外调用方都已迁移。正式免认证切换需同时处理项目自有入口；只刷新生成标记段不能移除它们。

## 隔离验证准备

源码与普通安装分别使用根 `tmp/20261110-onboarding-simplification/validation-source-env/`、`validation-wheel-env/`，均为 Python 3.14.10。依赖复用先前隔离 CPU 环境的 pytest 9.2.0、PyTorch 2.10.0+cpu、Pillow 13.0.0、Sentence Transformers 6.2.0 和 psutil 7.2.2。源码环境 editable 安装 0.8.0，已核实际导入本路线 `src/basepack/`；最终包普通安装到 wheel 环境自己的 site-packages，无源码覆盖。38 个包文件与 wheel、当前源码逐字节相等，包内 memory skill、schema 和模板完整。

产物为 `experiments/20261106-basepack/dist/onboarding-0.8.0/basepack-0.8.0-py3-none-any.whl`，SHA256 `58463238f157d38a1d8644820223552713f64d45e17211edcc77588ef1fc12be`。构建、安装仅有 uv 跨文件系统 hardlink 转复制提示；最初未指定 uv cache 时遇到沙箱缓存 ACL 错误，按既有项目内 cache 设置后正常，未改产品。

原生 SurrealDB 为既有 4.0.0 程序；预检端口 19161/19162 可用，最终回归分别使用自有一次性进程，结束时核进程与监听退出。共享 embedding `8765` 的 health 为 200，机器配置 SHA256 为 `0d480e3b17606c25e9ed8e6d07339d3d25e02c65ca3efbcf2c4d3b1d7afc70b8`；只连接既有服务。

Codex App Server 的最小 initialize/close 在受限沙箱中因 `.codex` SQLite runtime/arg0 目录 ACL 失败；相同调用经自动审查获准在正常用户上下文执行后通过。真实聊天采集沿此上下文验证。指定聊天导出留在忽略的 tmp，默认项目导出留在 `.basepack/validation-onboarding-codex-20261110/`，均未复制到长期证据目录。

## 实际回归

首次源码全套 339 passed、0 skipped，55.26 秒；包含真实共享模型及原生恢复测试。期间 `maintenance.py`、`codex_binding.py`、`test_memory_codex_binding.py` 接收定向修复，前后 hash 已记录，作为整合基线。冻结后相关组 85 passed、4 failed；失败均是测试 helper 使用旧 `_render` 参数，修正 fixture 后 locator/snapshot 8 passed，最后 binding 修复组 6 passed。最终普通 wheel 全套 **354 passed、0 skipped**，33.91 秒，源码/测试 hash 全程未变。所用一次性数据库均已退出、端口关闭。

新项目在中文/emoji 路径与其它 cwd 中完成无密码环境变量/文件的 init、prepare/apply、brief、vector/hybrid、read、neighbors、生成入口新 PowerShell，以及 UUID 误连和非回环拒绝。真实共享模型发布 3 个成员。随后薄包装真实 EmbeddingClient 计数：mtime 单独变化编码 0；全文件 LF→CRLF 仅 1 个原文块编码，2 个摘要复用；两次均无语义候选、语义 worker 派工 0，重复维护编码 0，旧版本仍精确回读。

旧库流程复用配置 owner 已只读导出的 0.7.1 原生备份与 assets，恢复到另一临时 endpoint 和新项目根，不再访问正式库。0.8.0 普通安装按原 UUID 执行 memory init，brief、真实 vector/hybrid、文字/图像快照及图关系通过；7 表全部记录逐字段不变，含 1539 成员、240 来源版本、194 关系与 1197 个兼容有效向量。原业务文件不在新根，旧快照仍正确回源。

## 聊天来源闭环

使用宿主实际 project ID 与全部 36 个其它注册本地根，普通 wheel 默认发现/采集一轮：3912 条全局元数据中 122 条匹配本项目，3454 条排除，336 条 cwd 不可取得而保留未决。沿已核父级补采后得到 492 个来源、6161 个正文 part、5,752,550 字节；其中 450 个带父级、102 个带 fork 关系，两者可重叠。匹配的 1 个归档聊天已实际导出 2 个文本 part。排除 ID 与实际导出交集为 0。

重复默认采集 492 个来源 hash/mtime 全部不变，零重写；本次截点没有观察到活动聊天新增。未运行全历史语义发布。10 条缺口保留：6 个聊天无可导出正文，4 条被引用 subagent 父级不符（两个 ID 各被引用两次）；336 条全局不可归属元数据不算成本项目已采集。正式 config、instructions、launcher 与机器配置 hash 前后相同，三个正式库及共享 embedding 的 ready/health 最终均为 200。

指定历史聊天另走真实共享模型闭环：主聊天 22 个文本 part 与独立 App Server 全文读取逐字节一致；重复采集不变，stop 先到阻止发布，新 control 接续成功，旧 source_version 精确 read，未变成员重新接受编码 0。初次临时 driver 把最后查询的编码计入重发数，修正统计时点后复跑通过，产品未改。

语义验收由 agent 共读真实人类 README 英文要求与计划 G 第 140 行，成功轮发布两块、另发两个真实模型查询。英文语义 query 经 vector 与 hybrid 均找回原用户要求；精确 thread/turn/item/part 定位、用户及计划版本快照回读通过。发布的 decision 保留两项 basis，并有计划→用户要求的有据关系。初次 driver 使用另一 memory_dir，无法按当前受管来源识别 chat locator；该失败轮已消耗相同的两块编码及两个查询。改为同一隔离采集目录后通过，未改产品。

真实附件导出、不同机器安装、长期维护净收益未在本轮取得实证；本轮不重做 CPU/CUDA 性能、Condor 作业或技能效果试验。默认采集不是全历史已理解，隔离候选验收也不代表正式实例已经切换。

选留原证在根 `artifacts/runs/20261110-onboarding-simplification/integration/`：构建/安装与字节核验、源码及 wheel JUnit/日志、实际新项目/恢复/机械维护/聊天验收的无正文回执、driver 与环境信息。一次性完整材料仍在根 `tmp/20261110-onboarding-simplification/validation-*`；聊天原文和旧库 export 未进入 Git、wheel 或长期证据副本。
