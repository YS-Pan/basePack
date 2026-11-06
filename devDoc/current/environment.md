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
