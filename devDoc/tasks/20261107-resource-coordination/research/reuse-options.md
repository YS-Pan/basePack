# 现成库与本地服务的精简调查

2026 年 11 月 8 日。用户明确以尽量少实现和维护自己的代码衡量简洁，允许另装库/软件及适度行为变化；运行不新增联网模型 API，理解与评分继续使用 Codex 订阅。采用决定和实施条件只维护在 [R9](../plan.md#r9-复用优先的资源实现)，本页保留本轮官方资料与静态核对依据。

## 优先复用项

| 候选 | 核实到的能力与边界 | 一手依据 |
| --- | --- | --- |
| Sentence Transformers | 官方 Qwen3-VL-Embedding-2B 集成支持文字、图片与图文；本机同 revision 已有 modules/Pooling 配置，可复用权重。默认截断和 FP16 归一化需显式对齐或更新语义身份 | [Qwen 模型卡](https://huggingface.co/Qwen/Qwen3-VL-Embedding-2B)、[多模态集成](https://huggingface.co/blog/multimodal-sentence-transformers)、[预处理](https://github.com/huggingface/sentence-transformers/blob/v6.2.0/sentence_transformers/base/modules/transformer.py)、[归一化](https://github.com/huggingface/sentence-transformers/blob/v6.2.0/sentence_transformers/base/modules/normalize.py) |
| LitServe | 提供 HTTP、模型 worker、队列、可选跨请求合批与健康检查；模型计算可调用 Sentence Transformers。0.2.19 的 timeout 只限排队，开始推理后可继续完成 | [入门](https://lightning.ai/docs/litserve/get-started)、[0.2.19 服务实现](https://github.com/Lightning-AI/LitServe/blob/v0.2.19/src/litserve/server.py)、[同步循环](https://github.com/Lightning-AI/LitServe/blob/v0.2.19/src/litserve/loops/simple_loops.py) |
| Shawl | 便携 Windows 服务包装器，支持日志、退出策略和 Job Object 进程树；托管唯一生产服务可替代自写 supervisor。管理员停止服务与子程序退出后的重启分开，实际账户的回收仍需验收 | [官方说明](https://github.com/mtkennerly/shawl)、[参数](https://github.com/mtkennerly/shawl/blob/master/docs/cli.md)、[服务实现](https://github.com/mtkennerly/shawl/blob/master/src/service.rs) |
| Tomli-W、psutil、pywin32 | 分别替代自写 TOML writer、Toolhelp 枚举和仍需保留的 Job Object ctypes 样板；服务软件已承担的职责不重复引入包装 | [TOML 写入](https://docs.python.org/3.13/library/tomllib.html)、[psutil](https://psutil.io/api/)、[win32job](https://github.com/mhammond/pywin32/blob/main/win32/src/win32job.i) |
| uv | 已有依赖锁、同步与 PyTorch CUDA 发行源配置，可减少环境安装的私有实现；不直接对现有共享系统 Python 做清理式同步 | [锁与同步](https://docs.astral.sh/uv/concepts/projects/sync/)、[PyTorch](https://docs.astral.sh/uv/guides/integration/pytorch/) |

## LitServe 的实施边界

以下静态核对固定在已发布 0.2.19，实施时复核选定发行版；不是本机运行结果。

- [batch/unbatch](https://github.com/Lightning-AI/LitServe/blob/v0.2.19/src/litserve/api.py#L254) 处理跨请求合批；单次 encode 内的批处理由 Sentence Transformers 完成。列表请求再次合批时，展平与结果拆分仍需按输入结构适配，批次请求数不等于 token 或像素预算。
- [Windows 接入](https://github.com/Lightning-AI/LitServe/blob/v0.2.19/src/litserve/server.py#L1487) 使用 API 线程，模型仍在独立 spawn worker，另有 Manager 进程。一个推理 worker 不等于整个服务只有一个进程；默认 manager.Queue 无界，不能据此宣称已提供 GPU 队列容量准入。
- worker 死亡后可通过 [restart_workers=True](https://github.com/Lightning-AI/LitServe/blob/v0.2.19/src/litserve/server.py) 重建进程，不自动重做失败推理；HTTP 客户端超时也不代表服务端计算已停止。
- [Windows 停机问题 #684](https://github.com/Lightning-AI/LitServe/issues/684) 仍有未关闭报告，涉及 API 线程的 terminate 与调试停止。它提示需要核选定版本并验证正常停止、主进程异常退出和整个进程树回收，不证明本机已经复现。

## 备选与未采用项

- [Xinference](https://inference.readthedocs.io/en/latest/models/builtin/embedding/qwen3-vl-embedding-2b.html) 明确支持当前图文模型，并有 Windows 与本地模型部署路线，可在主线受阻时比较。其 [embedding 实现](https://github.com/xorbitsai/inference/blob/main/xinference/core/model.py) 与 LLM abort 合同不同，不据此承诺旧请求级取消。
- [vLLM](https://docs.vllm.ai/en/stable/models/pooling_models/embed/) 支持该模型，但 [不支持原生 Windows](https://docs.vllm.ai/en/stable/getting_started/installation/gpu/)，默认图像预处理也有差异；本轮不为它先迁移 WSL/Docker。Infinity v3 已有 [该图文模型支持](https://github.com/michaelfeil/infinity/blob/main/libs/infinity-v3/docs/supported-models.md)，主要交付与验证在 Linux/Docker，另有 [许可边界](https://github.com/michaelfeil/infinity/blob/main/libs/infinity-v3/LICENSING.md)。
- TEI、Ollama、LM Studio 的常见文本 embedding 能力不代表当前 exact 图文模型接口已经适配；本轮未核得足够直接替换证据，不扩写适配它们。
- [HTCondor Python bindings](https://htcondor.readthedocs.io/en/25.x/apis/python-bindings/install.html) 可以减少 CLI 胶水，但本机现有二进制为 cp39，Python 3.13 只读导入失败于 classad2_impl。新匹配版本仍可另评；现阶段保留 CLI 与真实事故所需的 UTF-8 参数桥。
- [RPyC](https://rpyc.readthedocs.io/en/stable/tutorial/tut3.html#shared-service-instance) 可用共享实例实现很短的 Python 服务，但需明确按值传输，避免向量变成远程代理；[FastAPI](https://fastapi.tiangolo.com/advanced/events/) 可在 lifespan 加载共享模型。两者在放宽后的合同下都可行，不能沿用旧取消/空闲退出要求排除；本轮仅作比较依据，采用决定见 R9。
- Typer、Pydantic/Dynaconf 等额外 CLI/配置框架暂不优先引入；所选服务栈已有依赖与功能直接复用。

## 观察与限制

只读统计当前产品 Python 为 24 文件、1883 行、1661 非空行（含注释，不含测试和模板）；embedding 占 837 非空行。当前 Condor 普通显存池固定，worker 空闲退出不会自动扩大它；允许模型常驻可减少自写生命周期状态，仍需验证实际峰值与其他任务并存。

本轮只查官方资料、源码、目录及现有绑定导入；未安装候选、运行新模型服务或测量性能，支持列表不等于本机行为验收。最短原型在实现时重新核选定发行版本，不长期维护多后端、兼容协议或第二套调度器。记忆 CLI/MCP 与底座的小型比较归 [P0](../../20261106-memory-system/plan.md#p0-收敛边界和运行入口)，不把未实现记忆计为已删代码。
