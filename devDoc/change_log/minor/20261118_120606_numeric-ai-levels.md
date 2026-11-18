# AI 配置改用数字档位

项目 AI 配置使用正整数 `default_level` 和 `retrieval_level`，各档通过 `[ai.levels.<n>]` 定义。初始日常 3 档、检索 1 档，维护协调默认 2 档、阅读 1 档。CLI 显式选档用 `--level`，派工结果报告整数 `level`。现行文档、托管入口模板和随包／独立技能已同步。旧项目按 [AI 档位迁移](../../../experiments/20261106-basepack/docs/project-config-maintenance.md#ai-档位迁移) 更新配置和入口，继续使用原模型与推理强度。

源码验证 698 项通过、213 项跳过，主工作区配置和记忆入口定向验证 288 项通过。实际安装 0.18.6 后重新运行 `config ai` 和 `config ai --purpose retrieval`，分别解析到 3 档 `gpt-6.2-sol / ultra`、1 档 `gpt-6-luna / max`，两项均符合迁移前的实际结果。四档显式选取、随包 guide、托管入口及 `memory brief` 均已检查。见 [部署合同](../../system/deployment.md)。
