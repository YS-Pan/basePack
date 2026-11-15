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

最初三条不同长度的中英文短文本与强制math比较，最低余弦0.9999974、最大分量绝对差0.0003662；所有成功长度／批次均返回有限的2048维向量。后续数值与小型排序对照见下节；长期服务及所有输入形状仍未验。

## 同输入的向量与排序兼容性

隔离作业14403.0固定同一模型revision、FP16、ST6.2、指令、前处理、图片尺度和pooling，只切换强制math／cuDNN。使用10条中英文合成文档、2条实际2048-token文本、2张既有公开测试图片、2条图文及6条查询，逐条batch1编码，共22组配对；token数包含真实模板，输入及图片哈希保存在回执。两条2k文本由重复主题句加填充构造，图片实际118／182 token，图文129／195 token，均非真实全库抽样或大图边界。

| 输入 | 数量 | 新旧最低余弦 | 最大分量绝对差 |
| --- | ---: | ---: | ---: |
| 普通文本 | 10 | 0.9999933424 | 0.0004882813 |
| 2048-token文本 | 2 | 0.9999954626 | 0.0004577637 |
| 图片 | 2 | 0.9999888859 | 0.0006103516 |
| 图文 | 2 | 0.9999915743 | 0.0006713867 |
| 查询 | 6 | 0.9999961114 | 0.0003662109 |

额外4条混长文本batch4（43／44／52／44 token）在两个后端间最低余弦0.9999966587、最大分量差0.0006866455。同一后端从batch1改batch4也有浮点差异：math／cuDNN最低余弦分别0.9999969540／0.9999948723。

以math查询×math文档为基线，用与实际检索一致的cosine排序，对6个查询×16个候选比较：

| 对照 | 相似度分数最大变化 | top1／top3顺序／完整顺序一致 |
| --- | ---: | --- |
| cuDNN查询×旧math文档 | 0.0002984933 | 均6/6 |
| cuDNN查询×cuDNN文档 | 0.0007326907 | 均6/6 |

结论是同一输入下向量高度接近，但非逐bit一致；余弦0.99999不是检索准确率99.999%。[PyTorch2.10 SDPA说明](https://docs.pytorch.org/docs/2.10/generated/torch.nn.functional.scaled_dot_product_attention.html)明确不同融合后端的浮点运算可使输出不同。此次小样本支持旧向量复用，没有显示出仅因换kernel就需全量重算的证据；不能证明全库排序等价，近同分仍可能换序。此处计算为CPU float64 cosine对照，未运行数据库或完整hybrid检索／rank链。

`embedding_identity`没有包含attention后端或max_length；身份相同只表示当前复用合同，不能代替数值验证。当前max_length仅是拒绝阈值，不截断，所以只从2k放宽到10k不改变同一旧输入；重新分块或实际送入更长内容则是输入变化，应对变化项重新embedding，其差异不属于本次后端对照。本次没有math/cuDNN的10k配对数值测试，也未验证未来WSL／FlashAttention-2／vLLM路线。

原证单独保存在 `artifacts/runs/20261115-embedding-compatibility/`：探针、公开夹具、作业规格和日志、全部向量NPZ及逐项数值／排序JSON。44条单输入forward和2条batch4共52个向量输出均有限；从保存向量独立复算各组数值、两种排序与batch结果一致。作业原生completed，普通GPU池额度全部归还，共享服务health与identity保持；生产配置未切换。本次短任务只读取brief，未启动自动维护。

## FlashAttention与框架选择

- 保留当前Windows与ST/PyTorch，显式选择本机已验证的cuDNN路径，是当前改动最小的后续选项。生产接入仍需沿既有设备、图文、身份和资源合同验证。
- 指定使用FlashAttention-2时，优先WSL2/Linux加现有Transformers/ST。[Qwen官方模型卡](https://huggingface.co/Qwen/Qwen3-VL-Embedding-2B)支持FA2；[flash-attn官方](https://github.com/Dao-AILab/flash-attention#installation-and-features)支持Ada/FP16，正式环境要求列Linux，原生Windows编译仍保留测试限制。
- [Qwen官方README](https://github.com/QwenLM/Qwen3-VL-Embedding#usage)也提供vLLM pooling路线，要求vLLM>=0.14.0；[vLLM官方安装说明](https://docs.vllm.ai/en/latest/getting_started/installation/gpu/#requirements)的CUDA路线不原生支持Windows，可用WSL。换框架还涉及接口、预处理、批次与预分配，不能据名称承诺更少显存。

[FlashAttention-2论文](https://arxiv.org/abs/2307.08691)的分块方案避免保存完整L×L注意力矩阵。在固定模型／精度、无梯度embedding、不保留生成KV cache的条件下，可用 `M ≈ 模型权重 + c*B*L + 工作区` 解释主要增长；密集注意力计算量仍近似O(B*L²)。显式大mask、padding、多模态、工作区及框架预分配会改变整体曲线；模型官方32k能力与调用端长度、截断配置仍须分开核实。[PyTorch2.10 SDPA](https://docs.pytorch.org/docs/2.10/generated/torch.nn.functional.scaled_dot_product_attention.html)说明自动后端及输入限制；后续版本文档不能直接替代本机2.10实测。

## 收尾与原证

14399.0、14400.0、14401.0、14402.0全部原生completed；unsupported/OOM的case按原样保留，不当作推理成功。普通GPU池7164 MiB及其余额度归还，共享服务health、identity和生产2048/batch4/9216 MiB保持。原证在项目 `artifacts/runs/20261115-efficient-attention/`，包含后端矩阵、两次限额失败、最终成功、向量比较、探针和作业日志。

按长任务入口同时运行的自动维护已接受2批／2个初始来源，余42 initial、13 existing-change、4关系、1反馈留后续；既有App Server权限反馈未判修复，显存标定稿因缺id未发布。已stop，全部后代结束、无在途发布后release，owner=null；本次开发文档在收尾后写入，避免再与该轮来源发布冲突。
