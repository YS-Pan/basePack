# 开发环境核验

## 2026-11-13 三工具共用系统 Python

用量统计 0.2.0、AIGC 0.10.0、TTS 1.2.0 已普通安装到系统 Python 3.13 的机器 site-packages；新增 97 包、原 232 份全局版本保留，pip check 和实际调用通过。模型复用至 `D:/AgentTools/models/{aigc-detect,tts}`，用量状态在 `D:/AgentTools/state/codex-usage`，原源码位置不变，未新增常驻工具虚拟环境。完整检查、回退定位及限制见 [迁移结果](../archive/20261113-agenttools-migration/result.md)。

本轮 Condor 普通 GPU 池实测为 7164 MiB。槽账户不能读取私人 user-site，也没有普通用户 profile；不要用环境变量伪装 ysPan。测试按实际账户设置名称、显式传入可写缓存，HTTP/TTS 作业内禁用现有 Pydantic `logfire-plugin` 后实际运行通过；没有改变全机插件、ACL 或资源预算。更早各节的池额、安装位置与服务状态保留其历史时点。

## 2026-11-12 0.12使用整改安装

本项目稳定客户端路径仍为 `D:/AgentTools/envs/basepack-client-0.10/`，实际普通安装0.12.0.dev1，55个包文件与wheel/源码相同。原八表逐字段、配置/UUID/凭据和AGENTS块外正文保持；生成入口刷新为任务级直接brief和retrieve宿主协议。全套623通过、1跳过，专用CLI变量补齐后的反馈恢复文件另8项通过；真实阵列固定副本的11表恢复、精确知识版本及交付幂等通过。新客户端pip check和源码外实际查询通过，原证及取舍见[验收结果](../tasks/20261112-usage-rectification/acceptance-result.md)。

开发locked同步因网络与缓存缺基础torch wheel停止，临时环境复用机器既有匹配版本依赖；不是干净机器全extras安装证明。首轮沙箱ACL回归未得到预期PermissionError，正常用户单项及最终全套通过；沙箱脱离进程的临时server未跨调用存活，主验收改用有生命周期session的独立内存server。正式项目库和共享0.5服务未重启，其它项目未升级。

## 当前开发入口与临时目录

当前唯一 active 路线位于 `experiments/20261106-basepack/`；安装、构建与测试目标均为该实验工程，具体命令见 [路线 README](../../experiments/20261106-basepack/README.md)。从仓库根运行 pytest 时，显式指定实验的 pyproject、tests 和根 `tmp/<task>/pytest` 作为 basetemp。pytest 不保留持久缓存；构建 TEMP/TMP 和隔离验证环境也进入根 tmp。目录寿命见 [文档维护约定](../documentation.md)。

2026-11-09 先前布局迁移只改变开发维护位置；当时系统安装为 0.4.0。其后 R9 形成下节的 0.5.0 共享资源基线，此后在独立稳定环境安装客户端并运行项目局部数据库。历史快照按各自条件阅读。

选留证据现统一位于根 `artifacts/runs/`。前次临时材料整理的映射为 `artifacts/runs/tmp-reorganization-20261108/moves.json`，本次位置映射为 `artifacts/runs/20261109-project-layout/moves.json`；原始回执及下文历史路径保留当时含义，结合两轮映射回查长期副本，tmp 内容按可清除处理。

## 2026-11-12 0.11.0.dev1入口与派工升级

本项目独立环境`D:/AgentTools/envs/basepack-client-0.10/`保留路径，普通wheel升级0.11.0.dev1；有效Codex容量12（不含主agent）已采集并写入项目配置。最终安装52个包文件与源码/wheel逐字节一致，升级前后UUID、七表计数、meta、凭据及launcher摘要保持；入口自动刷新保留块外字节，随后定点更新本机版本说明。最终普通wheel相关226项通过，brief三条mandatory均fresh。实际单coord、检索、宿主层级及使用边界见[派工实施结果](../tasks/20261106-memory-system/dispatch-implementation-result.md)。所有自有owner已释放，没有执行数据库或共享模型重启，其它项目未升级。

## 2026-11-12 重启后的项目记忆库恢复

Windows `LastBootUpTime` 为北京时间 2026-11-12 01:48:16。故障时本项目 18080 无监听；现存 SurrealDB 进程实际属于 array reconstruct 项目、监听 18089。本项目沿用普通用户手动进程，没有开机启动，重启后须重新运行 `.basepack/memory/serve.ps1`。受限宿主中的上一轮 Hidden 启动只返回脚本 PID，两份日志为空，随后连接仍被拒；不能据 PID 认定数据库就绪，也没有证据将该次启动失败归因于旧事务冲突。

