# 开发环境核验

## 当前开发入口与临时目录

当前唯一 active 路线位于 `experiments/20261106-basepack/`；安装、构建与测试目标均为该实验工程，具体命令见 [路线 README](../../experiments/20261106-basepack/README.md)。从仓库根运行 pytest 时，显式指定实验的 pyproject、tests 和根 `tmp/<task>/pytest` 作为 basetemp。pytest 不保留持久缓存；构建 TEMP/TMP 和隔离验证环境也进入根 tmp。目录寿命见 [文档维护约定](../documentation.md)。

2026-11-09 先前布局迁移只改变开发维护位置；当时系统安装为 0.4.0。其后 R9 形成下节的 0.5.0 共享资源基线，此后在独立稳定环境安装客户端并运行项目局部数据库。历史快照按各自条件阅读。

选留证据现统一位于根 `artifacts/runs/`。前次临时材料整理的映射为 `artifacts/runs/tmp-reorganization-20261108/moves.json`，本次位置映射为 `artifacts/runs/20261109-project-layout/moves.json`；原始回执及下文历史路径保留当时含义，结合两轮映射回查长期副本，tmp 内容按可清除处理。

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

以下技能使用根 `.agents/skills/` 的项目级发现入口，junction 指向唯一维护源。2026-11-09 将 resources 的目标切至 active 实验内，其余两项保持根维护源。新检出时按下例建立联接；历史发现回执保留当时作用域和名称。[Codex 官方作用域说明](https://learn.chatgpt.com/docs/build-skills#where-codex-loads-local-skills) 区分项目级与用户级入口。

| Skill | 维护源 | 本机发现入口 |
| --- | --- | --- |
| `file-structure` | [SKILL.md](../../skills/file-structure/SKILL.md) | `.agents/skills/file-structure` |
| `agent-team` | [SKILL.md](../../skills/agent-team/SKILL.md) | `.agents/skills/agent-team` |
| `resources` | [SKILL.md](../../experiments/20261106-basepack/skills/resources/SKILL.md) | `.agents/skills/resources` |

本机联接由 `.gitignore` 排除，不重复保存源码。仓库换路径或新检出时，如需在技能列表中自动发现，可从仓库根目录首次建立项目级入口：

```powershell
New-Item -ItemType Directory -Force -Path '.agents/skills' | Out-Null
$skillSources = @{
    'file-structure' = 'skills/file-structure'
    'agent-team' = 'skills/agent-team'
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
