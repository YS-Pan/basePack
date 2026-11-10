# basePack 项目入口

本项目配置为 `$config`，运行 Python 为 `$python`。从项目根运行：

```powershell
& '$python' -m basepack --config '$config' config show
```

宿主分配 AI 工作前，用同一命令前缀运行 `config ai` 解析日常默认，`config ai --purpose retrieval` 解析多轮检索、筛选与重排默认，或 `config ai --tier tier2` 显式选档；按返回的 `model` 与 `reasoning_effort` 派工。档位映射只在项目配置 `[ai]` 维护。

在其它工作目录调用时，显式传该配置的绝对路径；不搜索父目录。首次接入运行 `doctor`（默认 core）；选用图文或作业能力时，再显式运行 `doctor --facility embedding` 或 `doctor --facility condor`。资源调用按安装包的 `embed` 与 `jobs` 帮助使用。共享 embedding 由机器 Windows 服务托管，客户端只连接；`embed --timeout` 只结束等待，已开始的共享推理仍可继续。服务未运行时由机器管理员启动。

项目配置、知识与工具产物保留在本项目 `.basepack/`，业务原件和显式导出按业务路径保存。新检出后通过 `init` 重建本机配置与本入口，不复制其它项目的知识或任务状态。

首次启用记忆时，若 `[memory.codex]` 绑定仍为空或 `registry_complete=false`，由 Codex 宿主读取当前聊天所属 projectId 和 `list_projects` 的完整注册根，自动把 projectId、其它项目根清单及 `registry_complete=true` 写入本项目配置。宿主发起 `init` 时可直接使用 `--codex-project-id`、可重复的 `--codex-other-project-root` 和 `--codex-registry-complete` 传入；无需逐聊天配置。每次维护预检前刷新完整注册根清单。非 Codex 宿主或元数据不可取得时保留缺失状态并说明聊天覆盖缺口，文件记忆仍可使用。

basePack 仍在开发，实际使用也作为测试样本。发现问题时，沿本项目已有约定及时记录现象、版本、最小复现条件和处理状态，证据去除凭据与私人资料；修复后补验证结果。同时形成可复制的 Issue 草稿，注明本地记录位置与最小复现，反馈到 [basePack Issues](https://github.com/YS-Pan/basePack/issues)。由用户提交，或取得用户明确授权后再提交。
