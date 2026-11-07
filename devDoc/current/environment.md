# 开发环境核验

观测时间：2026-11-06 23:34:19（北京时间，UTC 15:34:19）。这是当前开发进程的一次只读快照；仓库尚无依赖声明，最低兼容版本尚未确定。

## 实测入口与结果

| 对象 | 本次观察 |
| --- | --- |
| Shell / 系统 | PowerShell Core 7.6.9；系统报告 `Microsoft Windows 10.0.26300` |
| Python | `C:\Program Files\Python313\python.exe`，3.13.17，64-bit；本次使用系统解释器，`sys.prefix == sys.base_prefix` |
| Python Launcher | `py --list-paths` 仅列出上述 Python 3.13 |
| 仓库状态 | 无 `src/`、`pyproject.toml`、`tests/`、`.venv/`、`venv/`、`.memory/` |
| 共享资产 | `D:\AgentTools` 可见 `models/`、`profile/`、`state/` |
| HTCondor | CLI 位于 `C:\condor\bin`；`condor_version` 成功，版本 25.4.0 |
| 状态与队列 | `condor_status -json`、`condor_q -json` 均退出 1：当前进程的 `CONDOR_CONFIG` 环境变量及注册表未提供配置源 |
| GPU 元数据 | `nvidia-smi --query-gpu=name,memory.total --format=csv,noheader` 返回 RTX 4060 Ti、16380 MiB |

本次 Condor 查询尚未进入认证阶段；与 [早期调查](../work/20261106-rebuild/research/sources.md#agenttools-当前可复用部分) 的 `AUTHENTICATE:1005` 是不同观测，不能据此判定调度服务是否可用。

2026-11-07 资源协调计划期间定向只读复核：当前进程、用户和机器环境变量中的 `CONDOR_CONFIG` 均为空，但 `HKLM:\SOFTWARE\Condor` 的同名值已为 `C:\condor\condor_config`，该文件与 `.local` 均存在。上表是 11 月 6 日快照；本次未重跑 Condor 查询，注册表入口可见不代表当前认证、队列或 GPU 作业已通。后续按 [资源专项 R0](../work/20261106-rebuild/resource-coordination-plan.md#r0-复用准备与预算标定) 实测。

## 可见模型版本标识

以下仅核对目录名称，未校验权重内容或加载模型：

| 模型 | revision 目录名 |
| --- | --- |
| `BAAI/bge-reranker-v2-m3-int8` | `6f5ff65298512715a1e669753bc754d2bc8f367b` |
| `intfloat/multilingual-e5-large` | `ac6781cd1cf88b8306a536d7c9d18a5bd57cc14b` |
| `Qwen/Qwen3-Embedding-4B` | `5cf2132abc99cad020ac570b19d031efec650f2b` |
| `Qwen/Qwen3-VL-Embedding-2B` | `9f2f7e710d6d81056aa5c0a4f04764fec6bb7bda` |
| `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | `faf4aa4225822f3bc6376869cb1164e8e3feedd0` |

## 核验方法与限制

使用目录存在性检查、`Get-Command`、Python 标准库读取解释器信息，并对三条 Condor 命令、GPU 元数据查询及 Launcher 列表各执行一次只读查询；外部查询设 8 秒超时，均提前返回。未安装依赖、设置环境变量、加载模型、修改服务或提交计算任务。

模型可加载性、GPU 推理、实际队列和资源准入、项目安装及产品测试尚未验证。P0 接手先核配置来源，再验证资源接口；公共代码通过配置或探测定位共享资产，本页机器路径仅记录观测。

2026-11-07 安装布局规划期间只读检查：当前系统 Python 的 sysconfig purelib 为 `C:\Program Files\Python313\Lib\site-packages`；find_spec 可定位 basic_memory，未发现 basepack/context_memory。旧安装器仍复制 `.context-memory/app`，详细依据与新部署目标见 [路径布局计划](../work/20261106-rebuild/deployment-layout-plan.md#从旧方案到本方案)。本次未安装包、写入 AgentTools 配置或运行模型。

## 项目 skill 的本机入口

2026-11-07：以下两个 skill 使用项目级发现入口，通过 junction 指向仓库维护源，仅在本项目及子目录中自动发现；二者均无用户级注册，原 `~/.codex/skills/project-layouts` 联接已移除。[Codex 官方作用域说明](https://learn.chatgpt.com/docs/build-skills#where-codex-loads-local-skills) 区分项目级与用户级入口。

| Skill | 维护源 | 本机发现入口 |
| --- | --- | --- |
| `project-layouts` | [SKILL.md](../../skills/project-layouts/SKILL.md) | `.agents/skills/project-layouts` |
| `agent-team` | [SKILL.md](../../skills/agent-team/SKILL.md) | `.agents/skills/agent-team` |

本机联接由 `.gitignore` 排除，不重复保存源码。仓库换路径或新检出时，如需在技能列表中自动发现，可从仓库根目录首次建立项目级入口：

```powershell
New-Item -ItemType Directory -Force -Path '.agents/skills' | Out-Null
foreach ($skillName in @('project-layouts', 'agent-team')) {
    $skillSource = (Resolve-Path -LiteralPath "skills/$skillName").Path
    New-Item -ItemType Junction -Path ".agents/skills/$skillName" -Target $skillSource | Out-Null
}
```

AGENTS.md 仍直接引用仓库维护源；skill 本身不依赖本机绝对路径，也不需要安装 Python 包或加载模型。

此前 `project-layouts` 作用域调整的四份源码 SHA-256 保持不变，原始发现结果留在忽略目录 `.work/project-layouts-scope/`。本次英文版与 `agent-team` 注册后，实际 `skills/list` 在项目根目录及 `devDoc` 子目录均返回两个 skill 的 `scope=repo`、`enabled=true` 和英文元数据；项目外用户目录均未发现，三处均无发现错误。原始结果记录在 `.work/skills-english/`。
