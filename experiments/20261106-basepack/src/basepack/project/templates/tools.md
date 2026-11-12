<a id="ai-resources"></a>
## AI 与资源

宿主分配普通 AI 工作前，用本机 Python/配置前缀运行 `config ai` 解析日常默认，或 `config ai --tier tier2` 显式选档；按返回的 `model` 与 `reasoning_effort` 派工。记忆维护使用返回的 `worker`；检索使用 `memory retrieve --question '<业务问题>'`，默认全项目、6000 字符。`--scope` 仅为项目相对路径前缀，业务限制写入问题。命令只准备派工，宿主按返回名称、模型和推理强度实际创建 worker、接收最终内容后确认交付；检索不取得维护所有权。[检索派工与交付](<$skill#retrieve-in-one-delegation>)。

安装、升级或维护本项目 basePack 配置时，先读 [项目配置维护要点](https://github.com/YS-Pan/basePack/blob/main/experiments/20261106-basepack/docs/project-config-maintenance.md)，按受影响的变更同步；普通业务沿现有配置执行。

在其它工作目录调用时，显式传配置绝对路径；不搜索父目录。首次接入运行 `doctor`（默认 core）；选用图文或作业能力时，再显式运行 `doctor --facility embedding` 或 `doctor --facility condor`。资源调用按安装包的 `embed` 与 `jobs` 帮助使用。共享 embedding 由机器服务托管，客户端只连接；`embed --timeout` 只结束等待，已开始的共享推理仍可继续。服务未运行时由机器管理员启动。

配置、数据库、凭据、受管聊天/附件原件、控制与恢复必要回执留在配置指定的 `.basepack/` 位置。可重建的阅读包、batch、排名及一次性验证放项目根 `tmp/<任务或运行标识>/`；长期选留原证放根 `artifacts/runs/<运行标识>/`。仍在使用或发布未明的控制/回执保持稳定。清理前核 source_scope 与历史依据；新检出通过 `init` 重建本机入口，不复制其它项目状态。
