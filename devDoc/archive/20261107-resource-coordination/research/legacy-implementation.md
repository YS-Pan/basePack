# 旧资源与 embedding 实现核对

2026 年 11 月 7 日。按用户要求先读旧项目 Codex 聊天，再依线索读相关代码、测试与历史回执。用户本次明确 embedding 和其他 GPU 任务独立、可以并行；这取代先前计划中的 Condor 模型作业和整卡轮流。实施维护源为 [资源协调计划](../plan.md)。本次仅阅读，未运行测试、加载模型、提交任务或改旧项目。

## 聊天覆盖与用户意图

| 聊天 | 实际覆盖 | 与本任务有关的结论 |
| --- | --- | --- |
| [查找 context 目录超大原因](codex://threads/01a19f83-a7a4-77e1-b2ab-17893574b078) | 5 页、26 个 turn，至 hasMore=false；各 turn 用户消息与 final，过程按主题选读 | 已部署共享模型与系统 Python；用户接受粗估和自行限制，不要求 OS 精确强制；HTCondor 已安装，当时只做轻量探针 |
| [规划记忆系统升级](codex://threads/01a1a93d-5208-7503-95ac-4c520b917e2b) | 2 页、12 个 turn，至 hasMore=false；用户/最终答复及相关过程 | 后继改用统一 VL 2B，图片和文本进入同一向量空间，批处理和模型复用已有明确建设线索 |
| [执行Context存储与多模态升级](codex://threads/01a1a975-2747-72b2-8a00-0a64af80e865) | 1 页、1 个 turn，至 hasMore=false；用户/最终答复及 embedding 相关过程，未逐项审阅 2252 个 items | 声称完成 0.7.7 工程交付，需要按实际代码区分模型推理、同项目复用与尚无的跨项目公共服务 |
| [执行综合精简计划与建图专项](codex://threads/01a1ab10-3aba-7532-acd7-b0bf371ee184) | 2 页、2 个 interrupted turn，至 hasMore=false；用户信息、GPU 相关消息与命令筛选 | 后续仍有真实 CUDA 使用和释放记录，但主要建设是语义/文件整理，不据此推定统一资源平台已完成 |

共返回 41 个顶层 turn；不是逐项审计全部工具输出。超长返回在工具编排内先筛用户/最终答复和 GPU/embedding 相关项，再按线索读源码，未将聊天摘要当作代码完成证明。

基础设施聊天的关键定位均为北京时间 11 月 4 日：turn `01a1a464-1fe5-7030-8f0f-85b9d32d5060`（10:29）要求集中入口，并明确“先不实施”；`01a1a470…`（10:43）接受宽松预算；`01a1a473…`（10:46）要求考虑已安装 Condor；`01a1a47d-b449-7131-afd5-b748ae00f857`（10:57）授权当时的轻量提交。旧助手提出的“一个 GPU 任务独占”不是这些用户消息的永久要求。

## 代码复用清单

下表源码和测试均位于旧实验 `D:/project/20261024 doc system/20261102 context/`，作为提取依据，不作为新工具安装后的运行依赖。

| 已有能力 | 代码与实际行为 | 提取或改造边界 |
| --- | --- | --- |
| 本地多模态推理 | [vl_worker.py](<D:/project/20261024 doc system/20261102 context/src/context_memory/vl_worker.py>) 20–90：固定本地权重、GPU/eval、归一化与运行回执；[vl_preprocessing.py](<D:/project/20261024 doc system/20261102 context/src/context_memory/vl_preprocessing.py>) 6–26：真实输入预处理与 token 边界 | 提取 runtime/预处理；[vl_contract.py](<D:/project/20261024 doc system/20261102 context/src/context_memory/vl_contract.py>) 的型号、Windows 依赖和旧发布身份改为后端配置 |
| 文本/图片与批处理 | vl_worker 93–174 支持原图/图文输入，纯文字 batch 至多 4，图片逐项；[vl_bridge.py](<D:/project/20261024 doc system/20261102 context/src/context_memory/vl_bridge.py>) 63–93 每次传最多 8 项 | 保留批次与输入上限的语义，不把已有内部批处理称作跨请求动态合批；旧 assets/catalog 管线不整搬 |
| loopback 传输和热复用 | [vl_service.py](<D:/project/20261024 doc system/20261102 context/src/context_memory/vl_service.py>) 30–45、48–123：JSON transport、endpoint 注册、同项目加载复用；24–25 固定空闲 30 秒、寿命 1800 秒 | key 含 execution_home，endpoint 也在项目内；改机器级注册和模型实例键，保留创建锁 |
| 请求串行与错误回传 | vl_service 149–190 逐连接执行，错误有类型、原始消息与 traceback | 可作为单实例顺序服务起点；尚无逐请求取消、公平队列或跨请求合批 |
| owned 进程与超时清理 | [qwen_bridge.py](<D:/project/20261024 doc system/20261102 context/src/context_memory/qwen_bridge.py>) 25–63、131–229：Windows Job Object、JSONL、stderr、超时回收；vl_service 135–145 有请求/总寿命 watchdog | 提取进程所有权与传输；共享服务客户端取消不能沿用“关闭整个 owned worker”语义 |
| 查询侧服务接入 | [native.py](<D:/project/20261024 doc system/20261102 context/src/context_memory/native.py>) 264–276 默认走 VLProvider 复用 | 可提取薄客户端；旧 release/owner/attempt 绑定只保留新接口实际需要的部分 |
| 建库侧模型接入 | [bm_bootstrap.py](<D:/project/20261024 doc system/20261102 context/src/context_memory/bm_bootstrap.py>) 17–28 显式 reuse=False | 建库仍另起 owned worker，须改成建库/查询共用服务；已有实现不等于同模型所有请求已统一 |
| 模型与环境定位 | vl_contract 98 附近绑定系统 Python、共享权重和声明 | 优先复用既有环境和权重，不重装全部依赖；公共源码中移除机器固定路径与旧状态前提 |
| Condor 提交 | [probe-python.sub](<D:/project/20261024 doc system/temp/20261104-htcondor-smoke-105829/probe-python.sub>) 已含 executable、参数、初始目录、CPU/RAM/disk、日志和 periodic_remove | 提取原生 submit 模板；尚无通用 submit/status/wait/cancel/run 封装或真实 GPU 联合验收 |

## 与并行要求冲突的旧策略

1. qwen_bridge 66–128 是全卡 OS 字节互斥锁；vl_service 176 加载前取锁，194–195 清 runtime 后释放。对旧协议能覆盖驻留显存，但会阻止遵守同锁的普通任务与 embedding 并行。模型实例锁与跨机制整卡锁必须分开；vl_contract 58 附近的强制锁合同也要一起修改。
2. [qwen_worker.py](<D:/project/20261024 doc system/20261102 context/src/context_memory/qwen_worker.py>) 23–25 定义启动 free 13 GiB、自身 allocator 上限 12 GiB、整卡保留 3 GiB；vl_worker 17、39、49、50、89 直接继承。这不是 VL 2B 与其他任务并行时的预算，应改成允许输入/批次下的 embedding 自身峰值预算。
3. qwen_bridge 255 强制 CUDA_VISIBLE_DEVICES=0，qwen_worker 29 监测物理 GPU 0；提取时明确设备配置及物理/进程逻辑编号，不覆盖 Condor 给普通任务分配的设备。
4. vl_service 114–117 的 force close 向整个服务发送 shutdown，且排在当前请求之后；它不等于取消单个共享请求。async to_thread 的客户端取消也未接到服务端。
5. 本次计划重评补核：vl_service 135–144 的 watchdog 在单请求超过 600 秒或总寿命到期时调用 os._exit(3)；若原样提取为跨项目服务，会结束其他项目共用的实例，R1 必须将请求截止与服务寿命分开。89–93 直接从客户端 spawn 模型进程，也不能原样用于 Condor 作业内的共享服务冷启动。

## 已有验证与不能替代的验收

- [真实 VL 图文回执](<D:/project/20261024 doc system/20261102 context/evidence/storage-upgrade/vl/real-gpu-receipt.json>)：合成 fixture、非质量评测，27 附近标明范围；加载 reserved 为 4,257,218,560 B，短图文峰 reserved 为 4,376,756,224 B（约 4.08 GiB），并记录正常退出释放。它不是最长输入、最大批次或与重任务并存时的峰值。
- 真实查询 [text-to-text-VL.json](<D:/project/20261024 doc system/20261102 context/evidence/storage-upgrade/root-installed/acceptance/text-to-text-VL.json>) 279 与 [text-to-image-VL-controlled-adopted-scope.json](<D:/project/20261024 doc system/20261102 context/evidence/storage-upgrade/root-installed/acceptance/text-to-image-VL-controlled-adopted-scope.json>) 454–457 均记录 PID 42812，支持同项目顺序热复用；不证明跨项目单实例。
- [test_vl_contract.py](<D:/project/20261024 doc system/20261102 context/tests/test_vl_contract.py>) 225、253 使用 FakeRuntime 测同 home 的同 PID/跨 CLI 复用与释放；[test_vl_batching.py](<D:/project/20261024 doc system/20261102 context/tests/test_vl_batching.py>) 及 [test_vl_native_mock.py](<D:/project/20261024 doc system/20261102 context/tests/test_vl_native_mock.py>) 是可提取的回归依据。本次没有重新运行它们。
- [旧 Qwen 工程验收](<D:/project/20261024 doc system/20261102 context/evidence/system-python-migration/qwen-engineering-acceptance-2.json>) 421–454 测跨项目进程约 0.35 秒后取得锁，但 gpu_model_loaded=false；证明锁等待，不能称双 GPU 负载并行。
- [Condor 核验](<D:/project/20261024 doc system/temp/20261104-htcondor-smoke-105829/verification.json>) 30–49：CPU job 以 condor-slot1_1 运行，能用系统 Python、列模型目录和写产物，尚未实际打开权重或使用 GPU；24–28 的另一个 PowerShell job 调度退出 0 却无应用产物。

## 并行设计的技术依据

建议独立服务固定预留 embedding 峰值 E 和系统余量 S，Condor 普通任务使用 T-E-S 的预算；同一张卡上先只让一个普通 GPU 作业运行，无须再建显存可消耗资源或动态锁队列。预算和单实例范围仍需新实现验证。

Condor 可发布自定义 slot 属性并用于 requirements，request_gpus=1 用于其池内普通任务之间的设备分配；设备总显存门槛不能充当剩余预算。[自定义属性配方](https://htcondor.readthedocs.io/en/25.0/faq/admins/slot-attrs.html)、[GPU 资源声明](https://htcondor.readthedocs.io/en/25.0/man-pages/condor_submit.html)

NVIDIA DEFAULT 模式允许多进程使用同卡；本方案不要求 MPS。Windows 下仍须实测设备模式、服务会话、路径权限与两工作负载并存；不把声明预算当硬隔离或保证 kernel 同时执行。[NVIDIA 计算模式](https://docs.nvidia.com/deploy/mps/when-to-use-mps.html)、[Condor 作业环境](https://htcondor.readthedocs.io/en/25.0/users-manual/env-of-job.html)

本次另核官方文档：Windows Condor 默认以专用低权限账户执行，并回收作业派生进程；作业默认不继承提交环境，分配后的 CUDA_VISIBLE_DEVICES 也应保留。由此要求 R0 验证账户、文件和 endpoint 访问，并让共享服务由作业树之外的入口启动；这是新方案的实施约束，不是当前机器已通过的结论。[Windows 说明](https://htcondor.readthedocs.io/en/25.0/platform-specific/microsoft-windows.html)、[作业环境](https://htcondor.readthedocs.io/en/25.0/users-manual/env-of-job.html)

当前新缺口收敛为：机器级服务作用域、建库统一接入、独立两机制的预算、普通任务薄入口、共享取消和真实并行验收。先按复用清单提取，保留这几项必要回归，不复制旧平台的业务授权、协议层和整套发布/审计树。
