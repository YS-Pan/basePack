# AgentTools 迁移进度

2026-11-13。**技术迁移、正式安装与已知调用方切换完成。** 结果及继续开发方法见 [result.md](result.md)，原计划见 [plan.md](plan.md)。语音主观听审未做，已提供公开样例；这与自动 QA、完整覆盖和解码检查分别记录。

## 已交付

- 三个独立轻量包：用量统计 0.2.0、AIGC 0.10.0、TTS 1.2.0。各自声明可选功能依赖，不引入三工具公共业务核心或 basePack 反向依赖。代码正式安装到系统 Python 3.13 的机器 site-packages，无新增常驻工具虚拟环境。
- 用户已选择 `D:/AgentTools`。AIGC 179 文件共 55,458,054,087 B、TTS 25 文件共 4,769,138,640 B 同卷归集至各自 models 子目录，移动前后清单、长度、时间与 manifest 哈希一致，原源码保留小 manifest。准备入口核验复用通过，没有下载新模型。
- 用量状态归集至 `D:/AgentTools/state/codex-usage`。SQLite 原生一致性备份及 quick_check 通过；真实增量保留全部旧事件和会话，新增 7784 个事件，解析失败 0。原缓存、设置、32 份报告、三项媒体 SHA 不变；invalid 备份保留原恢复位置。
- 普通 user-site 安装对 Condor 独立槽账户返回 WinError 5，未通过修改 ACL 或用户变量冒充账户。离线机器包已预检，用户执行管理员步骤后新增 97 包、原 232 份全局版本保留，pip check 通过；本任务的旧 user-site 副本已卸载。普通桌面与宿主两种配置均指向已选 D 盘位置。
- 原三个源码目录与 Codex project 保持原位。按快照校验、备份后应用用量 33 项、AIGC 38 项、TTS 41 项，另补一份 Git 字节保留规则，避免未来 checkout 换行转换破坏固定源码哈希。固定 vendor 源码、许可与默认小参考录音可入独立 Git 仓库；旧项目 venv 安装/修复入口明确退役。未操作 Codex 应用设置、项目根或聊天。

## 实际验证

- 用量完整合成测试 217 通过；独立轻安装、zstd、查询/增量、PNG/MP4 和 Tk 更新/取消通过。正式系统包又从无关 cwd 完成查询、14 张 PNG、MP4、GUI 检查，未再扫描真实日志或改变真实报告。
- AIGC 完整候选回归 183 通过，后续真实缺陷有定点回归。22 个 tokenizer 在原 4.57.6 与系统 5.22.1 上输入/窗口一致；新旧分类器默认中英文标注、raw、Desklib/CoCoDet，及 Neo/Falcon 统计样本对照通过。浮点 abs/rel=1e-4，整数与 token 严格比较；模型/profile 保持。统计模型 GPU/CPU 混合加载、scratch 清理有实证。
- 普通 AIGC CLI 默认十模型标注 14384.0 的完整报告通过，Torch reserved 峰值 6,891,241,472 B；不能拿数值对照脚本逐模型清缓存的低峰值替代实际 CLI 预算。正式机器包 CPU CLI、HTTP 8766 与 embedding 8765 并存、执行超时回收及一次重启恢复通过。
- TTS 原 3.12 的 31 项契约/小模型检查通过；新依赖、Transformers 5 缓存 mask、私有 YAML loader、资源与缺依赖分支有定点回归。3.13 中文/英文 CPU 与 GPU 实际合成通过；GPU 全复用、坏块重建、设置冲突保护通过。正式机器版 14392.0 将 1178 汉字/1337 规范化字符完整覆盖为 12 块，生成 264.22 秒 MP3，自动 QA、ffprobe 和独立完整解码通过。
- huangzetao 的既有 adapter 实际 plan→run 生成中文十模型完整报告和英文 MP3；dissertation 的外部 skill 链接、安装可见性及文档合同通过。两项目导航、镜像与差量阅读最终 live/input complete=true、pending=0。没有读取论文正文或改变历史回执。
- 所有最终功能作业均确认已知进程及 Condor 历史回收；测试 HTTP 端口已释放，embedding 保持健康。未改变机器预算；本轮普通 GPU 池实际为 7164 MiB，旧 5116 MiB 是历史观察。

## 保存与 Git

长期原证与原文件备份在 `artifacts/runs/20261113-tool-migration/`；普通离线 wheel、哈希/来源、约束、安装计划/日志和用户配置回执在 `D:/AgentTools/installers/20261113-three-tools/`。临时构建、依赖探查和候选环境在 `tmp/20261113-tool-migration-impl/`，不作为唯一长期依据。

用量 main 提交 `edda407`，保留原三项媒体修改；huangzetao 保持原 master，安全四文件提交 `3495739`，其原 untracked handoff 正文和忽略的 local 配置保留工作树；dissertation devDoc main 提交 `22a876e`。AIGC 原有大量未提交的 0.9 工作树未被整批提交，迁移改动已应用并留备份；TTS 原无 Git，未自动初始化。没有远程推送。

## 使用中发现的条件与未决问题

TTS 3.13 不能仅放宽旧约束：HyperPyYAML 1.2.3 与系统 mdformat_frontmatter 2.2.0 的 ruamel 范围无交集，且 Loader 在 0.19.1 缺 max_depth。已用私有、带许可和来源哈希的原源码及公开 loader 参数适配，两代 ruamel 的标签/实际配置与最终语音通过；系统 Markdown 依赖没有降级。Kokoro/Misaki 固定上游提交支持 3.13，英文模型复用原已装文件重 pack，最终不依赖旧 venv。

Windows 槽账户缺普通 profile。验证显式定位可写缓存及实际执行账户名称；系统现有 Pydantic logfire 插件在无 home 下失败，HTTP/TTS 作业内设置 `PYDANTIC_DISABLE_PLUGINS=logfire-plugin` 后通过，未全机禁用插件。人工听审、逐字 ASR 和完整 CPU 长文未做；长文在 GPU 验证。Torch allocator 与含背景的全设备显存采样不能冒充独立进程树全部显存或硬隔离。

资源客户端 0.12.0.dev1 两项反馈保留待所属后续处理：`jobs wait 14367.0 --timeout 45` 的内部 condor_wait 约 4.04 秒触发 subprocess.TimeoutExpired，不能当作原作业失败或授权重提；失败作业 14368.0 的 PID 被后续进程复用，工具仅按 PID 检查导致 cleanup_confirmed=false。已证旧 PID 退出、该次在模型加载前失败，未把工具未确认误报为确认。

## 自动记忆维护收尾

初始 brief 曾在沙箱连接 18080 被拒；以正常用户恢复原数据库后取得 3 条 mandatory。自动维护早期因 Codex App Server ACL、随后 embedding 停止失败，原错与控制收尾保留。用户管理员启动 BasepackEmbedding 后健康恢复 200。

最新自有 run `d55e5a71470845d2b95614621eb32c7b` 全项目扫描 1248 个 Git 来源，固定语义回执处置 42/45（35 initial、7 existing-change），发布成功；3 条原始聊天捕获缺口不可恢复，重复 member ID 产品入口反馈仍 pending。协调者已结束，stop 后 publications=[]，release 成功，最终 owner=null。该后台维护没有被当作完整记忆审计，也不扩成本次业务验收。
