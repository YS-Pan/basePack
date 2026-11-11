# basePack 项目入口

本项目配置为 `$config`，运行 Python 为 `$python`。从项目根运行：

```powershell
& '$python' -m basepack --config '$config' config show
```

首次启用记忆时，若 `[memory.codex]` 绑定仍为空或 `registry_complete=false`，由 Codex 宿主读取当前聊天所属 projectId 和 `list_projects` 的完整注册根，自动把 projectId、其它项目根清单及 `registry_complete=true` 写入本项目配置。宿主发起 `init` 时可直接使用 `--codex-project-id`、可重复的 `--codex-other-project-root` 和 `--codex-registry-complete` 传入；无需逐聊天配置。每次维护预检前刷新完整注册根清单。非 Codex 宿主或元数据不可取得时保留缺失状态并说明聊天覆盖缺口，文件记忆仍可使用。

basePack 仍在开发，实际使用也作为测试样本。发现问题时，沿本项目已有约定及时记录现象、版本、最小复现条件和处理状态，证据去除凭据与私人资料；修复后补验证结果。同时形成可复制的 Issue 草稿，注明本地记录位置与最小复现，反馈到 [basePack Issues](https://github.com/YS-Pan/basePack/issues)。由用户提交，或取得用户明确授权后再提交。
