# AgentTools 迁移进度

更新：2026-11-13。范围与阶段见 [plan.md](plan.md)。

## 当前状态

用户已授权执行，实施中；本次大文件根已明确选择 `D:/AgentTools`。三个分支在根 tmp 的候选副本中并行实现，原源码/Codex project 保持原位；系统安装、资产归集和调用方切换由主 agent 统一执行。

已由两个 tier2 分别核 AIGC、TTS，一个 tier3 核用量统计；主 agent 核当前 basePack/AgentTools 安装、接口、官方上游与调用方，整合为系统 Python 优先路线。实际使用模型与推理强度来自本项目 config ai：tier2 为 gpt-6.1-terra/ultra，tier3 为 gpt-6.1-sol/ultra。团队用量不可得，未作成本结论。

三个工具的独立包、候选真实功能与共享依赖集合已完成验证；用户已执行管理员机器安装，正式系统 Python 的三工具导入和全机 pip check 通过。当前进行机器安装后的调用方与入口收尾。

源码仍在三个原项目。用量统计已提交 main@edda407；AIGC 原有大量未提交工作与 TTS 无 Git 的状态保持，迁移文件已应用且原内容保存在任务备份。下一步完成正式安装包的异目录/HTTP/GUI/消费者检查，保留实际限制并记录恢复入口。

### 正式系统安装与资源归集

- 最终发行：codex-usage-plot 0.2.0、local-aigc-detectors 0.10.0、local-kokoro-tts 1.2.0。三个包分别独立，基础 wheel 不含模型或大型运行库；本机按完整功能显式安装依赖，共用 `C:/Program Files/Python313/python.exe`，无新增常驻工具虚拟环境。
- 曾先装入 user-site 的包在 ysPan 下可用，但 Condor 的独立槽账户读取私人 Roaming 返回 WinError 5；不能通过设置用户环境变量授予权限。已准备离线机器包并实际预检后，请用户完成必要的 Windows 管理员写入。用户已执行，97 个包新增、原 232 份全局登记版本保留，正式 pip check 通过；三工具从系统 `Lib/site-packages` 导入。本任务旧 user-site 副本已卸载，普通导入也来自系统包。
- 离线包与唯一管理员步骤保留在 `D:/AgentTools/installers/20261113-three-tools/`；含 wheel 哈希、来源、约束、安装前后计划、日志和用户路径回执。模型没有随此安装下载。ysPan 的普通 Roaming 配置已由实际桌面 PowerShell 登记，三个工具均指向本次确认的 D 盘位置；Codex 宿主上下文也沿用相同选择。
- AIGC 179 个现有资源文件（55,458,054,087 B）同卷移至 `D:/AgentTools/models/aigc-detect`；TTS 25 个现有模型/音色文件（4,769,138,640 B）同卷移至 `D:/AgentTools/models/tts`。前后相对文件清单、长度、时间和 manifest 哈希相同；源码保留小 manifest。AIGC 中文准备入口复核哈希通过，TTS 两后端 `--use-existing` 均 ready、downloads=[]。用量状态与报告在 `D:/AgentTools/state/codex-usage`，原缓存/备份/报告保留恢复定位。
- 原源码已按快照校验应用：用量 33 项、AIGC 38 项、TTS 41 项。TTS 固定 vendor 源码、许可和默认小参考录音不再被 Git 忽略；旧 venv 安装/修复及无法重放新补丁的源码安装入口明确退役。未创建或修改任何 Codex project/聊天设置。
- 另以真正普通 AIGC CLI 默认缓存运行十模型中文标注（14384.0），完整报告和输入哈希检查通过、进程回收已确认。Torch reserved 峰值 6,891,241,472 B，明显高于逐模型清缓存的数值对照测试；申报使用整普通 GPU 池 7164 MiB，不能拿后者的低峰值代替实际 CLI 预算。此短样本不证明所有长度或并发上限。

正式文件应用前的备份、模型移动回执及选留功能证据已保存在 `artifacts/runs/20261113-tool-migration/`；临时候选环境只用于本轮验证。新旧公开样本 WAV 在该目录的 `audio/`，自动 QA 及恢复已验，主观听审未完成；不以自动检查代替发音和自然度判断。

### 18:35 实施检查点

