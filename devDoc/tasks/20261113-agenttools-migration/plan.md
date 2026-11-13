# AgentTools 三工具迁移计划

2026-11-13。状态：已完成本轮评估，实施待启动。本轮仅交付计划；用户要求尽量共用系统 Python，并将 Codex 用量统计一并归集。实际进度与使用故障见 [progress.md](progress.md)。

## 推荐方案与范围

三个工具独立维护、普通安装到共用系统 Python；basePack 复用现有资源提交能力。先验证依赖与真实功能，再移动源码、共享资产和调用入口。推荐交付顺序：**共同准备 → Codex 用量统计 → AIGC → TTS → 调用方联合验收与退役旧入口**。TTS 的兼容调查可与前两项并行，不成为它们交付的前置。

| 工具 | 现维护源 | 目标维护源 | Python 路线 |
| --- | --- | --- | --- |
| Codex 用量统计 | `D:/project/trifles/20260829 codex usage` | `D:/AgentTools/tools/codex-usage` | 系统 3.13；补打包和显式运行目录，改掉自动创建项目环境 |
| AIGC 检测 | `D:/project/20260928 aigc detect` | `D:/AgentTools/tools/aigc-detect` | 优先适配系统现有 Transformers 5，保留模型、profile 和输出含义 |
| TTS | `D:/project/20261004 text to speech` | `D:/AgentTools/tools/tts` | 先验证系统 3.13 上的 Kokoro/Misaki、CosyVoice 及配套音频依赖 |