本轮在普通用户上下文以原 launcher 和原 store 隐藏启动，跨调用 `/ready` 返回 200，0.10.0.dev1 客户端 `memory brief` 成功，三条 mandatory 均 fresh；恢复时 owner 为 null。数据库保持运行，日志为 `.basepack/memory/logs/surreal.stdout.log` 与 `surreal.stderr.log`；未改变自启动策略。

## 2026-11-11 0.10.0.dev1维护改造与本项目接入

候选隔离验证后合回唯一active路线。本项目普通wheel安装在独立稳定环境`D:/AgentTools/envs/basepack-client-0.10/`，Python3.13.17、psutil7.2.2、websocket-client1.9.2；原共用客户端仍为0.9.1。本项目runtime.python和两份托管入口刷新，原UUID、三条fresh mandatory、刷新前后七表计数及块外字节通过；最终50个包文件与源码和安装逐字节相同。

完整候选源码482passed/5skipped；五个跳过项随后在active源码和独立数据库全部通过，使用真实共享embedding、原图向量、特殊ID、overflow和原生恢复。事务与反馈负测另有实际输出。旧HTTP413原批次在生产SurrealKV经新原生事务成功，3来源29成员，未调整服务配置或手工拆批。隔离负测采用SurrealDB4.0.0内存引擎，未覆盖自定义WS限额、全面磁盘负测和长期负载。一次owner.json替换WinError5的原占用者仍未知。

旧备份/可重建杂项按引用和逐文件证据清理；升级仅留一套当前回退材料。版本、最终wheel哈希、来源/动作、无审计策略对照的负面结果及实际记忆维护沿[实施结果](../tasks/20261106-memory-system/maintenance-implementation-result.md)与[原证索引](../../artifacts/runs/20261111-maintenance-implementation/README.md)核实，不把下文历史0.9.1位置当当前运行入口。

## 2026-11-11 0.9.1 一致性修复与旧依据兼容

稳定客户端 `D:/AgentTools/envs/basepack-client/Scripts/python.exe` 已普通 no-deps 升级为 0.9.1，Python 3.13.17。最终 wheel 位于 active 工程 `dist/consistency-0.9.1-final/`，SHA256 `1843a2df3630c094775b81d78ded799527230fce8365bc1e8d0d92629c39f3cc`；42 个包文件与源码、隔离普通安装及稳定安装逐字节相同。最终源码 432 passed/0 skipped，源码外普通 wheel 432 passed/0 skipped；独立认证库、共享图文 embedding、原生恢复和 Condor policy 检查均启用。初次临时 wheel 测试环境缺依赖的 11 失败及 K1 初版兼容负验原证均保留，不当作最终交付结果。

新 wheel 实际回读正式库 1128 个非退役记录所用独立 basis，全部成功；其中 58 项旧重绑定依据曾被初版过强门槛拒读，现已修复并保留原同源合同。普通升级前后七表全部记录逐表 digest 相同，UUID、三条 mandatory、397 pending 和 1274/1274 兼容向量保持；升级未维护知识或重启正式库/共享服务。新 NoProfile PowerShell 实际执行更新后的项目入口，brief 返回三条 mandatory 和 397 pending。此轮仅验本项目及共用安装，未重验其它项目功能。记忆维护在升级核验后另行执行，实际接受与余项见 [本轮进度](../archive/20261111-consistency-review/progress.md)，非秘密证据在 `artifacts/runs/20261111-consistency-review/`。

## 2026-11-11 0.9.0 worker prompt 与全项目默认

稳定客户端 `D:/AgentTools/envs/basepack-client/Scripts/python.exe` 已普通 no-deps 升级为 0.9.0；Python 3.13.17，从稳定 site-packages 导入。main 独立重算最终 wheel SHA256 `3bdb716795d09db9ca087904e38c920f18c9a2134555906b1e816d1725fd1d12`，42 个包文件与最终 wheel、源码一致，包含英文 coordinator/reader 模板。源码外最终普通 wheel 完整检查 395 passed、0 skipped，启用独立认证库、真实共享模型与本机 Condor policy 检查；此前初版与最终候选仅两份模板及 RECORD 不同，完整检查已对最终候选重跑。具体范围与真实多批验收见[本轮结果](../archive/20261111-memory-worker-prompts/result.md)。

