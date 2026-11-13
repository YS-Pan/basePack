# AgentTools 迁移进度

更新：2026-11-13。范围与阶段见 [plan.md](plan.md)。

## 当前状态

用户已授权执行，实施中；本次大文件根已明确选择 `D:/AgentTools`。三个分支在根 tmp 的候选副本中并行实现，原源码/Codex project 保持原位；系统安装、资产归集和调用方切换由主 agent 统一执行。

已由两个 tier2 分别核 AIGC、TTS，一个 tier3 核用量统计；主 agent 核当前 basePack/AgentTools 安装、接口、官方上游与调用方，整合为系统 Python 优先路线。实际使用模型与推理强度来自本项目 config ai：tier2 为 gpt-6.1-terra/ultra，tier3 为 gpt-6.1-sol/ultra。团队用量不可得，未作成本结论。

已确认 AIGC 的 Transformers 5 tokenizer 接口差异、TTS 发布包的 Python/Transformers 约束、8765 配置冲突，以及用量统计自动创建 .venv/源码目录持久写入需要调整。候选实际模型行为与共享依赖集合尚未验证。

下一步先交付用量统计，再 AIGC、TTS；分支候选通过必要检查后统一安装和切换，不把兼容声明或单元测试当作真实功能验收。

### 18:35 实施检查点

- 三个轻量 wheel 候选已构建：用量统计 0.2.0、AIGC 0.10.0、TTS 1.2.0。包内包含各自代码和小资源，不相互依赖；原源码目录与 Codex project 未迁移。
- 用量统计 217 项合成测试、24 项异目录安装检查、数据/zstd/缓存、PNG/MP4 与 Tk 更新/取消检查通过。33 个相关文件已按原快照逐项校验、备份并应用到原源码；原有三个媒体改动未覆盖。正式系统 Python 3.13 已通过普通 pip 用户安装装入 codex-usage-plot 0.2.0 和 backports.zstd 1.8.0；现有科学计算库未升级或降级。用户安装目录属于该系统解释器，未新建工具虚拟环境；`python -m codex_usage` 不依赖用户 Scripts 加入 PATH。真实设置/缓存转移及增量验收继续进行。
- AIGC 183 项完整候选测试及最后 20 项定点测试通过；22 个本地 tokenizer 在原 Transformers 4.57.6 与系统 5.22.1 上的 token、offset 和窗口一致。真实模型前后对照执行中，未据此宣称分数和统计后端兼容。
- TTS 候选在干净 3.13 轻安装下的 help/plan、包资源、缺资源非交互退出通过；旧 3.12 下契约和小模型检查通过。系统 3.13 的 Kokoro/Misaki 固定上游提交可解析、英文 G2P 离线检查通过；CosyVoice 的新依赖组合及实际音频仍在验证，尚未改系统 TTS 依赖。
- Condor 实测普通 GPU 池为 7164 MiB，旧计划引用的 5116 MiB 不再作为本轮申报依据。测试实际暴露 worker 缺少用户环境变量，以及 librosa/platformdirs 在 worker 账户访问 Windows Known Folder 失败；已保存原错误，使用明确的任务缓存目录与真实用户环境进行对照，未修改工具业务逻辑来掩盖故障。

实施脚本、候选与测试原证暂在 `tmp/20261113-tool-migration-impl/`；正式应用前的原文件备份在 `artifacts/runs/20261113-tool-migration/source-backup/`。任务收尾时保留所需运行原证和短结论。

实施工作区为 `tmp/20261113-tool-migration-impl/`，`source-baseline.json` 保存起点、原 Git 状态和候选文件哈希。用量 main@48efc99 的三个媒体本地改动原样保留。AIGC main@0136784 之后已有大量工作树/未跟踪的 0.9 代码，候选使用现行工作树，不能按旧 HEAD 覆盖。TTS 原目录尚无 Git；源码/vendor 副本排除模型、环境和输出。

分支负责人沿已解析档位实际派发：用量由 tier3 负责，AIGC/TTS 由 tier2 负责，各自管理有限 helper；主 agent 负责依赖与资源窗口、外部路径整合和最终交付。相关代码只在各候选目录修改，未先改外部正式环境。

用户随后明确独立安装、代码安装为 Python 包及首次大文件下载先选目录。计划已修订：AgentTools 改为可选资源根建议，basePack 改为可选调度；开发源码不要求迁入 AgentTools/tools。基础安装仅含轻量代码/依赖，重型运行库与模型按所需功能准备；人工与 agent 共用准备入口，agent 下载前取得用户目录选择，库/HTTP/无人值守缺资源时明确返回准备要求。安装与上述首次使用行为均待实施验证。

用户进一步明确未来可分别发布独立 GitHub 仓库，单工具用户无需知道其余工具存在。计划已补各包独立声明/发布/验收边界，basePack 改为外部通用命令调度，工具无需反向依赖。已核 AIGC CLI/HTTP 调本工具 Detector、TTS CLI 调本工具 service/引擎、用量 GUI 调本包报告入口；这些内部复用已存在，三工具共用业务核心未计划建设。未实施打包或调度接入。

用户要求保留原 Codex project 继续开发。计划已明确源码保持原位、project/聊天保留，开发检查后更新普通安装包，再从源码外核已装版本。此前 list_projects 核到 TTS 与用量统计仍绑定原源码目录，AIGC 未出现在该次可见登记中；该观察不推断其不存在，也不作为本次迁移的前置。未修改任何 Codex project、聊天归属或目录。

按用户本次要求移除 Codex 应用内操作：当前专用工具可管理部分聊天及侧边栏，但没有编辑 project 主文件夹的入口。计划删去 Edit project、主目录重绑及聊天 cwd 同步等安排；本轮固定保留源码目录与现有开发入口，不把应用操作转为用户必须完成的迁移步骤。

## 检查与限制

- 已检查源代码、锁及普通安装元数据、工具 launcher/路径、已知消费者、官方兼容资料；未加载模型、合成音频、读取用量原始对话或改动机器配置。
- 计划文档完成 UTF-8、相关本地链接及 Git 差异检查；不运行无关产品回归。
- 当前系统包为 basePack 0.5.0，本项目客户端 0.12.0.dev1，共享服务保持原安装，分别记录，未将版本混为统一全机状态。

## basePack 使用反馈

2026-11-13，0.12.0.dev1 客户端初次 brief 在沙箱内连接 `http://127.0.0.1:18080` 被拒（WinError 10061）。随后以正常用户恢复原数据库服务，brief 成功返回 3 条 mandatory，已用于本轮实施。数据库继续作为项目常驻入口保留。

自动维护早期尝试遇到 Codex App Server sqlite ACL、随后 embedding 服务停止；失败记录已保留，相应 control 均按 stop/owner/release 收尾。用户已以管理员启动原 BasepackEmbedding，健康检查恢复 200。最新自有 run `d55e5a71470845d2b95614621eb32c7b` 已按脚本返回的模型与推理强度派出协调者，全项目扫描 1248 个 Git 来源，当前处理中；业务收尾时独立执行 stop、确认发布结束、释放所有权，再记录实际覆盖。
