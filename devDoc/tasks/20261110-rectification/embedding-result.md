# CPU/CUDA embedding 与 Python 兼容结果

本分支实现机器设备自动选择、CPU/CUDA 共用语义身份和具名安装依赖；轻客户端解除无依据的 Python 3.14 上限。正式共享服务、稳定客户端和正式项目数据库未在本分支升级或重启。最终发行版本、产品文档及共享安装由主 owner 整合。

## 已实现合同

- 机器模板默认 `device='auto'`：Torch 可用 CUDA 时选择 `cuda:0`，否则选择 CPU。显式 `cpu`、`cuda:0` 继续有效。CPU 不调用 CUDA 初始化、显存分配器或 `nvidia-smi`；LitServe 接收已解析的 accelerator 和单设备配置。CUDA 才要求正的管理员显存预算，并应用既有 allocator 上限。真实加载、CUDA 初始化和推理异常继续沿原错抛出。
- 两个设备均使用既有 `float16`、固定模型 revision、Sentence Transformers 6.2.0 及相同前处理、pooling 和归一化。语义身份算法未改变；设备、地址和路径不参与身份。同模型合同可直接复用既有 0.5.0 共享服务向量。正常浮点差异、几乎同分换序和 K 边界互换不要求重算或量化。
- 新服务 `/info` 的 model 元数据增加实际 `device` 和 `dtype`。旧服务响应仍有效，客户端响应合同不变。`doctor --facility embedding` 检查模型入口并报告配置设备；实际设备和推理由服务启动及短冒烟确认。
- 新项目模板默认 `memory.search_mode='vector'`；search 与 brief 的任务相关通道由记忆分支统一使用该配置。文字项目仍可显式选择 `text`，没有查询内补建或静默文字回退。
- Python 元数据为 `>=3.13`，没有任意的新上限。`embedding` 保留共同栈；`embedding-cpu` 与 `embedding-cuda` 分别要求 `torch/torchvision` 的 `+cpu`、`+cu128` 版本，uv 的来源按 extra 选择且二者互斥。普通 wheel 的依赖元数据同样要求具名后端；pip 安装时使用对应官方 PyTorch 附加索引。未升级模型栈版本。

## 验证与证据

源码局部回归 62 项通过：设备选择、CPU 不初始化 CUDA、实际 LitServe CPU connector 不探测 `nvidia-smi`、原生 CUDA 错误保留、身份跨 CPU/路径复用、输入限制、HTTP 客户端、配置与模型准备。复用的 `tmp/r9-env` 安装元数据为旧 0.5.0，因此这次局部检查排除了 1 项安装版本锚点；最终普通 wheel 回归由主 owner 统一执行。

普通 wheel 的轻客户端闭环已在 CPython 3.13.17 和 3.14.10 通过：实际从临时环境 site-packages 导入，仅安装 basePack 与 psutil，在独立临时 SurrealDB 中完成 init、prepare/apply、文字 search、原文 read、neighbors 和 brief，结束后关闭该临时数据库。证据分别为 [3.13 闭环](../../../artifacts/runs/20261110-rectification-embedding/packaging/light313-run-v2/verification.json)和 [3.14 闭环](../../../artifacts/runs/20261110-rectification-embedding/packaging/light314-run/verification.json)。

`embedding-cpu` 的锁定非 editable 安装在 3.13.17、3.14.10 均通过依赖检查、完整 LitServe/Sentence Transformers/Qwen3-VL/PIL 导入、CPU 矩阵计算和 torchvision 原生 NMS；Torch 为 `2.10.0+cpu`、`torch.version.cuda=None`。`embedding-cuda` 的两个解释器组合完成官方 wheel 元数据核查和解析，实际 CUDA 模型推理沿用本机 3.13 既有服务。见[安装总证据](../../../artifacts/runs/20261110-rectification-embedding/packaging/packaging-verification.json)。CPU 3.14 全模型推理、CUDA 3.14 推理及 free-threaded Python 本次未验证。锁内 NetworkX 3.7 自身声明排除 3.14.1；这是该锁的具体依赖条件，不是轻客户端或 basePack 的统一版本禁令。