升级前停止本轮后台维护，旧 0.8.1 wheel 保留。安装没有写知识表或重启服务；同一 UUID、七表计数、meta、三条 mandatory 内容、397 pending 和 1274/1274 兼容向量均与停写后的 baseline 相同。这是计数/入口及指定记录比较，不冒充七表逐字段迁移核验。本项目生成入口已刷新，Git 默认发现实际返回 287 个文件候选且无格式缺口，安装后的 prompt 默认 coordinator/tier2，英文与派工元数据实收通过；没有据此宣称这些文件已语义接受。

新 NoProfile PowerShell 按生成 memory 段执行 brief，实际返回 3 条 mandatory 与 397 pending。沙箱以 `-File` 执行临时 `.ps1` 曾被 AuthorizationManager 拒绝；保持原安全策略，改按生成入口本来要求的命令段用 `-Command` 实测。初次提取误选通用 config show 围栏，发现没有 mandatory 后改为只取 basepack-memory 标记内的 brief 围栏，并核实际内容通过。0.9.0 本轮只验本项目入口与共用安装，三个项目 0.8.1 认证升级的既有实证仍见下节。

Codex App Server 在受限沙箱初始化用户状态目录失败的问题仍存在；本轮经自动批准在正常用户上下文执行同一默认维护命令成功，未改 HOME 或范围、未静默降级。共享 embedding、数据库及 Condor 保持原实例。

## 2026-11-11 0.8.1 认证凭据与普通安装（历史）

稳定客户端 `D:/AgentTools/envs/basepack-client/Scripts/python.exe`（Python 3.13.17）已以普通 no-deps 安装升级到 0.8.1，从其 site-packages 导入。最终 wheel SHA256 为 `5b823201fcdef46f7f22db13af624da6d80cd6f23f9937d4f14a382f6b19917f`，38 份安装文件与最终 wheel、源码逐字节一致。源码外普通包完整回归为 369 passed、0 skipped；末次重包仅含同义 SKILL 文案与 RECORD 差异，Python 代码及测试未变，未为该措辞重复功能回归。

本项目、array reconstruct 与 ppt memsys 均保留原 UUID、账户和 store 目录；密码文件与 launcher 字节不变，数据库 PID 6232/33428/1236 及创建时间保持，未重启或迁库。七表全记录逐字段比较一致。三个项目分别在新的 NoProfile PowerShell、其它 cwd、清空 PASSWORD 环境变量的条件下直接运行生成入口 brief，均退出 0；read 与默认 vector 查询也实际通过。客户端自动读配置的唯一密码文件，旧 password_env 与手工桥已从配置、instructions 和自有包装清理。

三项目另补齐各自 Codex 宿主 ID 和 36 个其它注册项目根，仅更新配置，本次升级没有执行历史聊天采集或语义接受；数据库不变与检索成功不代表来源已全部维护。共享 embedding 与 Condor 沿原实例。普通包、外部手写入口、保留状态与恢复材料的证据入口见 [0.8.1 安装结果](../archive/20261110-onboarding-simplification/credential-installation-result.md)。下节及后续版本记录保留各自日期的历史条件。

## 2026-11-10 0.7.1 整改与安装

稳定客户端已普通升级为0.7.1，源码外完整CPU依赖的Python3.14.10环境全套266项通过、无跳过；轻客户端3.13/3.14与CPU/CUDA实际图文、索引复用的条件见[整改结果](../archive/20261110-rectification/result.md)。三个已接入项目保留UUID，兼容向量全部复用后切为vector，七表所有字段不变。生成凭据入口在无继承变量的新NoProfile PowerShell和其它cwd中实过。共享0.5.0模型服务、机器配置与Condor策略保持原实例。

## 当前资源查询与执行边界（2026-11-10）

0.6.3 发布准备已在独立轻量客户端、全新下载的 SurrealDB 和临时数据目录验证，源码 201 项通过、无跳过；新 shell 使用生成入口的实际结果与独立新机资源部署待验范围见 [发布结果](../tasks/20261106-rebuild/github-publish-result.md)。该次发布准备没有替换当时的正式环境；当前客户端安装状态见本页最新安装记录，资源查询的双上下文边界仍按本节实证。

最新双上下文复查仍为：受限 agent 沙箱中的 `condor_status` 成功、`condor_q -json` 以 `AUTHENTICATE:1005` 失败；相同配置在正常用户上下文两者均成功，队列为空。沙箱内 Windows NTSSPI 认证限制仍在，不能把正常用户路径验收通过写成该限制已修复，也不能由容量查询成功推断队列认证成功。对照原证为 `artifacts/runs/20261110-condor-auth-context/`。

