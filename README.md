# basePack

basePack 为 agent 提供项目局部记忆、共享计算资源协调，以及可独立使用的协作和文件结构技能。

| 能力 | 用途 | 按需准备 |
| --- | --- | --- |
| 项目记忆 | 保存摘要、原文块、图片与关系，启动时提供线索，按原文变化维护依据 | Python 3.13 客户端、每项目独立的 SurrealDB 4；文字检索可独立运行 |
| 资源协调 | 多项目复用图文 embedding，提交和查询普通重任务 | 图文编码使用 NVIDIA CUDA 服务；作业使用 HTCondor |
| agent-team | 按任务选择单人、直接协作或分层团队 | 支持 skills 与订阅 agent 的宿主 |
| file-structure | 按内容职责和生命周期建议项目布局 | 支持 skills 的宿主 |

当前版本为 **0.6.3 开发版**，支持范围为 Windows、Python 3.13。理解材料、建图和评分由宿主订阅 agent 完成，basePack 不要求另配 LLM API。纯文字路径已有本机独立环境与新数据库实测；图文和作业的 [既有实测](devDoc/archive/20261107-resource-coordination/r9-result.md) 使用作者机设施（RTX 4060 Ti 16 GB、CUDA 12.8）。完整新机资源部署路径已提供，仍待独立机器验收；更广泛的质量、性能和费用收益仍待评估，见 [交付与待验范围](devDoc/tasks/20261106-rebuild/progress.md)。

**basePack 当前仍处于开发过程中，现阶段的实际使用同时作为测试样本。应记录使用过程中遇到的问题，作为后续改进的依据。**

## 安装轻量客户端

先安装 Git 与 Python 3.13，在 PowerShell 中执行：

```powershell
git clone https://github.com/YS-Pan/basePack.git
Set-Location basePack
py -3.13 -m venv .venv
$python = (Resolve-Path '.venv/Scripts/python.exe').Path
& $python -m pip install './experiments/20261106-basepack'
& $python -c "from importlib.metadata import version; print(version('basepack'))"
```

Python 包在 `experiments/20261106-basepack`，从仓库根安装时需指定该目录。以上只安装轻量客户端；使用文字记忆、通用 skills 时无需安装模型依赖。这个虚拟环境随当前 clone 保存，移动或删除它后应在新位置重建客户端并更新项目入口。

## 先试文字记忆

1. 按 [项目接入](experiments/20261106-basepack/docs/setup-project.md) 创建最小机器配置，为自己的项目运行 `init`。新项目的 `memory.search_mode = 'text'`，`doctor` 默认只检查 core。
2. 按 [项目 SurrealDB](experiments/20261106-basepack/docs/administrator.md#项目-surrealdb) 安装数据库，为该项目选择独立目录、端口和密码，启动后检查 `/ready`。无需 embedding 或 HTCondor。
3. 按 [凭据加载步骤](experiments/20261106-basepack/docs/setup-project.md#凭据与新-shell-接续) 运行 `memory init`、`memory brief`，再执行 [最小读写闭环](experiments/20261106-basepack/docs/memory.md#最小闭环示例)。启用后，新 shell 和新聊天沿生成的 `AGENTS.md → .basepack/instructions.md` 入口加载凭据并接续。

各项目的配置、知识、数据库、密码与本机入口保存在各自的忽略目录中，**项目记忆不随本仓库源码分发**。新 clone 通过 `init` 生成自己的配置；恢复已有知识时使用对应项目的备份。

## 独立 skills

[agent-team](skills/agent-team/SKILL.md) 和 [file-structure](skills/file-structure/SKILL.md) 可以独立使用，无需安装 Python 包或数据库。以 Codex 为例，将完整技能目录复制到目标项目的 `.agents/skills/`；该目录是 [官方支持的本地发现位置](https://learn.chatgpt.com/docs/build-skills#where-codex-loads-local-skills)。在本仓库根执行以下命令，目标项目应尚无这两个同名技能：

```powershell
$repo = (Get-Location).Path
$skillRoot = Join-Path '<absolute-target-project>' '.agents/skills'
New-Item -ItemType Directory -Force -Path $skillRoot | Out-Null
Copy-Item -LiteralPath (Join-Path $repo 'skills/agent-team') -Destination $skillRoot -Recurse
Copy-Item -LiteralPath (Join-Path $repo 'skills/file-structure') -Destination $skillRoot -Recurse
Get-ChildItem -LiteralPath $skillRoot -Filter SKILL.md -Recurse
```

在目标项目的新聊天中核对技能列表，或明确要求读取对应的 `SKILL.md`；Codex CLI / IDE 可用 `$agent-team`、`$file-structure` 显式调用。未显示时重启宿主再核对。其它宿主使用其技能安装方式，也可直接提供完整技能路径。本仓库开发机的 `.agents/skills` 联接是本机发现入口，Git 中的维护源为 `skills/`。分层协作的完整质量对照尚未完成，具体模型由使用者宿主与项目配置决定。

wheel 包含程序、配置与入口模板、记忆 schema 和 `memory guide` 定位的记忆 skill；两项通用 skills、[资源 skill](experiments/20261106-basepack/skills/resources/SKILL.md) 与仓库示例从源码目录获取。

## 文档与反馈

| 入口 | 内容 |
| --- | --- |
| [路线 README](experiments/20261106-basepack/README.md) | 按能力使用、开发、构建和测试 |
| [项目接入](experiments/20261106-basepack/docs/setup-project.md) | 配置、凭据、新 shell 接续、升级和移动 |
| [记忆使用](experiments/20261106-basepack/docs/memory.md) | 首建、检索、小批维护和备份 |
| [资源使用](experiments/20261106-basepack/docs/resources.md) | 图文 embedding、HTCondor 作业与 Python API |
| [管理员说明](experiments/20261106-basepack/docs/administrator.md) | 所需设施的官方来源、安装、服务和容量配置 |
| [AGENTS.md](AGENTS.md)、[实现概览](devDoc/system/overview.md) | 参与开发的规则与实现入口 |

使用问题先沿自己的项目记录约定保存现象、版本、最小复现条件与处理状态；修复后补验证结果。按 [问题反馈格式](experiments/20261106-basepack/docs/setup-project.md#问题记录与反馈) 形成可复制的 Issue 草稿，去除凭据和私人资料后，由使用者提交到 [GitHub Issues](https://github.com/YS-Pan/basePack/issues)，或明确授权 agent 提交。

当前尚未授予本项目的开源复用许可。第三方依赖和模型遵循各自许可，图文模型声明见 [Qwen 使用声明](experiments/20261106-basepack/src/basepack/embedding/NOTICE.Qwen3-VL-Embedding.txt)。