用户原意见 [11 月 4 日「梳理项目任务依赖」](codex://threads/01a1a488-6632-7842-9c8f-11326461a416)。旧方案的资源入口前置已由 basePack 交付，按 [当前资源实现](../../system/modules/resources.md)、[部署合同](../../system/deployment.md) 和 [资源使用](../../../experiments/20261106-basepack/docs/resources.md) 接入，无需重做资源管理或先完成记忆系统后续工作。

工具核心、模型选择与业务规则仍归各工具。首期沿用 CLI/Python 与现有 skill；AIGC 的既有 HTTP 调用按需要保留并接入同一执行入口。模型、共享状态、业务输入输出分别定位；项目记忆与 Codex 原日志维持原归属。

## 本轮已核事实与待验证部分

本轮只读检查源代码、依赖声明、安装元数据、已知调用方和官方上游；未安装依赖、加载模型或运行真实推理。

| 对象 | 2026-11-13 观察 | 对计划的影响 |
| --- | --- | --- |
| 系统 Python | `C:/Program Files/Python313/python.exe`，3.13.17，非 venv；Torch 2.10.0+cu128、Transformers 5.22.1、Hub 1.33.0、NumPy 2.5.4 | 以现有兼容集合为首选，合并工具需求后再统一安装；元数据可导入不等于模型功能通过 |
| basePack 安装 | 系统资源包仍为 0.5.0；本项目独立客户端为 0.12.0.dev1，共享 embedding 是独立服务环境 | 使用已验客户端提交任务，JobSpec.executable 单独指定工具的系统解释器；本轮迁移不要求合并已有服务环境或先升级全部客户端 |
| 用量统计 | Matplotlib、NumPy、pandas、tzdata 已装；Tkinter 8.6 可导入；缺 imageio-ffmpeg、backports.zstd；PATH 有 FFmpeg/ffprobe | 系统路线阻力较小，仍需解析依赖并验证动画、压缩日志和 GUI；第三方包按正式需求补齐 |
| AIGC | 包固定 Transformers 4.57.6，与系统 5.22.1 的 Hub 依赖不相容；fast tokenizer 的 prepare_for_model 调用在 v5 失效 | 适配 tokenizer 和加载接口，完成旧版数值对照；放宽版本号或 no-deps 安装不能证明兼容 |
| TTS | 现有已验环境是 Python 3.12；Kokoro/Misaki 发布包 0.9.4 限制 Python<3.13；CosyVoice 清单固定 Transformers 4.51.3；系统缺 torchaudio 等 | 系统路线需要实际适配和短音频证明，不能承诺直接安装旧锁即可工作 |
| 资源与端口 | AIGC 默认 HTTP 和 basePack embedding 都用 127.0.0.1:8765；当前机器配置给 embedding 预留 9216 MiB，历史普通 GPU 池为 5116 MiB | AIGC HTTP 另设明确端口并同步消费者；真实容量在实施时查询，7B 模型现有 10 GiB 默认预算必须重新处理 |

AIGC 的接口变化依据 [Transformers 5 官方迁移指南](https://github.com/huggingface/transformers/blob/v5.22.1/MIGRATION_GUIDE_V5.md#removed-methods)。统计后端传入的旧内存加载参数在系统 v5 被忽略，7B 模型的 CPU/GPU 峰值与卸载也须实测。

[Kokoro](https://github.com/hexgrad/kokoro/blob/main/pyproject.toml) 和 [Misaki](https://github.com/hexgrad/misaki/blob/main/pyproject.toml) 官方 main 已将范围放宽到 Python<3.14，是可冻结提交验证的候选；[Kokoro 0.9.4](https://pypi.org/project/kokoro/0.9.4/) 与 [Misaki 0.9.4](https://pypi.org/project/misaki/0.9.4/) 发布包仍限制 Python<3.13。[CosyVoice 官方清单](https://github.com/QwenAudio/CosyVoice/blob/main/requirements.txt) 仍固定 Transformers 4.51.3。实施时固定实际 tag/commit 和构建产物，源码声明不等于本机功能支持。

系统路线若遇到有复现依据、短期无法解决的 TTS 阻塞，明确保留未达目标部分；可暂用已有已验 TTS 3.12 入口，或将必要兼容运行时作为机器共享例外另行确定。其余两个工具继续交付。旧 AIGC/TTS 的 Transformers 锁也不同，不能直接假定把它们放进同一个 3.12 环境即可解决。每个工具新建一套环境不作为默认方案。

## 目标布局与安装责任

```text
D:/AgentTools/
  tools/
    codex-usage/                 独立源码、测试、文档、发布定义
    aigc-detect/
    tts/                        含固定来源的必要 vendor 代码
  models/                       权重按现有身份与 revision 共用
  state/
    codex-usage/                本机设置、SQLite 缓存、默认报告
    aigc-detect/                机器配置、日志与可重建 scratch
    tts/                       机器配置与工具缓存
    basepack/                  沿现状保留
  constraints/
    system-python313.txt       本机已联合验证的共用依赖约束
  bin/、envs/、profile/          沿现状按用途维护
  basepack.toml                 仍只维护 basePack 资源设施配置
```

工具 pyproject 声明各自需求；本机约束集中维护共用依赖的实际版本与必要 wheel 来源。安装使用标准 pip/uv 与普通 wheel，运行入口从选定系统解释器的 site-packages 导入；源码维护根与安装位置各有职责。对外分发仍保留工具自己的依赖声明。

模型 manifest、revision、来源和必要校验信息随工具维护，权重通过明确配置定位共享 models。保持 Hugging Face snapshot/相对目录及 vendor 的来源、许可证和版本，迁移先保留原布局可识别性，再按需要归一。配置由各工具唯一解析，不向 basePack 的机器 schema 塞入无消费者的通用工具注册系统。

业务报告和音频按调用方显式路径保存；用量统计的本机默认报告归 state/codex-usage。工具日志和缓存可写目录由配置定位，普通安装后不能由 __file__ 推导到 site-packages 写入。

## 实施阶段与完成条件

### 1. 固定起点及验证共同依赖

- 核三个工具的 Git/未提交文件、调用入口、固定模型和在途任务；保存旧包/锁、配置及恢复定位。用量统计当前 main 为 48efc99，三个已有本地改动均为输出媒体，迁移时保留，沿原项目约定排除两张 PNG 的后续提交。
- 先在可丢弃候选环境中复用或安装同版本依赖，做合并解析、Windows cp313 wheel 可得性、必要 import 与最短功能试验。候选环境仅用于验证，最终运行目标仍是系统 Python。Torch/torchaudio 版本与 CUDA 来源成对选择。
- TTS 先尝试固定上游兼容提交和最小代码适配，维持 CosyVoice 中文、Kokoro 英文；需要的模型、G2P 资源和 vendor 依赖明确登记。不以换掉现有语音能力来隐去兼容问题。
- 形成实际可满足的依赖集合及系统变更清单；有冲突的部分列出复现与下一步。**完成：候选路线和未解决项清楚，所选最短功能链确实运行，而非只有 resolver 或 pip check 成功。**

### 2. Codex 用量统计先交付

补 pyproject 和安装命令，保留 `python -m codex_usage`；启动器显式使用系统解释器，移除创建、修复工具专用 .venv 的日常流程。GUI 设置、缓存、报告及 query 的增量默认缓存共用一个路径解析源。

迁移 SQLite 前结束该工具的写入进程，连同必要 WAL/SHM 或原生一致性备份一起处理；保留设置、旧报告与 invalid 备份的恢复定位。当前缓存约 691 MB，属于已有本机状态，不是源码或小样例；本阶段不顺带清理。原始 `.codex` 日志保持原位。默认 query 继续只读扫描、不创建缓存；显式 cache/output 继续有效。

**完成：** 系统解释器、源码目录之外，用合成日志验证 query、增量与完整结果一致、压缩日志、报告和默认 MP4；检查图片及 GUI 启动/更新/取消/打开输出。可选 GIF 路径发生变化时定点验证。正式切换时用已有缓存验证一次真实增量和原统计身份保持，不顺带改价格、统计范围或图表含义。

### 3. AIGC 适配与资源接入

保留现有模型 revision、自定义 loader、窗口覆盖与 profile。修正 fast tokenizer 的特殊 token/窗口构造和 v5 加载接口，收敛模型根与 scratch 配置；同步独立 HTTP 端口、client、启停及健康入口。

GPU 推理和重 CPU/内存统计通过 basePack `jobs run` 一次提交完整任务，采用工具原有 CLI/核心；保持调用方 cwd、输入、报告与真实退出码。普通参数准备、已有结果重合并等轻任务可直接运行。若保留 HTTP，前端调用同一作业执行路径，模型驻留与资源许可同生命周期；首期优先任务结束释放模型的模式。现有进程内推理锁不能充当跨工具 GPU 协调。

**完成：** 旧锁环境与系统候选在固定样例上比较中英文原始 detect、中文十模型 annotate、英文默认融合及自定义 loader，核 token/特殊符号、切窗、原始与融合分、标签和完整报告；预先说明合理数值容差，门限附近的标签变化须处理。复用已有 smoke/deployment 测试并补实际差异回归。Neo/Falcon 统计路径另验峰值、卸载及 scratch，模型与 profile 不因迁移自动更换。

### 4. TTS 适配与资源接入

将模型、vendor、缓存、FFmpeg/ffprobe 和实际解释器显式配置；修复 doctor 对 root/.venv 的硬编码及按源码根找模型的行为。保留现有输出身份、显式覆盖、分块复用、损坏块恢复与失败回执。

GPU 与长文重任务沿同一 basePack jobs 入口；继承 Condor 的 CUDA_VISIBLE_DEVICES，逻辑 cuda:0 只表示进程可见设备。测整个应用树的 RAM/显存峰值后申报，既往短音频的 Torch allocated 不能替代总峰值。FFmpeg 路径与 MP3 编码器在执行账户下实测。

**完成：** 固定中文、英文及混读样例实际离线生成音频、解码并抽听；代表长文完整覆盖，原输入重跑可复用、损坏单块可重建、设置改变按原合同处理；CPU 路径与 Condor GPU 路径分别验证。原有模型和语音能力保持，新的依赖集合与恢复身份有证据。

### 5. 系统切换、路径迁移与联合交付

每个工具的候选通过后分别执行本节切换，用量统计和 AIGC 可以先交付；最后做联合验收。

候选通过后，结束使用受影响系统解释器的任务，再由一个安装者应用已定版本，保存变更包和可执行回退点。按本次实际依赖变化回验受影响工具与系统消费者；已有独立 embedding 服务只在自身实现或依赖确需改变时调整。

同卷移动源码及所需资产，保留各自 Git 历史、未跟踪必要材料和本地修改；虚拟环境按旧版恢复需要保留，不当成可直接改路径的正式新安装。更新配置、普通安装、启动器、快捷方式、dissertation 的两个 skill junction 及正文、huangzetao 的 external_projects 登记与 handoff；核三个 Codex project 路径和接续聊天 cwd，历史聊天和旧回执保留原义。

用调用方和另一中文/空格 cwd 验证最终入口：用量 query、检测完整报告、中文与英文音频。AIGC/TTS 与 embedding 验并发准入、排队、超时取消和进程回收；按实测声明预算。若 7B 或长音频需求超过当前普通池，验证可用的 CPU/offload 路线；确需改机器预算时单列设施调整，不能绕过准入或私自占用背景预留。

**完成：** 三工具逐项记录实际安装版本/解释器、调用命令、输入输出位置、真实功能与回收证据，恢复材料可用；已知调用方实际切换。随后退役已无人使用的旧运行入口和依赖，不删除原业务成果或改写历史回执。某工具仍有兼容阻塞时只报告已完成部分，其余继续交付。

## 实施组织与本轮边界

主负责人维护共用依赖、系统安装窗口与最终集成；工具分支可并行准备代码和样例，系统环境切换由一人统一执行。实施记录回到各工具原有文档，跨工具状态在本任务接续，避免三处维护同一环境结论。

本轮交付为以上评估与计划。依赖解析安装、候选推理、目录移动、消费者修改和真实迁移验收均属于后续实施；现有 tools 目标目录尚未创建。
