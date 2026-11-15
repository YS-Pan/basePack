# 高效 attention 路线与显存实测

2026-11-15。承接[math路径标定](embedding-vram-20261115.md)，调查换框架／FlashAttention能否降低长上下文显存。结论是本机不必先换服务框架：现有Windows、Sentence Transformers6.2.0、PyTorch2.10.0+cu128和Qwen3-VL-Embedding-2B/FP16，经显式选择cuDNN attention已在隔离作业跑通单条10k和10k×4。生产服务仍用原配置，本次仅形成可评审的实验结果。

## 原生后端与原因

小张量矩阵作业14399.0在本机RTX4060Ti检测到：Torch原生Flash未编译；EFFICIENT_ATTENTION在enable_gqa=true时无可用kernel，展开KV头后可用；CUDNN_ATTENTION对两种情况均可用。当前HF在无mask的CUDA路径会启用GQA。本机默认优先序为Flash、Efficient、Math、cuDNN、Overrideable，因此在该输入上先落math，不能把配置写了sdpa当作已经采用融合kernel。

完整模型实验只用 `sdpa_kernel(SDPBackend.CUDNN_ATTENTION)` 显式选择后端，没有修改Transformers的GQA逻辑。跟踪确认实际出现 `_scaled_dot_product_cudnn_attention` 和 `_cudnn_attention_forward`；这是cuDNN融合attention，不是安装了Dao-AILab的flash-attn包。两者都可避免完整注意力中间矩阵，但具体支持范围须分别验证。

## 纯文本实测

token数含模板，由实际preprocess的attention_mask核对。表内是PyTorch张量峰值，单位GiB；不含全部CUDA进程开销或桌面。

| 长度 | batch1 | batch4 |
| --- | ---: | ---: |
| 2048 | 4.074 | 4.382 |
| 4096 | 4.177 | 未测 |
| 8192 | 4.382 | 未测 |
| 10240 | 4.485 | 6.024 |

单条四点对应峰值MiB为 `4067.086 + 52.531*(L/1024)`，在已测点残差为0；batch4两点也与临时内存按B×L增长相符。本样本的权重常驻部分约4 GiB，新增部分近线性，不是把总显存直接随长度相乘。

10k×4最初在顺序测试及全新进程的6656 MiB分配器上限下均被拒；同一7164 MiB作业总预订内，将分配器上限设为6912 MiB后成功，allocated峰6168.10 MiB，reserved峰6906 MiB（6.744 GiB）。因此张量峰约6.02 GiB不代表6.5 GiB分配器额度必然足够。单条10k的reserved峰4766 MiB（4.654 GiB）。

三条不同长度的中英文短文本与强制math比较，最低余弦0.9999974、最大分量绝对差0.0003662；所有成功长度／批次均返回有限的2048维向量。它只证明小样本数值接近及这些纯文本负载可执行，未验图像、典型检索排序、长期服务或所有padding形状，identity相同也不代替这些验收。

## FlashAttention与框架选择

- 保留当前Windows与ST/PyTorch，显式选择本机已验证的cuDNN路径，是当前改动最小的后续选项。生产接入仍需沿既有设备、图文、身份和资源合同验证。
- 指定使用FlashAttention-2时，优先WSL2/Linux加现有Transformers/ST。[Qwen官方模型卡](https://huggingface.co/Qwen/Qwen3-VL-Embedding-2B)支持FA2；[flash-attn官方](https://github.com/Dao-AILab/flash-attention#installation-and-features)支持Ada/FP16，正式环境要求列Linux，原生Windows编译仍保留测试限制。
- [Qwen官方README](https://github.com/QwenLM/Qwen3-VL-Embedding#usage)也提供vLLM pooling路线，要求vLLM>=0.14.0；[vLLM官方安装说明](https://docs.vllm.ai/en/latest/getting_started/installation/gpu/#requirements)的CUDA路线不原生支持Windows，可用WSL。换框架还涉及接口、预处理、批次与预分配，不能据名称承诺更少显存。

[FlashAttention-2论文](https://arxiv.org/abs/2307.08691)的分块方案避免保存完整L×L注意力矩阵。在固定模型／精度、无梯度embedding、不保留生成KV cache的条件下，可用 `M ≈ 模型权重 + c*B*L + 工作区` 解释主要增长；密集注意力计算量仍近似O(B*L²)。显式大mask、padding、多模态、工作区及框架预分配会改变整体曲线；模型官方32k能力与调用端长度、截断配置仍须分开核实。[PyTorch2.10 SDPA](https://docs.pytorch.org/docs/2.10/generated/torch.nn.functional.scaled_dot_product_attention.html)说明自动后端及输入限制；后续版本文档不能直接替代本机2.10实测。

## 收尾与原证

14399.0、14400.0、14401.0、14402.0全部原生completed；unsupported/OOM的case按原样保留，不当作推理成功。普通GPU池7164 MiB及其余额度归还，共享服务health、identity和生产2048/batch4/9216 MiB保持。原证在项目 `artifacts/runs/20261115-efficient-attention/`，包含后端矩阵、两次限额失败、最终成功、向量比较、探针和作业日志。

按长任务入口同时运行的自动维护已接受2批／2个初始来源，余42 initial、13 existing-change、4关系、1反馈留后续；既有App Server权限反馈未判修复，显存标定稿因缺id未发布。已stop，全部后代结束、无在途发布后release，owner=null；本次开发文档在收尾后写入，避免再与该轮来源发布冲突。