- 三个轻量 wheel 候选已构建：用量统计 0.2.0、AIGC 0.10.0、TTS 1.2.0。包内包含各自代码和小资源，不相互依赖；原源码目录与 Codex project 未迁移。
- 用量统计 217 项合成测试、24 项异目录安装检查、数据/zstd/缓存、PNG/MP4 与 Tk 更新/取消检查通过。33 个相关文件已按原快照逐项校验、备份并应用到原源码；原有三个媒体改动未覆盖。正式系统 Python 3.13 已通过普通 pip 用户安装装入 codex-usage-plot 0.2.0 和 backports.zstd 1.8.0；现有科学计算库未升级或降级。用户安装目录属于该系统解释器，未新建工具虚拟环境；`python -m codex_usage` 不依赖用户 Scripts 加入 PATH。真实设置/缓存转移及增量验收继续进行。
- AIGC 183 项完整候选测试及最后 20 项定点测试通过；22 个本地 tokenizer 在原 Transformers 4.57.6 与系统 5.22.1 上的 token、offset 和窗口一致。真实模型前后对照执行中，未据此宣称分数和统计后端兼容。
- TTS 候选在干净 3.13 轻安装下的 help/plan、包资源、缺资源非交互退出通过；旧 3.12 下契约和小模型检查通过。系统 3.13 的 Kokoro/Misaki 固定上游提交可解析、英文 G2P 离线检查通过；CosyVoice 的新依赖组合及实际音频仍在验证，尚未改系统 TTS 依赖。
- Condor 实测普通 GPU 池为 7164 MiB，旧计划引用的 5116 MiB 不再作为本轮申报依据。测试实际暴露 worker 缺少用户环境变量，以及 librosa/platformdirs 在 worker 账户访问 Windows Known Folder 失败；已保存原错误，使用明确的任务缓存目录与真实用户环境进行对照，未修改工具业务逻辑来掩盖故障。

实施脚本、候选与测试原证暂在 `tmp/20261113-tool-migration-impl/`；正式应用前的原文件备份在 `artifacts/runs/20261113-tool-migration/source-backup/`。任务收尾时保留所需运行原证和短结论。

### 实际功能验证补充

用量统计正式 0.2.0 已用旧缓存完成增量：7247 文件复用、0 重读、0 解析失败；旧 399340 个 event 指纹及 6388 个 session 全部保留，新增 7784 个 event。源缓存、设置、32 份旧报告及三项本地媒体的前后哈希不变；目标缓存为 SQLite 原生一致性备份，并经 quick_check。普通桌面与 Codex/MSIX 的 APPDATA 配置可见性继续核对，不能只以宿主中的路径保存成功验收。

AIGC 分类器旧版任务 14363.0 与候选任务 14365.0 完整通过并确认进程回收。公开中英文样本的默认 annotate、Desklib/CoCoDet 与两组 raw 检测：31 组 token/offset/window 事件一致，在 abs/rel=1e-4 下分数与标签无差异（整数和 token 严格相等）。系统已普通安装 0.10.0，第三方依赖无变更；统计后端和正式资产位置仍待验。安装审阅发现并修复 CLI 在准备前未拒绝不合法分类器 ID、仅 wheel 用户无法定位 skill 等问题。

TTS 原 3.12 基线任务 14366.0 已实际生成中文混读 23.76 秒、英文 22.91 秒音频，自动 QA 通过并确认进程回收；未将自动 QA 当作人工听审。系统 3.13 依赖验证发现 HyperPyYAML 1.2.3 与系统 mdformat_frontmatter 2.2.0 的 ruamel 约束无交集，且旧 Loader 在 ruamel 0.19.1 实际缺少 max_depth。候选将原 YAML 辅助源码纳入私有命名空间、使用公开 loader 参数适配，两代 ruamel 的标签和真实配置占位构造通过；完整新运行时音频仍待验，不降级系统 Markdown 依赖。

实施工作区为 `tmp/20261113-tool-migration-impl/`，`source-baseline.json` 保存起点、原 Git 状态和候选文件哈希。用量 main@48efc99 的三个媒体本地改动原样保留。AIGC main@0136784 之后已有大量工作树/未跟踪的 0.9 代码，候选使用现行工作树，不能按旧 HEAD 覆盖。TTS 原目录尚无 Git；源码/vendor 副本排除模型、环境和输出。