上述安装初版 wheel 为 0.6.4；实际 CPU 验收加载当前源码，其编码器与 identity 文件和普通 CPU wheel 逐字节相同。主 owner 随后重建最终 0.7.0 wheel，在本分支的 Python 3.14 CPU 环境普通安装，并从源码外运行全套 255 项，全部通过、无跳过；本分支按该结果结束，不重复回归。最终 wheel 为 `experiments/20261106-basepack/dist/rectification-0.7.0/basepack-0.7.0-py3-none-any.whl`，SHA256 为 `742dad25435ffa061f2a4bff30a7abb9353ac6be227d7078fd804475c6dc8176`。

## 实际 CPU 与跨设备验收

在无 CUDA 的 Torch CPU 3.13 环境，用 Condor 临时托管单份 CPU LitServe 服务，申请 2 CPU、12288 MiB RAM、512 MiB scratch、600 秒执行限；没有增加 GPU 模型。实际完成以下短流程：

1. 新项目默认 vector；先显式用 text 接受两个文字块和一张原图，再由 CPU 补建并切回 vector。CPU `/info` 为 `device=cpu`、`dtype=float16`，身份与既有 CUDA 0.5.0 服务相同：`Qwen3-VL:4e32ece7973113a13abd40dcbe5e5e4c8592f172f75535dc087f74f5269bba9e`。
2. 默认 search 和 brief 用“持久化数据多久备份一次”找到“每周导出数据库快照”，并按返回的版本与行位置读回原文。图像查询找到白底左红三角、右蓝正方形；实际查看了原图，图像原件在搬迁后仍定位至新项目内。
3. CPU 索引由 CUDA 查询、CUDA 索引由 CPU 查询均找回相应文字与原图；两次 `embed` 均直接复用全部 3 条向量，没有因设备变化重建。空 scope 过滤、项目搬迁后的 ID/依据/向量复用均通过。
4. 原件增加“导出文件保存90天”后，发布前仍能读取旧版本原文；CPU 准备新候选并一起发布知识与匹配向量。发布后默认 search/brief/read 反映新依据，pending 为 0。

两组 2048 维结果均为有限数值。三个同输入向量的 CPU/CUDA 余弦为 0.999993–0.999998，最大逐元素绝对差为 0.00027–0.00037；这些是本次观测，不设为产品硬阈值，不要求近同分同序。完整断言见[验收结果](../../../artifacts/runs/20261110-rectification-embedding/cross-device/verification.json)，输出与源码普通安装对应性见[数值观测](../../../artifacts/runs/20261110-rectification-embedding/cross-device/cross-device-numerics.json)。

最终临时服务作业 `14357.0` 执行 127 秒后由本验收主动停止，native 终态及全部 5 个已知进程回收均确认，见[清理结果](../../../artifacts/runs/20261110-rectification-embedding/cross-device/cpu-job-cleanup.json)。临时 SurrealDB 进程同时结束；正式共享模型服务保持原状。

开发中保留两次验收脚本修正的原证：首次 Condor 环境没有用户名，Torch 默认缓存路径构造失败；仅在临时 launcher 显式将 `TORCHINDUCTOR_CACHE_DIR` 指向 scratch 后继续。第二次脚本错误地要求 LF，但 Windows 写入与快照正确保留了 CRLF；修正测试预期后完成上面的完整流程。两次临时作业均已结束并确认回收；没有据此修改产品异常处理或加入重试层。原错及清理记录在 `artifacts/runs/20261110-rectification-embedding/setup-attempts/`。

## 对主 owner 的交接

机器 schema 1 和项目 schema 2 保持；配置已有字段，无迁移层。系统资源说明应更新 CPU/CUDA 设备选择、CUDA 专属预算、身份跨设备复用及 `/info` 观测字段；部署与环境说明区分轻客户端兼容、具名模型 extras 的依赖可解和实际推理证据。源码、配置、测试及示例没有新增需登记的产品文件。必要原证已选留 `artifacts/runs/20261110-rectification-embedding/`；一次性安装环境和剩余中间物在 `tmp/rectification-embedding/`，可按项目约定清理。本分支没有未完成的产品修复；共享安装与最终 Git 提交由主 owner 负责。
