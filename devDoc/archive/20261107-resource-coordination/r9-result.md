# R9 实施结果

更新：2026 年 11 月 9 日（北京时间）。本文记录实际实施证据；阶段状态以 [进度](progress.md) 为准，目标与完成条件见 [R9 计划](plan.md#r9-复用优先的资源实现)。

## 模型小试与源码整合

Sentence Transformers 6.2.0 在断网模式复用现有 Qwen3-VL-Embedding-2B revision `9f2f7e710d6d81056aa5c0a4f04764fec6bb7bda`，没有下载或复制第二份权重。7 条文本、图片和图文资料均得到有效 2048 维向量，4 个查询的完整排序与旧实现一致；对应向量余弦最低 0.99997679，最大相似度差约 0.00073174。这是小资料集的数值与排序比较，不代表所有索引都可直接混用。

采用原生 FP16 lasttoken pooling/normalize，范数略有变化，新的 `embedding_identity` 为 `Qwen3-VL:4e32ece7973113a13abd40dcbe5e5e4c8592f172f75535dc087f74f5269bba9e`。身份纳入实际 ST 版本、模型 manifest、指令与像素合同；运行路径、队列期限和批次不影响语义身份。记忆 P2 使用这个公开身份判断索引兼容。

显式关闭截断，torch 模块 prehook 在实际 tokens 3021 超过 2048 时拒绝调用模型 forward。ST 负责模型、聊天模板、图像预处理、pooling 和归一化；含图请求维持批次 1，纯文本按机器配置分批。已核图像 `size` 参数与弃用的 min/max 参数产生逐位相同的预处理张量。新路径该小试峰值 allocated 约 4118 MiB、reserved 4134 MiB；不作为最大输入预算证明。原证与脚本选留于根 `artifacts/runs/r9/model/`。

源码已替换旧 embedding 模型子类、HTTP/队列、supervisor、双端点登记和进程所有权代码，公开客户端只调用 LitServe `/predict`。退役取消、tokens_only、逐请求回执和文件代码指纹。`psutil` 替代 Toolhelp；真实验收暴露的观察范围问题及修复见下节。

R8 记录的六份迁移配置及新增三份配置现均为项目 schema 2，旧有效配置入口不存在。0.5.0 仅直接支持现有 0.4.0 项目；删除一次性 `migrate` 与自写 TOML writer，因此无需新增 Tomli-W。更老项目先用保留的 0.4.0 wheel 显式迁移。核查未覆盖任意其他盘或嵌套项目，不声称没有未知外部调用方。

初次源码与普通安装回归各 66 项通过；实际作业暴露回收观察问题后新增回归，修正后的源码 68 项通过。覆盖真实本地 HTTP 请求/原生错误/超时不重投、拒截断、图片检查、语义身份、项目配置及 jobs 状态/参数/进程处理。正式安装与真实 GPU 验收另记下节，不以回归数量替代功能结果。

### 实际部署与验收暴露的问题

独立依赖环境初放 D 盘时，Transformers 逐文件读取源码构造导入结构造成长时间启动等待，faulthandler 定位到 `create_import_structure_from_path`。保持原生依赖和模型不变，将正式服务环境准备到 `C:/ProgramData/basepack/envs/service/`，模型仍在原 D 盘位置。C 盘环境 ST 导入实测约 6.7 秒，正式服务随后完成加载；环境不继承系统包，未安装 MCP、FastMCP、accelerate 或 qwen-vl-utils。

第一次真实 CPU 作业 14339.0 正常算出 499500、退出 0，但回收确认卡在全系统逐进程 `ppid()`。Windows psutil 的该方法每次重新取得全局父 PID 表，逐项调用重复快照形成平方成本；先前较小样本的 4–6 秒和缓存后 0.015 秒不足以验收。该轮被明确记为失败，没有以作业完成代替客户端流程通过。

修复后回收确认只对本作业已知 PID 调用 `pid_exists`；撤销活动作业时只对已知根调用公开 `children(recursive=True)`，由 Condor 负责终止进程树。删除全局父表和独立 `_processes` 模块，保留原始观察错误及进程已退出的明确处理。新增回归覆盖无关进程属性不可读与根退出竞态，正常用户自建子树测试约 1.33 秒通过；真实作业按新实现重新验收。

部署时按原 model.lock.json 对 17 个文件、4,271,067,156 字节逐一核对大小及 SHA256，全部匹配；结果见 `artifacts/runs/r9/model/deployment-weight-check.json`。这项内容核验只在本次部署执行，运行请求不重复扫描权重。

## 服务与 Windows 托管小试

LitServe 0.2.19＋Shawl 1.9.0 的 CPU 小试已通过下述功能与托管检查，可以进入真实模型验证。本节没有验收真实模型显存回收、普通 GPU 作业并存、源码外业务项目接入或正式安装切换。

### 版本、接口与环境

核对官方最新发行版后选用 LitServe 0.2.19、Shawl 1.9.0；Shawl win64 可执行文件 SHA256 为 `0985555b71e7f943b8f3fc639952a9890aa62e66617942a2d0996985fe8e7c6d`。官方来源、取得时间和源码快照保存在 [服务小试原证](../../../artifacts/runs/r9/service) 的 `source-receipt.json` 及相邻文件。

- 使用薄 `LitAPI(max_batch_size=1)`，单设备、`workers_per_device=1`、`num_api_servers=1`。本轮只以 CPU 假模型运行；一个推理 worker 之外仍有 Manager、主进程和 Windows API 线程。
- 使用框架原生 `POST /predict`、`GET /health`、`GET /info`；`model_metadata` 通过 `/info` 返回，身份和版本诊断无需新增端点。原生认证使用 `LIT_SERVER_API_KEY` 与 `X-API-Key`。
- 服务小试环境位于根 `tmp/r9-env/`，采用系统包可见的临时环境。系统已有 fastmcp 与 MCP 2.3.0，触发 LitServe 可选 MCP 导入后因旧 `mcp.server.fastmcp` 接口不存在而失败，原错保存在 `functional-mcp2-error.log`。临时环境叠加 MCP 1.30.0 后完成验证，系统包未改变。正式交付应使用独立共享环境且不安装无关的 fastmcp/MCP，不把这个小试兼容处理变成产品依赖。

### 请求与 worker 行为

正常用户上下文运行 CPU 假模型，实际结果见 `dummy-receipt.json` 和 `functional.log`：

| 场景 | 实际结果 |
| --- | --- |
| 正常请求与原生诊断 | 输入 3 返回 6，`/info` 返回单设备、单 worker、队列期限与模型元数据 |
| 队列期限 0.5 秒，已有推理占用 2 秒 | 排队请求在出队时返回 HTTP 504，实等约 1.81 秒；已开始的推理完成后返回 HTTP 200 |
| 客户端 0.1 秒观察超时 | 客户端得到 ReadTimeout；等待当前推理完成后，另一请求正常返回 HTTP 200 |
| 推理 worker 主动异常退出 | 在途请求约 1.86 秒后返回 HTTP 500；`restart_workers=True` 创建新 PID，后续输入 6 返回 12，失败请求未重做 |

排队期限不是 HTTP 响应时限，也不停止已经开始的推理。调用方仍需自己的有限等待；超时不停止共享服务，也不代表 GPU 计算已经取消。worker 重建使用框架原生监控，服务主进程和 Shawl 的恢复策略另行配置。

### 原生停机缺陷与托管选择

本机复现了 [Windows 停机问题 #684](https://github.com/Lightning-AI/LitServe/issues/684)：原生 `/shutdown` 已返回 HTTP 200，8 秒后仍有 Python 主进程存活；日志包含 `'Thread' object has no attribute 'terminate'`，随后 worker 监控记录 BrokenPipeError。普通启动进程被强杀也留下子进程。这组结果说明该 Windows 服务需要外部进程树所有者；不以 HTTP 停机成功代替进程回收验收。普通探针的崩溃操作针对 venv 启动进程，实际 LitServe 主进程另在下述 SCM 小试中直接强杀。

采用 Shawl 原生 `--kill-process-tree --no-restart --stop-timeout 3000`，由 Windows SCM 托管。Shawl 使用 Job Object 追踪并在退出时回收子树；管理员通过 SCM 停止服务。首版明确不自动重启主服务：主进程或 Shawl 异常时服务停止，由管理员检查日志并手动启动。推理 worker 的原生重建不受此选择影响。未验收 Shawl `--restart` 或 SCM 自动恢复，不声称已提供相应能力。

以真正管理员权限创建临时手动服务 `BasepackR9Probe_20261109`，账户为 LocalSystem。健康检查通过后保存 Shawl、真实 LitServe 主进程和全部已启动子进程，再执行下列操作：

| 操作 | 服务停止及进程回收耗时 | 测试补杀 |
| --- | --- | --- |
| SCM 正常停止 | 约 0.184 秒 | 无 |
| 直接强杀实际 LitServe 主进程 | 约 0.476 秒 | 无 |
| 直接强杀 Shawl | 约 0.203 秒 | 无 |

三种操作后原进程树均无存活进程，静默观察 2 秒后服务保持 Stopped；临时服务随后删除。账户、命令、PID、退出状态和日志见 `scm-receipt.json`、`scm-admin.log` 与 `scm-logs/`。这些耗时是本次假模型观测，不是正式服务的停机时限承诺。

### 证据与接续

必要探针脚本、日志、回执和上游源码快照已选留到根 `artifacts/runs/r9/service/`，不依赖 `tmp/` 长期保留。快照中的原运行路径仍指向当时临时环境，供复核原条件，不作为正式服务定义。

真实模型结果见下节；CPU 小试保留其原条件。

## 普通安装与真实联合验收

系统 Python 的 core/jobs 和 `C:/ProgramData/basepack/envs/service/` 的服务包均普通安装 0.5.0 wheel；源码、wheel 与两处安装的代码/模板一致性在最终交付时记录。纯净环境由 uv.lock 和显式 cu128 索引准备，未改变系统模型依赖、机器权重和 Condor 60/70 策略。修复后的源码与源码外安装回归各 68 项通过。

两个中文及空格路径项目从源码外包初始化并使用公开入口。原证在 `artifacts/runs/r9/runtime/runtime-processor-boundary/`，输入、结果、日志、公开调用脚本与独立观测器相邻保留。

| 场景 | 实际结果 |
| --- | --- |
| 两项目并发请求 | 同一 worker PID 57368、同一新向量身份，输出均 2048 维且归一化 |
| CPU 14343.0 | 结果 499500，退出 0，确认回收 |
| 应用失败 14344.0 | 原始退出码 7，success=false，确认回收 |
| GPU 14345.0 | 真实 CUDA 矩阵结果 256，持续约 35 秒、9983 轮，保留 Condor 设备 UUID，确认回收 |
| 边界 embedding | 四条实际 2048-token 文本同批；1600×1200 原图按像素预算缩放至 995328 像素，图片及图文向量正常 |
| 计算重叠 | 已安装模型的同步 forward 时间段内观察到普通 GPU 作业完整 CUDA matmul；文字、图片、图文均有证据 |
| 观察超时 | 客户端 0.001 秒明确 TimeoutError；另一项目仍由同 worker 正常响应 |
| 取消 14346.0 | Condor removed、已知应用及后代均退出、cleanup_confirmed=true；另一项目模型仍存活 |
| 容量与配置 | 结束后 12 CPU/24576 MiB RAM/4 同卡名额/7164 MiB 普通池全部归还，60/70 文件 SHA256 前后相同 |

全卡 nvidia-smi 共 292 个采样，峰值 8246 MiB；模型观测峰值 allocated 约 6871 MiB、reserved 7022 MiB。观测器添加 CUDA 同步与日志，只用于确认真实计算区间和资源峰值，不据此声称物理 SM 同时执行或吞吐提升。它通过临时服务环境变量挂载，运行包始终来自 site-packages；正式生命周期测试前已移除，最终服务定义不含 tmp 或 PYTHONPATH。

边界夹具初用裸 AutoTokenizer 计出 2048，实际 Processor 保留额外 EOS 得到 2049，产品正确拒绝且没有进入 forward。该轮记录为失败；修正测试唯一计数源为实际 AutoProcessor 后，四条实际 tokens 均为 2048，并重新完成上述联合验收。失败回执保留在 `artifacts/runs/r9/failures/`。

## 正式服务生命周期

正式 SCM 定义使用 LocalSystem、Manual、Shawl `--no-restart --kill-process-tree --stop-timeout 3000`，无临时观测器。真实模型测试通过，原证见 `artifacts/runs/r9/lifecycle/lifecycle-final/`：

- 在途 worker 92696 被强杀，请求返回 HTTP 500；未重放失败请求，LitServe 原生重建为 165052 后可正常推理。该故障注入确认客户端请求在途，不声称准确定位在模型 forward 内。
- SCM 正常停止、强杀真实 LitServe 主进程、强杀 Shawl 三种情况下，整棵已捕获进程树均退出，无测试补杀；显存各下降 4229 MiB，静默窗口后保持 Stopped。
- 包含观察显存及 2 秒静默窗口的耗时分别约 5.09、2.44、2.35 秒；这些是本机观测而非固定停机时限承诺。每次由管理员显式重新启动，模型和相同向量身份均恢复。

主服务仍需管理员手动恢复，worker 由 LitServe 原生重建。没有新增自写 supervisor、通用进程所有权或推理重试。

## 回退演练

第一轮恢复旧 wheel 与机器配置成功，但旧 supervisor 在原子替换历史 broker.json 时得到 WinError 5，整轮明确失败，随后正常恢复 0.5.0 服务。历史登记 PID 17804 已不存在，文件属性与 ACL 可写；Windows 受控探针复现了目标文件被读取时替换报相同错误、关闭读取后成功的行为，与启动时并发读取过期登记的竞争一致。没有修改 ACL、旧包或增加重试。

将该过期登记原样保存至 `D:/AgentTools/state/basepack/rollback/r9/legacy-registration/` 后，重新完成真实 0.5→0.4→0.5 演练。0.4.0 从 site-packages 启动旧 supervisor，worker 248048 生成有限、归一化的 2048 维文本向量；旧身份为 `Qwen3-VL:9b224ef380b04193c72819c7d13e689da1413739d3152e4a598e9ec6f13cc7ac`。用旧 admin 正常停止后 supervisor/worker 均退出，无补杀。

随后恢复 0.5.0 wheel 与原 0.5 机器配置字节，重新启动正式 SCM。fresh 进程确认模块版本与发行元数据均为 0.5.0，worker 253232 返回原新向量身份及有效 2048 维向量；两个项目全文件、60/70 策略和机器配置哈希前后不变。服务环境无需重新安装依赖。成功回执、调用脚本及逐步命令见 `artifacts/runs/r9/deployment/rollback-cleared-registration/`，原失败及恢复证据仍在 `artifacts/runs/r9/failures/rollback-final/`。


## 最终交付与结案

0.5.0 wheel 位于 `experiments/20261106-basepack/dist/r9/basepack-0.5.0-py3-none-any.whl`，29387 字节，SHA256 `454342ea807a96f1b4af3f46db8b6dc5d40fb77b6f280de81f514a3d78fbf2e1`。24 份代码、模板和许可与源码、wheel、系统及服务两处普通安装逐字一致，两处发行元数据也与 wheel 一致；核心 pip 来源记录的 hash 匹配，服务 uv 来源记录的 URL 匹配（uv 未记录 archive hash，以实际内容逐字核对）。两个环境的公开模块版本均为 0.5.0，导入保持轻量，退役模块均不存在。原生 uv 锁检查与服务依赖检查通过，公开 stop/status/embed CLI 通过。

| 维护面 | 原 0.4.0 | 交付 0.5.0 |
| --- | --- | --- |
| 产品 Python 源码 | 24 文件、1661 非空行 | 18 文件、834 非空行，约减少 49.8%；含注释，不含测试/文档/锁 |
| 模型与服务适配 | 自写模型子类、预处理、pooling、HTTP、队列和生命周期 | ST 与 LitServe 薄适配；Shawl/SCM 拥有进程树 |
| 配置与环境 | 系统模型依赖、私有 marker、idle_seconds | 核心安装加一个锁定的纯净服务环境，endpoint/service_name/queue_timeout；预算与项目格式保持 |
| 运维 | 手动 launcher 与私有管理 RPC | 原生服务注册/控制/日志；常驻模型、worker 原生重建、主服务手动恢复 |

初次 D 盘候选依赖环境已删除；正式服务不依赖 tmp、源码检出或临时观测器。必要探针、配置与安装回执、原始错误、向量及进程/GPU 时间线选留在 `artifacts/runs/r9/`，最终一致性回执为 `final-installation.json`。旧 0.4.0 wheel、机器配置及过期登记保留在共享回退目录；模型和 Condor 策略继续各自维护。

本任务 R0–R9 全部结束，材料整体归入 `devDoc/archive/20261107-resource-coordination/`；现行合同交给根 system 与产品文档，记忆 P2 取得公开接口和新语义身份。记忆检索、图与数据库仍由独立任务交付。此轮按模型、服务、通用观察和文档分工；宿主未提供可归因的主上下文、往返次数或团队 token 统计，阶段时间保留在回执，不据此声称节省用量。
