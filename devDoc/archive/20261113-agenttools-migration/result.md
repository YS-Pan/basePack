# 三工具迁移结果

2026-11-13。独立打包、资源归集、系统安装和已知调用方切换已完成。三个工具共用系统 Python 3.13，没有新增常驻工具虚拟环境；各自可独立安装，不依赖另外两个工具、AgentTools 或 basePack。

## 安装与使用

| 工具 | 正式包 | 本机资源/状态 |
| --- | --- | --- |
| 用量统计 | codex-usage-plot 0.2.0 | `D:/AgentTools/state/codex-usage`，默认报告在其 `reports/` |
| AIGC | local-aigc-detectors 0.10.0 | `D:/AgentTools/models/aigc-detect` |
| TTS | local-kokoro-tts 1.2.0 | `D:/AgentTools/models/tts` |

代码实际位于 `C:/Program Files/Python313/Lib/site-packages/`。普通命令、中文/空格工作目录以及 Condor 槽账户均验证使用机器安装包。基础 wheel 只含代码与小资源；重型运行库按功能显式安装，模型/音色首次准备先取得目录选择，库/HTTP/无人值守缺资源时返回准备要求。

```powershell
python -m codex_usage gui
python -m aigc_detector --help
python -m local_tts --help
```

本次约 55.46 GB AIGC 文件、4.77 GB TTS 文件均复用原资源，同卷移动前后清单、长度、时间和 manifest 哈希一致。原始 `.codex` 日志及业务成果保持原位，未下载新的模型。机器安装新增 97 个发行包，原 232 份全局包登记版本保留，pip check 通过；旧 user-site 安装副本已清除。

## 实际验收

- 用量统计：217 项合成测试；独立轻安装、压缩日志、增量查询、14 张 PNG、MP4 和 Tk 更新/取消通过。正式系统包再次核验。原缓存原生一致性备份后真实增量成功，原事件与会话身份全部保留；原缓存、设置、报告和三项媒体 SHA 不变。
- AIGC：新旧中文十模型、英文默认标注、两组 raw、Desklib/CoCoDet 的 token、窗口、profile、分数及标签对照通过；预设浮点 abs/rel=1e-4，整数和 token 严格相等。Neo/Falcon 统计路径的代表样本分数、窗口和 revision 一致，GPU/CPU 混合加载、临时文件清理有实证。普通 CLI 默认缓存的完整十模型标注也已通过。
- TTS：中文 CosyVoice3、英文 Kokoro 的 CPU/GPU 实际合成通过；GPU 验证全块复用、损坏单块重建和设置冲突保护。正式机器包另合成 1178 汉字的中英混读长文，12 块完整覆盖，得到 264.22 秒 MP3，自动 QA、ffprobe 及独立完整解码通过。
- 调用方：huangzetao 的既有 adapter 实际生成完整检测报告及 MP3；dissertation 两个原 skill 发现链接保留，安装可见性及文档合同通过。两项目受影响文档、导航、镜像和差量阅读检查通过。
- 调度：机器安装 AIGC 的 CPU、HTTP 8766 与 embedding 8765 并存、执行超时回收、端口释放及一次重启恢复通过。所有最终功能作业均确认已知进程及 Condor 历史回收，未改变机器预算。

## 继续开发与恢复

原源码及现有 Codex project 保持原位：

- `D:/project/trifles/20260829 codex usage`
- `D:/project/20260928 aigc detect`
- `D:/project/20261004 text to speech`

继续在对应项目改源码、验证、构建 wheel，再更新同一系统 Python 中的相应包。更新一个工具无需重新发布其余两个；正式运行验收从源码目录之外执行。机器级 site-packages 的写入需要 Windows 管理员权限。没有修改 Codex 应用设置、项目根或聊天。

用量源码提交为 `edda407`；huangzetao 原 master 的四份安全 tracked 文件提交为 `3495739`，dissertation devDoc main 为 `22a876e`。AIGC 原有未提交工作保留，迁移文件已应用；TTS 原无 Git，未擅自初始化，其固定 vendor 已可入库并按原字节保留。huangzetao 原 untracked handoff 正文保留工作树，本机配置仍忽略；未推送或创建远程仓库。

选留原证、源文件备份和模型移动回执在 [本机迁移原证](../../../artifacts/runs/20261113-tool-migration/)。离线 wheel、哈希/来源、约束、管理员安装日志及用户配置回执在 `D:/AgentTools/installers/20261113-three-tools/`。旧环境、原缓存及 invalid 备份保留恢复定位，不再作为日常正式运行入口。

## 验证边界

语音尚未人工听审或逐字 ASR 校对，自动 QA 不证明发音和自然度；新旧公开样例 WAV 在迁移原证的 `audio/`。CPU 验证为短句，完整长文在 GPU 上验证。显存测量区分 Torch allocator 与含背景的全设备采样，不宣称取得独立进程树全部显存峰值或硬隔离。

当前 Windows Condor 槽账户需要显式可写缓存及实际执行账户名称；系统 Pydantic 的现有 `logfire-plugin` 在无 home 账户下失败，HTTP/TTS 验收仅在作业环境中禁用该无关插件，未改系统包、ACL 或冒充私人账户。basePack 使用中发现的两项回收/等待观察问题及自动记忆维护余项见 [进度记录](progress.md)。