正常用户路径已分别通过下述 CPU `14348.0` 和 GPU/embedding 并存 `14350.0` 的实际提交、执行、输出与回收验收。提交端使用正常用户安全上下文，作业执行端仍是 `condor-slot1_1`。日常认证诊断与实时资源核查按 [管理员说明](../../experiments/20261106-basepack/docs/administrator.md#安装与执行账户)；本机配置、服务和认证政策未因本次故障调整。旧 yadof 材料只提供宿主权限、拓扑与凭据排查经验，本次查阅未找到同款 SSPI 修复案例，不承接其可选认证策略。

## 2026-11-10 0.6.2 GPU 作业与共享 embedding 并存复核

正常用户上下文使用稳定 0.6.2 客户端提交 GPU 作业 `14350.0`，申请 1 CPU、2048 MiB RAM、1 个同卡 GPU 名额及 2048 MiB 显存。应用复用系统 Python 的 torch 2.10.0+cu128，以 `condor-slot1_1` 在 CUDA 上执行 256×256 全一矩阵乘法；30 轮计算后的全矩阵最大误差为 0，元素和为 16777216，结果文件回传，退出码 0。

startd 直接查询和队列/事件原证一致：运行时普通池剩 11 CPU/22528 MiB RAM/3 个 GPU 名额/5116 MiB 显存，动态 slot 分得申请的全部配额；结束后恢复 12/24576/4/7164，动态 slot 为 0，已知 worker/应用进程消失且 scratch 删除。作业前、中、后 embedding 分别处理 1/4/1 条文本，均返回有限、近单位范数的 2048 维向量，worker PID 2948 和语义身份不变。中间请求完整处于 GPU 作业运行区间，包含 7 个同步 CUDA matmul 区间；未观测服务内部 forward，不据此声称物理 kernel 同时执行或吞吐提升。本次不验最大负载、显存硬隔离、取消或超时。

首轮 `14349.0` 因验收脚本误把 Condor 短 UUID 与 CUDA 完整 UUID 作全等比较而提前结束，确认该作业回收后才提交成功轮；设备通过 UUID 前缀、原生事件完整 DeviceUuid 与 nvidia-smi 全 UUID 交叉核对。未改机器/Condor 配置或重启共享服务，相关配置 hash 前后一致。成功原证为 `artifacts/runs/20261110-condor-gpu-embedding-verified/verification.json`，首轮失败与回收记录为 `artifacts/runs/20261110-condor-gpu-embedding/first-attempt.json`。WDDM 的进程列表未枚举这些跨账户 CUDA 进程，不用它单独证明回收；回收结论来自已知 PID、原生终态、scratch 和直接 slot 查询。

## 2026-11-10 0.6.2 正常用户 CPU 作业复核

受限进程的 `condor_q` 出现 NTSSPI 握手失败；相同配置在正常用户上下文通过队列查询、WRITE 认证及 Condor doctor。随后从源码外工作目录，以稳定 0.6.2 客户端实际提交作业 `14348.0`，申请 1 CPU、512 MiB RAM、64 MiB scratch，不申请 GPU。输入脚本传入 Condor scratch，实际账户为 `condor-slot1_1`；平方和结果 `333328333350000` 经 `result.json` 回传，stdout、事件日志及原生 history 一致，退出码 0。

回收已核原生终态、该作业队列为空、worker/venv 启动器/实际应用三个 PID 消失及 scratch 删除；直接查询 startd 得到动态 slot 为 0，12 CPU/24576 MiB RAM/4 同卡名额/7164 MiB 普通显存池全部可用。运行中的 collector 快照未显示配额扣减，分配依据为原生事件中的 1 CPU/512 MiB；首次验收脚本误判 venv 进程层级，修正验证方法后复核同一已完成作业，没有重提。原脚本、补核脚本与回执选留在 `artifacts/runs/20261110-condor-normal-user-cpu/`，入口为 `verification.json`。本次只覆盖 CPU 成功路径和输入/输出传输，不新增 GPU 计算、取消或超时验收。

## 2026-11-10 0.6.2 项目模型等级配置与安装

稳定客户端 `D:/AgentTools/envs/basepack-client/Scripts/python.exe` 已普通安装 0.6.2 wheel；源码外以 `-I` 核安装位置与 `config show`、`config ai`，33 个包文件与 wheel 字节一致，wheel SHA256 为 `44658d1856e7a635c7f36a656fd06839422858e019af16d1872d7e5324b7aaec`。本项目配置已补入 AI 节。源码全套 137 passed、41 skipped（未提供一次性数据库的集成项）；配置和 activation 专项 41 passed。本次不重跑数据库全验收，历史 P0–P5 与 0.6.1 结果保持各自条件。安装核验回执选留 `artifacts/runs/20261110-ai-tiers/installed-verification.json`；配置与使用见 [项目接入](../../experiments/20261106-basepack/docs/setup-project.md#agent-模型等级)。

## 2026-11-10 0.6.1 修复与安装

特殊记录 ID 往返与最小输入诊断已在源码提交 `488e298` 实现，连同此前并发/初始化修复进入普通 0.6.1 wheel。源码与源码外普通安装分别 157 passed、0 skipped，均执行四项真实共享向量检查。wheel 为 `experiments/20261106-basepack/dist/memory-0.6.1/basepack-0.6.1-py3-none-any.whl`，54,761 B，SHA256 `2a1bc7e014e2a89697ced0970352cf9f724f287ebf3baa728a4edb4b4403efd2`。

稳定客户端 `D:/AgentTools/envs/basepack-client/Scripts/python.exe` 已普通升级到 0.6.1，导入来自其 site-packages，全部包文件与该 wheel 一致。此环境不含 pip，升级使用现有测试环境的 pip `--python` 显式指定目标；没有为客户端引入模型依赖。升级前保留旧 wheel 与项目原生恢复集合，升级后本仓库七表全记录逐字段未变，brief/search/read 通过。独立两项目与原生恢复验收、PPT业务实测结果从 [专项进度](../tasks/20261106-memory-system/progress.md) 接续，历史结果不并入本轮。

全套源码初次检查的八项失败来自测试环境缺少锁定 sentence-transformers 发行元数据，安装 6.2.0 的轻量测试包后全套通过；系统 torch/Pillow/pytest/psutil 作为既有测试依赖复用。受限宿主会回收 Hidden 后台进程，普通用户执行相同启动脚本后跨调用 ready/init/brief 与实际读写通过；该环境边界不由产品新建进程管理器处理。M4期间原共享服务停止后由用户以管理员恢复，服务实现与身份不变；两个正式库也按既有入口重开原store。短期存续不等于宿主重连后的长期驻留保证。回执选留 `artifacts/runs/20261110-memory-061/`。

## 2026-11-09 升级后一致性修复（源码）

P5 安装基线之后，仓库修复了失效知识版本、关系依赖并发核查、错项目初始化的 schema 副作用，以及项目入口生成的路径/标记问题，见 [修复记录](../change_log/minor/20261109_170434_reconcile-memory-contracts.md)。本轮修复只在源码与隔离测试中交付，未重建 wheel 或重装稳定客户端；下节仍描述此前的普通安装版本，共享资源服务保持原状。

## 2026-11-09 记忆与 0.6.0 部署核验

0.6.0 普通 wheel 已安装于 `D:/AgentTools/envs/basepack-client/`，仅含轻量客户端及 psutil 7.2.2；非 editable，无 user-site overlay。系统 Python 的原安装及 embedding 0.5.0 环境未改。本项目已由该解释器执行 init 和 memory init，跨调用 brief 成功；实际 devDoc 首建与完整试用结果统一见 [记忆进度](../tasks/20261106-memory-system/progress.md)。

稳定 SurrealDB 4.0.0 程序位于 `D:/AgentTools/bin/surrealdb-4.0.0/surreal.exe`。本项目 `.basepack/memory/serve.ps1` 读取同目录 password.txt 后设置原生凭据环境，以普通用户隐藏手动进程启动 `surrealkv://store`，监听 loopback 18080，数据保留在本项目并供多聊天共用。SCM 管理员安装未执行，本轮不以创建服务为完成前提；脚本、秘密文件与库均被 Git 忽略。启动 source_scope 声明项目纲领、文档维护约定及记忆计划三个文件，不代表整个 devDoc 已有语义覆盖。

共享 embedding 继续沿用 R9 的 0.5.0 服务、8765 endpoint 和原有语义身份，0.6.0 客户端保持 HTTP 合同兼容，实际健康与身份保持不变，本轮未重启共享模型。开发真实回归已覆盖跨层文字/图像编码、身份及输入版本排除、原生恢复和从保留表示重建向量；源码证据与正式安装分别验收。

## 2026-11-10 产品文档移出的历史环境事实

整改前管理员文档记录 Python 3.13.17、uv 0.13.7、驱动 617.42、RTX 4060 Ti 16380 MiB；这些是当时机器观测。LitServe 0.2.19 原生 `/shutdown` 在 Windows 小试曾残留进程，因此沿 R9 用 Shawl/SCM 停止服务树。原位置与版本依据见[文档整改结果](../archive/20261110-rectification/docs-result.md#环境证据交接)，能力条件在产品管理员说明维护。

## 2026-11-09 R9 共享资源基线

系统 Python `C:/Program Files/Python313/python.exe` 普通安装 basepack 0.5.0 core/jobs；服务 wheel 普通安装于 `C:/ProgramData/basepack/envs/service/`，依赖由 uv.lock 与 cu128 源准备，不继承系统 site-packages。共享模型保持原 D 盘 revision，17 个 manifest 文件的字节及 SHA256 已核实。Shawl 1.9.0 位于 `D:/AgentTools/bin/shawl-1.9.0/shawl.exe`，SCM BasepackEmbedding 采用 LocalSystem/Manual，日志在 `D:/AgentTools/state/basepack/embedding/logs/`。

源码与源码外安装回归各 68 项通过；真实两项目图文、CPU/GPU 计算重叠、超时隔离、作业取消、正式服务故障与显存回收、0.5→0.4→0.5 回退均通过。当前服务已恢复运行，Condor 60/70 策略与原项目文件未变。完整条件和原证见 [R9 结果](../archive/20261107-resource-coordination/r9-result.md)。下面 R8 及同日布局迁移段落保留当时快照，不作为当前安装版本。

## 2026-11-08 R8 部署核验

系统 Python `C:/Program Files/Python313/python.exe` 已普通安装 basepack 0.4.0，包根为 `C:/Program Files/Python313/Lib/site-packages/basepack`。30 份代码/模板/许可与 wheel 及源码一致，旧源码入口不存在；源码和源码外安装回归各 92 项通过。六份旧配置已显式迁移，源码外两项目、深层中文/空格配置、项目移动及新检出初始化已核验。

真实作业 14335–14338 核得 CPU 结果 499500、应用退出 7、GPU 矩阵结果 256，以及图文向量、GPU/embedding 并存、请求/作业取消、日志和资源归还。机器 schema 1、模型、共享状态位置及 Condor 60/70 策略保持原合同；容量仍为 12 CPU/24576 MiB RAM、4 个同卡名额、7164 MiB 普通池及 9216 MiB 背景预留。本段记录本轮已取得的环境证据，最终生命周期和交付状态只维护在 [资源进度](../archive/20261107-resource-coordination/progress.md)。原始回执为 `artifacts/r8/installed-files.json`、`installation-receipt.json` 和 `runtime-receipt.json`。

本次 pytest 使用仓库内忽略目录作为 `--basetemp`；wheel 构建将 TEMP/TMP 置于该目录，避免受限 Windows 临时目录 ACL。真实 Condor 查询与作业使用正常用户认证上下文，保留受限进程 SSPI 失败的原始信息；不改认证策略。

## 较早环境快照

以下保留各次观测的当时条件，旧 PID、队列与版本不作为当前操作依据。

2026-11-08 R7 历史状态：系统 Python 普通安装basepack0.3.0，22份代码/模板/许可与源码及wheel一致；源码与源码外安装回归均22项通过。通用60配置容量保持12CPU/24576MiB、4个同卡令牌、7164MiB显存池与9216MiB背景预留；新增70配置由schedd原生转换官方GPU字段，拒绝非法申报并保留原筛选。原生14319–14331与普通客户端14332–14334、最大embedding联合验收通过，均已清理，队列为空且资源归还。作业树外broker43200无模型驻留，测试worker21732已退出。详见 [R7回执](../archive/20261107-resource-coordination/standard-submit-result.md) 与 `artifacts/standard-submit/final-state.json`。

2026-11-08 R6 历史状态：系统 Python 已普通安装 basepack0.2.0，22份代码/模板/许可与源码、wheel逐字节一致，14项普通wheel回归通过。通用 `C:/condor/config/60_resources.conf` 直接维护12CPU/24576MiB、4个同卡GPU名额与7164MiB普通显存，背景总预留9216MiB；旧专属片段与TOML普通预算已移出。原生显存队列、四作业CUDA进展及第5项排队、普通客户端与最大embedding共存全部通过，本轮14299–14311已释放，节点资源全部恢复。独立交互用户broker8060无模型驻留；机器重启后仍按管理员说明启动。证据见 [通用节点结果](../archive/20261107-resource-coordination/native-condor.md) 与 `artifacts/native-condor/final-state.json`。下文保留各历史批次的当时条件。

2026-11-08 R5历史状态：系统Python当时保留basepack0.1.0普通wheel安装，实际位置 `C:/Program Files/Python313/Lib/site-packages/basepack`；22份代码/模板/许可与源码及wheel逐字节一致。源码外两个项目、移动项目、新检出、图文embedding与GPU14295真实并行全部通过，11项普通wheel回归通过。机器级交互用户broker26696从AgentTools工作目录后台启动，当时无模型驻留；测试作业/模型已释放，队列为空。`artifacts/r5/wheel-receipt.json`、`deployed-state.json`保留该批交付回执。

2026-11-08 R0：系统 Python 3.13.17 已安装 basepack。普通用户 pip 会回落用户站点，现经管理员安装到系统 site-packages，`python -s` 可加载。editable 引用本仓库 `src/`，新进程观察到临时代码修改；普通 wheel 安装到系统 site-packages 后，从源码目录外初始化两个项目并调用 config show/doctor，通过后恢复 editable。最小安装原始回执位于 `artifacts/r0/*-receipt.json`，管理员安装日志同目录。

当时 pytest 使用 `--basetemp artifacts/<batch>/pytest`，避免受限 Windows 临时目录 ACL。Condor 的 SSPI 查询在受限进程中会失败，同一显式配置命令在正常用户上下文通过；后续真实 Condor 验证用正常上下文，具体功能结果记录在资源任务。

2026-11-08 R0–R4：复用 torch2.10.0+cu128、torchvision0.25.0+cu128、transformers5.22.1、qwen-vl-utils0.0.14、既有VL2B权重与Condor25.4.0。实际slot账户condor-slot1_1可加载系统包、访问权重/项目并连接作业外broker；普通任务不继承提交环境，保留Condor设备UUID。机器配置 `D:/AgentTools/basepack.toml` 派生 `C:/condor/config/60_basepack.conf`，执行端现为12CPU/24576MiB、单GPU普通预算5116MiB，hash5dd7fc9014b383e0。NUM_CPUS/MEMORY变更仅reconfig不足，实测peaceful重启startd才更新既有父slot。测量与功能证据见资源进度。

观测时间：2026-11-06 23:34:19（北京时间，UTC 15:34:19）。这是当前开发进程的一次只读快照；仓库尚无依赖声明，最低兼容版本尚未确定。

## 实测入口与结果

| 对象 | 本次观察 |
| --- | --- |
| Shell / 系统 | PowerShell Core 7.6.9；系统报告 `Microsoft Windows 10.0.26300` |
| Python | `C:\Program Files\Python313\python.exe`，3.13.17，64-bit；本次使用系统解释器，`sys.prefix == sys.base_prefix` |
| Python Launcher | `py --list-paths` 仅列出上述 Python 3.13 |
| 仓库状态 | 无 `src/`、`pyproject.toml`、`tests/`、`.venv/`、`venv/`、`.memory/` |
| 共享资产 | `D:\AgentTools` 可见 `models/`、`profile/`、`state/` |
| HTCondor | CLI 位于 `C:\condor\bin`；`condor_version` 成功，版本 25.4.0 |
| 状态与队列 | `condor_status -json`、`condor_q -json` 均退出 1：当前进程的 `CONDOR_CONFIG` 环境变量及注册表未提供配置源 |
| GPU 元数据 | `nvidia-smi --query-gpu=name,memory.total --format=csv,noheader` 返回 RTX 4060 Ti、16380 MiB |

本次 Condor 查询尚未进入认证阶段；与 [早期调查](../archive/20261107-resource-coordination/research/infrastructure.md#agenttools-当前可复用部分) 的 `AUTHENTICATE:1005` 是不同观测，不能据此判定调度服务是否可用。

2026-11-07 资源协调计划期间定向只读复核：当前进程、用户和机器环境变量中的 `CONDOR_CONFIG` 均为空，但 `HKLM:\SOFTWARE\Condor` 的同名值已为 `C:\condor\condor_config`，该文件与 `.local` 均存在。上表是 11 月 6 日快照；本次未重跑 Condor 查询，注册表入口可见不代表当前认证、队列或 GPU 作业已通。后续按 [资源专项 R0](../archive/20261107-resource-coordination/plan.md#r0-复用准备与预算标定) 实测。

## 可见模型版本标识

以下仅核对目录名称，未校验权重内容或加载模型：

| 模型 | revision 目录名 |
| --- | --- |
| `BAAI/bge-reranker-v2-m3-int8` | `6f5ff65298512715a1e669753bc754d2bc8f367b` |
| `intfloat/multilingual-e5-large` | `ac6781cd1cf88b8306a536d7c9d18a5bd57cc14b` |
| `Qwen/Qwen3-Embedding-4B` | `5cf2132abc99cad020ac570b19d031efec650f2b` |
| `Qwen/Qwen3-VL-Embedding-2B` | `9f2f7e710d6d81056aa5c0a4f04764fec6bb7bda` |
| `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | `faf4aa4225822f3bc6376869cb1164e8e3feedd0` |

## 核验方法与限制

使用目录存在性检查、`Get-Command`、Python 标准库读取解释器信息，并对三条 Condor 命令、GPU 元数据查询及 Launcher 列表各执行一次只读查询；外部查询设 8 秒超时，均提前返回。未安装依赖、设置环境变量、加载模型、修改服务或提交计算任务。

模型可加载性、GPU 推理、实际队列和资源准入、项目安装及产品测试尚未验证。下一阶段由资源专项 R0 核配置来源，分别验证 embedding 与 Condor 接入，再按各链结果推进；公共代码通过配置定位共享资产，本页机器路径仅记录观测。

2026-11-07 安装布局规划期间只读检查：当前系统 Python 的 sysconfig purelib 为 `C:\Program Files\Python313\Lib\site-packages`；find_spec 可定位 basic_memory，未发现 basepack/context_memory。旧安装器仍复制 `.context-memory/app`，详细依据与新部署目标见 [路径布局计划](deployment.md#升级与回退)。本次未安装包、写入 AgentTools 配置或运行模型。

## 项目 skill 的本机入口

以下技能使用根 `.agents/skills/` 的项目级发现入口，junction 指向唯一维护源。2026-11-09 将 resources 的目标切至 active 实验内，其余两项保持根维护源。2026-11-10 新增 engineering-judgment 联接，按用户要求保留，不运行技能测试。新检出时按下例建立联接；历史发现回执保留当时作用域和名称。[Codex 官方作用域说明](https://learn.chatgpt.com/docs/build-skills#where-codex-loads-local-skills) 区分项目级与用户级入口。

| Skill | 维护源 | 本机发现入口 |
| --- | --- | --- |
| `file-structure` | [SKILL.md](../../skills/file-structure/SKILL.md) | `.agents/skills/file-structure` |
| `agent-team` | [SKILL.md](../../skills/agent-team/SKILL.md) | `.agents/skills/agent-team` |
| `engineering-judgment` | [SKILL.md](../../skills/engineering-judgment/SKILL.md) | `.agents/skills/engineering-judgment` |
| `resources` | [SKILL.md](../../experiments/20261106-basepack/skills/resources/SKILL.md) | `.agents/skills/resources` |

本机联接由 `.gitignore` 排除，不重复保存源码。仓库换路径或新检出时，如需在技能列表中自动发现，可从仓库根目录首次建立项目级入口：

```powershell
New-Item -ItemType Directory -Force -Path '.agents/skills' | Out-Null
$skillSources = @{
    'file-structure' = 'skills/file-structure'
    'agent-team' = 'skills/agent-team'
    'engineering-judgment' = 'skills/engineering-judgment'
    'resources' = 'experiments/20261106-basepack/skills/resources'
}
foreach ($entry in $skillSources.GetEnumerator()) {
    $skillSource = (Resolve-Path -LiteralPath $entry.Value).Path
    New-Item -ItemType Junction -Path ".agents/skills/$($entry.Key)" -Target $skillSource | Out-Null
}
```

AGENTS.md 仍直接引用仓库维护源；skill 本身不依赖本机绝对路径，也不需要安装 Python 包或加载模型。

改名前，`project-layouts` 作用域调整时四份源码 SHA-256 保持不变，原始发现结果留在忽略目录 `artifacts/project-layouts-scope/`。英文版与 `agent-team` 注册后，实际 `skills/list` 在项目根目录及 `devDoc` 子目录均返回两个 skill 的 `scope=repo`、`enabled=true` 和英文元数据；项目外用户目录均未发现，三处均无发现错误。原始结果记录在 `artifacts/skills-english/`，保留当时的名称与元数据。

2026-11-07 改名复核：`skills/list` 强制刷新后，在项目根目录及 `devDoc` 子目录发现 `file-structure`，显示名为 `File Structure`，`scope=repo`、`enabled=true`；旧名 `project-layouts` 均未发现。`agent-team` 仍正常发现，项目外用户目录未发现这两个技能或旧名，三处均无发现错误。最新回执见本机忽略目录 `artifacts/file-structure-rename/`。