分支负责人沿已解析档位实际派发：用量由 tier3 负责，AIGC/TTS 由 tier2 负责，各自管理有限 helper；主 agent 负责依赖与资源窗口、外部路径整合和最终交付。相关代码只在各候选目录修改，未先改外部正式环境。

用户随后明确独立安装、代码安装为 Python 包及首次大文件下载先选目录。计划已修订：AgentTools 改为可选资源根建议，basePack 改为可选调度；开发源码不要求迁入 AgentTools/tools。基础安装仅含轻量代码/依赖，重型运行库与模型按所需功能准备；人工与 agent 共用准备入口，agent 下载前取得用户目录选择，库/HTTP/无人值守缺资源时明确返回准备要求。安装与上述首次使用行为均待实施验证。

用户进一步明确未来可分别发布独立 GitHub 仓库，单工具用户无需知道其余工具存在。计划已补各包独立声明/发布/验收边界，basePack 改为外部通用命令调度，工具无需反向依赖。已核 AIGC CLI/HTTP 调本工具 Detector、TTS CLI 调本工具 service/引擎、用量 GUI 调本包报告入口；这些内部复用已存在，三工具共用业务核心未计划建设。未实施打包或调度接入。

用户要求保留原 Codex project 继续开发。计划已明确源码保持原位、project/聊天保留，开发检查后更新普通安装包，再从源码外核已装版本。此前 list_projects 核到 TTS 与用量统计仍绑定原源码目录，AIGC 未出现在该次可见登记中；该观察不推断其不存在，也不作为本次迁移的前置。未修改任何 Codex project、聊天归属或目录。

按用户本次要求移除 Codex 应用内操作：当前专用工具可管理部分聊天及侧边栏，但没有编辑 project 主文件夹的入口。计划删去 Edit project、主目录重绑及聊天 cwd 同步等安排；本轮固定保留源码目录与现有开发入口，不把应用操作转为用户必须完成的迁移步骤。

## 检查与限制

- 评估阶段检查源代码、锁及普通安装元数据、工具 launcher/路径、已知消费者和官方兼容资料；实施阶段的真实模型、音频与系统安装范围以本页检查点为准。用量工具只读取统计元数据，不输出原始对话正文。
- 计划文档完成 UTF-8、相关本地链接及 Git 差异检查；不运行无关产品回归。
- 当前系统包为 basePack 0.5.0，本项目客户端 0.12.0.dev1，共享服务保持原安装，分别记录，未将版本混为统一全机状态。

## basePack 使用反馈

2026-11-13，0.12.0.dev1 客户端初次 brief 在沙箱内连接 `http://127.0.0.1:18080` 被拒（WinError 10061）。随后以正常用户恢复原数据库服务，brief 成功返回 3 条 mandatory，已用于本轮实施。数据库继续作为项目常驻入口保留。

自动维护早期尝试遇到 Codex App Server sqlite ACL、随后 embedding 服务停止；失败记录已保留，相应 control 均按 stop/owner/release 收尾。用户已以管理员启动原 BasepackEmbedding，健康检查恢复 200。最新自有 run `d55e5a71470845d2b95614621eb32c7b` 按脚本返回的模型与推理强度派出协调者，全项目扫描 1248 个 Git 来源，固定语义回执 45 来源已处置 42（35 initial、7 existing-change），发布均成功；剩余 3 条原始聊天捕获缺口不可恢复，重复 member ID 入口校验缺陷反馈仍 pending。协调者已结束，主 agent 已 stop 自有 control，owner 核 publications=[] 后 release 成功。维护原证在 `tmp/basepack-maintenance/812cbdf9557c45cabd7b9873594e1ddc/9a553459f2904853a3a3d6ccf465f438/`。

资源客户端 0.12.0.dev1 使用反馈：观察排队任务 `jobs wait 14367.0 --timeout 45` 时，内部 `condor_wait -wait 4` 约 4.04 秒触发原始 subprocess.TimeoutExpired；这不是任务失败。已保留 traceback，本轮按 status 观察原任务，未重提任务；等待调用的进程超时预算问题待资源工具所属后续修复。
