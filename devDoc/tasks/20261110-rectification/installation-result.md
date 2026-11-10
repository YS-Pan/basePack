# 0.7.0 普通安装与项目升级

更新：2026 年 11 月 10 日。

共用轻客户端已从 0.6.2 一次普通升级至 0.7.0，三个正式项目完成备份、原 UUID 入口刷新及只读核验。随后主 agent 转达新的向量迁移要求，已停止进一步正式配置、入口和安装修改；以下记录保留已完成阶段，向量覆盖迁移尚未执行。

## 安装来源与轻客户端

交付 wheel 为 `experiments/20261106-basepack/dist/rectification-0.7.0/basepack-0.7.0-py3-none-any.whl`，SHA256 为 `742dad25435ffa061f2a4bff30a7abb9353ac6be227d7078fd804475c6dc8176`。旧 0.6.2 wheel 继续保留在 `dist/ai-tiers-0.6.2/`。

主 agent 先完成普通 wheel 全套回归 255 passed、0 skipped，再授权正式升级。升级前以 CIM 查询确认没有 `basepack-client` Python 进程，核对 wheel hash；使用 uv 0.13.7 对 `D:/AgentTools/envs/basepack-client/Scripts/python.exe` 执行一次普通 wheel 安装。安装后为 Python 3.13.17、`mode=wheel`，导入位置在该环境 `Lib/site-packages/basepack/`，安装来源指向上述 wheel。

Python 3.13.17、3.14.10 两个独立临时轻环境也普通安装同一 hash，完成 init、memory init、示例、search、read、neighbors、brief 实际闭环；仅含 basepack 0.7.0 与 psutil 7.2.2，无 embedding 重依赖及源码覆盖。3.13 的临时来源审计曾错误地要求可选 `archive_info.hashes` 字段，KeyError 原错保留，修正审计后通过；产品闭环本身已通过。

## 正式项目保护与核验

三个端点均已正常运行，未启动或停止数据库。每个项目在自己的 `.basepack/memory/backups/rectification-0.7.0-20261110-final-070/` 保存原生 SurrealDB export、前后配置和 instructions、已登记原件、必要 assets、逐表逐字段 digest、mandatory 与实际命令结果；外项目知识和备份未复制到本项目。

| 项目 | endpoint | UUID | 七表计数¹ | mandatory |
| --- | --- | --- | --- | --- |
| basePack | 18080 | `464948e9-d41e-420f-966b-ebaa602fd9bc` | 1 / 207 / 237 / 1533 / 21 / 194 / 2314 | 3 |
| array reconstruct | 18089 | `3b76dcd5-2b05-46fa-b73d-d6e9e4ba9e7f` | 1 / 36 / 39 / 272 / 21 / 21 / 430 | 1 |
| ppt memsys | 18081 | `ef685966-0442-4d93-8e6c-1c93efacca9a` | 1 / 7 / 9 / 34 / 0 / 2 / 60 | 2 |

¹ 顺序为 meta、source、source_version、member、node、semantic、change。

升级前仅调用只读 read/search，并直接读取 mandatory；旧 0.6.2 brief 会标记 stale，因此未用于基线。三个项目均以原 UUID 执行 memory init，basePack 保留原 `text`，另外两个补显式 `memory.search_mode="text"`。新生成的 memory 标记段已替换旧段，其余项目自有段保留；basePack 自有段中已失效的 0.6.2 临时限制被移除，ppt 自有段中的当前客户端版本改为 0.7.0。

三个项目的 read/search 基线与升级后实际调用均成功。升级后 read 的 source_version 与原快照一致，原文逐行比对保存的 source_version；指定不存在的快照时仍原样报 `Source snapshot not found`。brief 返回全部必保信息，明确不扫描或维护来源。memory init 及所有查询后，七表计数、整表 digest 和每个字段 digest 与备份前完全一致，含 stale、retired、历史、更正、来源和向量字段；未做历史清理、恢复 stale 或正式库维护。

## 证据与交接

临时核验脚本、中心摘要及安装日志在 `tmp/rectification-installation/`：`upgrade_projects.py`、`preparation.json`、`verification.json`、`shared-upgrade.log`、`shared-verification.log`、`light-client-summary.json`，轻环境原证在 `light313/` 与 `light314/`。中心摘要只保留安装信息、计数和 digest，实际知识与命令内容位于所属项目备份。

共享 embedding 0.5 环境、机器配置、Condor 与服务未修改；未执行 array 业务计划。收到新要求后保留已经安装的 0.7.0 和三项目当前 text 配置，等待主 agent 确认向量覆盖迁移的实施范围。本阶段不以消除记忆维护积压为完成条件。
