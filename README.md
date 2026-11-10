# basePack

basePack 为 agent 提供项目局部记忆、共享计算资源协调，以及可独立使用的协作和文件结构技能。

| 能力 | 用途 | 按需准备 |
| --- | --- | --- |
| 项目记忆 | 保存摘要、原文块、图片与关系，查询已发布知识，独立维护更新 | Python 3.13+ 客户端、每项目独立的 SurrealDB 4、CPU/CUDA 共享编码服务 |
| 资源协调 | 多项目复用图文 embedding，提交和查询普通重任务 | 编码服务支持 CPU/CUDA；作业使用 HTCondor |
| agent-team | 按任务选择单人、直接协作或分层团队 | 支持 skills 与订阅 agent 的宿主 |
| file-structure | 按内容职责和生命周期建议项目布局 | 支持 skills 的宿主 |
| engineering-judgment | 判断设计、错误处理、兼容和操作流程中的契约、职责与必要负担 | 支持 skills 的宿主 |

当前源码为 **0.7.1 开发版**，面向 Windows、Python 3.13+。理解材料、建图和评分由宿主订阅 agent 完成，basePack 不要求另配 LLM API。安装和使用按所选功能准备设施，开发验证与环境记录见 [整改进度](devDoc/tasks/20261110-rectification/progress.md)。

**basePack 当前仍处于开发过程中，现阶段的实际使用同时作为测试样本。应记录使用过程中遇到的问题，作为后续改进的依据。**

## 安装轻量客户端

先安装 Git 与 Python 3.13 或 3.14，在 PowerShell 中执行（示例使用 3.13）：

```powershell
git clone https://github.com/YS-Pan/basePack.git
Set-Location basePack
py -3.13 -m venv .venv
$python = (Resolve-Path '.venv/Scripts/python.exe').Path
& $python -m pip install './experiments/20261106-basepack'
& $python -c "from importlib.metadata import version; print(version('basepack'))"
```

Python 包在 `experiments/20261106-basepack`，从仓库根安装时需指定该目录。以上只安装轻量客户端；项目记忆通过配置连接共享模型服务，模型依赖装在服务环境中。通用 skills 可独立使用。这个虚拟环境随当前 clone 保存，移动或删除它后应在新位置重建客户端并更新项目入口。

历史发布包可从 [GitHub Releases](https://github.com/YS-Pan/basePack/releases) 获取；本轮源码的普通 wheel 构建见 [路线 README](experiments/20261106-basepack/README.md#开发检查与构建)。已有项目先按 [升级步骤](experiments/20261106-basepack/docs/setup-project.md#版本升级) 备份并更新入口。

## 启用项目记忆

1. 按 [项目接入](experiments/20261106-basepack/docs/setup-project.md) 创建最小机器配置，为自己的项目运行 `init`。新项目默认 `vector`，也可选择 `hybrid`。`doctor` 默认只检查 core。
2. 按 [项目 SurrealDB](experiments/20261106-basepack/docs/administrator.md#项目-surrealdb) 安装数据库，为该项目选择独立目录、端口和密码，启动后检查 `/ready`。
3. 按 [共享模型部署](experiments/20261106-basepack/docs/administrator.md) 准备 CPU 或 CUDA 编码服务，在机器配置中填写 endpoint，完成一条编码冒烟。记忆不要求 HTCondor。
4. 按 [凭据加载步骤](experiments/20261106-basepack/docs/setup-project.md#凭据与新-shell-接续) 运行 `memory init`、`memory brief`，再执行 [最小读写闭环](experiments/20261106-basepack/docs/memory.md#最小闭环示例)。启用后，新 shell 和新聊天沿生成的 `AGENTS.md → .basepack/instructions.md` 入口加载凭据并接续。

各项目的配置、知识、数据库、密码与本机入口保存在各自的忽略目录中，**项目记忆不随本仓库源码分发**。新 clone 通过 `init` 生成自己的配置；恢复已有知识时使用对应项目的备份。

## 独立 skills

[agent-team](skills/agent-team/SKILL.md)、[file-structure](skills/file-structure/SKILL.md) 和 [engineering-judgment](skills/engineering-judgment/SKILL.md) 可以独立使用，无需安装 Python 包或数据库。将需要的完整技能目录复制到目标项目的 `.agents/skills/`。在本仓库根执行以下命令，目标项目应尚无对应同名技能：

```powershell
$repo = (Get-Location).Path
$skillRoot = Join-Path '<absolute-target-project>' '.agents/skills'
New-Item -ItemType Directory -Force -Path $skillRoot | Out-Null
Copy-Item -LiteralPath (Join-Path $repo 'skills/agent-team') -Destination $skillRoot -Recurse
Copy-Item -LiteralPath (Join-Path $repo 'skills/file-structure') -Destination $skillRoot -Recurse
Copy-Item -LiteralPath (Join-Path $repo 'skills/engineering-judgment') -Destination $skillRoot -Recurse
Get-ChildItem -LiteralPath $skillRoot -Filter SKILL.md -Recurse
```

可明确要求读取对应的 `SKILL.md`，或用 `$agent-team`、`$file-structure`、`$engineering-judgment` 调用。其它宿主使用其技能安装方式。本仓库开发机的 `.agents/skills` 联接指向 Git 中的 `skills/` 维护源。engineering-judgment 保留独立使用，效果通过长期真实反馈维护。

wheel 包含程序、配置与入口模板、记忆 schema 和 `memory guide` 定位的记忆 skill；三项通用 skills、[资源 skill](experiments/20261106-basepack/skills/resources/SKILL.md) 与仓库示例从源码目录获取。

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

本项目自有源码、skills 和文档采用 [MIT 许可证](LICENSE)。第三方依赖和模型遵循各自许可，图文模型声明见 [Qwen 使用声明](experiments/20261106-basepack/src/basepack/embedding/NOTICE.Qwen3-VL-Embedding.txt)。
