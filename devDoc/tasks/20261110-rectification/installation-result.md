# 普通安装与旧项目向量迁移

更新：2026 年 11 月 10 日。

共用轻客户端已普通升级至 0.7.1。三个正式项目均保留原 UUID、知识和来源，复用全部有效向量，默认配置切为 `vector`，并完成生成入口、新 PowerShell 凭据接续及实际检索核验。七表所有字段与升级前完全一致。0.7.0 的已发生事实保留为阶段历史。

## 当前安装

最终 wheel 为 `experiments/20261106-basepack/dist/rectification-0.7.1/basepack-0.7.1-py3-none-any.whl`，SHA256 为 `ec8d8a4cacf0c60eb518a960c601fa2b0c80e85d707e85ecab901013553f3b08`。主 agent 的普通 wheel 全套回归为 266 passed、0 skipped，含全部四项真实共享模型与原生恢复验收。

核对最终 hash、通过 CIM 确认共用客户端进程数为零后，使用 uv 0.13.7 对 `D:/AgentTools/envs/basepack-client/Scripts/python.exe` 执行一次 0.7.0 → 0.7.1 普通 wheel 升级。当前 Python 3.13.17，`mode=wheel`，实际导入来自其 `Lib/site-packages/basepack/`，安装来源指向该 wheel。旧 0.6.2、阶段 0.7.0 wheel 均保留。

Python 3.13.17、3.14.10 两个轻环境已顺序普通升级相同最终 hash，每环境 35 个包文件与 wheel 逐字节一致，仅安装 basepack 0.7.1 与 psutil 7.2.2。独立临时库按默认 vector 运行现行示例，apply 自动编码三个成员，search/brief 覆盖为 3/3、待建 0；`hybrid --literal` 对 A-17 返回 file/chunk 词法命中及 section 语义补充。原件改写后的快照 read、显式版本回源及 neighbors 均正确，临时数据库已退出，共享机器配置 hash 不变。仅观察到 uv hardlink 转复制提示，无产品失败。

## 0.7.0 阶段事实

阶段 wheel 为 `experiments/20261106-basepack/dist/rectification-0.7.0/basepack-0.7.0-py3-none-any.whl`，SHA256 为 `742dad25435ffa061f2a4bff30a7abb9353ac6be227d7078fd804475c6dc8176`。旧 0.6.2 wheel 继续保留在 `dist/ai-tiers-0.6.2/`。

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

升级前仅调用只读 read/search，并直接读取 mandatory；旧 0.6.2 brief 会标记 stale，因此未用于基线。0.7.0 阶段三个项目均以原 UUID 执行 memory init，暂保留原文字检索语义；新授权后已全部迁移为默认向量。生成入口仅替换 memory 标记段，其余项目自有段保留；basePack 自有段中已失效的 0.6.2 临时限制被移除，当前客户端版本说明随最终安装更新。

三个项目的 read/search 基线与升级后实际调用均成功。升级后 read 的 source_version 与原快照一致，原文逐行比对保存的 source_version；指定不存在的快照时仍原样报 `Source snapshot not found`。brief 返回全部必保信息，明确不扫描或维护来源。memory init 及所有查询后，七表计数、整表 digest 和每个字段 digest 与备份前完全一致，含 stale、retired、历史、更正、来源和向量字段；未做历史清理、恢复 stale 或正式库维护。

## 旧项目向量迁移

在 0.7.0 基线提交 `461e45b` 后，按新授权逐项目运行 memory embed 确认已有向量复用，并把默认配置切为 `vector`。共享服务 health=200，语义身份保持 `Qwen3-VL:4e32ece7973113a13abd40dcbe5e5e4c8592f172f75535dc087f74f5269bba9e`。

| 项目 | 有效发布范围 | 兼容向量 | 新编码 | 覆盖待建 | 既有 stale / retired |
| --- | --- | --- | --- | --- | --- |
| basePack | 1191 | 1191 | 0 | 0 | 342 / 3 |
| array reconstruct | 272 | 272 | 0 | 0 | 0 / 0 |
| ppt memsys | 30 | 30 | 0 | 0 | 4 / 4 |

有效发布范围仅含 `stale=false AND retired!=true` 的成员；既有 stale/retired 保留，不计入待建。所有有效向量均为 2048 维、数值有限，身份及输入版本兼容。因为全部可复用，本阶段没有提交补建编码请求；随后每个项目的默认 search 与 brief 实际调用共享模型并命中代表性成员，read 按其 source_version 逐行回源。三项目七表逐字段 digest 完全不变，包含向量字段、知识、ID、来源、历史和必保信息。

最终 0.7.1 已再次按原 UUID 刷新全部入口。逐项目核验默认 vector search/brief、hybrid literal 的词法命中标志、拒绝纯 text 及 vector literal、快照 read；三个新的 NoProfile PowerShell 进程从其它 cwd、移除继承密码后，直接执行生成的 bootstrap，全部成功。再次比对七表全部字段 digest，仍与最初备份相同。

ppt 原缺 `[ai]` 已按既有升级合同只补缺项，采用本项目当前宿主映射；未覆盖已有配置。实际 `config ai --purpose retrieval` 返回 `tier1 / gpt-6-luna / max`。配置前后快照已纳入该项目备份。

## 证据与交接

必要安装摘要、脚本和日志已选留 [artifacts/runs/20261110-rectification-installation](../../../artifacts/runs/20261110-rectification-installation/)。其中 `preparation.json` 与 `verification.json` 记录 0.7.0 阶段，`vector-migration.json` 记录复用迁移，`verification-071.json` 记录最终逐项目检查，`shared-upgrade-071.log` 与 `processes-before-upgrade-071.json` 记录最终安装及进程排空。中心证据只保留安装信息、计数和 digest，实际知识与命令内容保留在所属项目备份。

每个项目的向量迁移、入口刷新、独立 shell、模式错误与快照 read 原证在其自己的 `.basepack/memory/backups/rectification-0.7.1-vector-20261110/`。一次性完整材料仍位于 `tmp/rectification-installation/`。

共享 embedding 0.5 环境、机器配置、Condor 与服务未修改；未执行 array 业务计划。本阶段不以消除记忆维护积压为完成条件。
