# Embedding 上下文长度与显存标定

后续已实测现有框架显式使用cuDNN后跑通10k×4，见[高效后端结果](efficient-attention-20261115.md)。本文18–19／60–65 GiB只针对保持math路径的外推，不代表换后端后的需求或本卡的固有限制。

2026-11-15。针对2k提高至约10k的显存问题，在独立HTCondor作业内复用本机Qwen3-VL-Embedding-2B固定revision、FP16、Sentence Transformers6.2.0和PyTorch2.10.0+cu128。共享0.13.0.dev1服务保持运行，生产配置仍为2048、纯文本batch4、9216 MiB预算；本次没有提高生产上限。

## 实测与估计

| 实际含模板长度与负载 | PyTorch峰值allocated | 峰值reserved | 性质 |
| --- | ---: | ---: | --- |
| 模型刚加载 | 4058.96 MiB | 4064 MiB | 本次实测 |
| 1024，batch1 | 4275.63 MiB／4.18 GiB | 4296 MiB | 本次实测 |
| 2048，batch1 | 4780.18 MiB／4.67 GiB | 4812 MiB／4.70 GiB | 本次两轮一致 |
| 3072，batch1 | 5580.73 MiB／5.45 GiB | 5642 MiB | 本次实测 |
| 3584，batch1 | 6093.00 MiB／5.95 GiB | 6166 MiB | 本次实测 |
| 2048，batch4 | 6871.41 MiB／6.71 GiB | 7020 MiB／6.86 GiB | 同实现的[R9边界实测](../../../archive/20261107-resource-coordination/r9-result.md) |
| 10000–10240，batch1 | 约18–19 GiB | 未实测 | 保持math后端的外推 |
| 10000–10240，batch4 | 约60–65 GiB | 未实测 | 另假设临时内存随batch近似成比例 |

allocated是张量占用，reserved还含PyTorch分配器缓存；这些数字不含进程全部CUDA开销、桌面和其他程序。预算9 GiB不是预先占用9 GiB，刚加载约4 GiB也不是2k推理峰值。[PyTorch内存口径](https://docs.pytorch.org/docs/2.10/notes/cuda.html#memory-management)解释了两者与nvidia-smi观察值的区别。

单改max_length仅改变本项目forward前的输入检查，不会按新上限预分配一份10k工作区。只有实际送入更长序列才触发相应峰值；实际长度、batch和后端共同决定需求。

## 为什么10k外推很大

本次torch报告 `flash_attention_available=false`，CPU算子跟踪明确出现 `aten::_scaled_dot_product_attention_math` 与softmax；不是只根据配置里的sdpa字符串推断。此路径的实测峰值包含显著平方项。[PyTorch SDPA说明](https://docs.pytorch.org/docs/2.10/generated/torch.nn.functional.scaled_dot_product_attention.html)区分Flash、内存高效与math实现，后端按输入条件选择；math对FP16输入仍使用浮点中间量。

令x为含模板token数／1024，用1k、2k、3k单条数据拟合得到峰值MiB约为 `4067.09 + 60.55*x + 148*x*x`，3.5k点的误差为1 MiB。外推10000/10240分别为18.33/19.02 GiB。将临时部分随batch乘4得到61.42/64.15 GiB；该假设对已有2048×4预测6919.46 MiB，相对实测高约0.7%，但没有直接验证10k批次。

这些是保持本次math路径的容量估计，不是10k实测或所有平台的模型要求；更换后端后需要重新标定。当前16 GiB卡及9 GiB服务预算预计无法直接承载此路径的单条10k。先解决高效attention后端，再评估长输入，比只改输入检查上限更有意义。

## 执行与收尾

作业每次申请2 CPU、12288 MiB RAM和7164 MiB显存；PyTorch分配器限额6656 MiB，为其他进程开销留空间。14397.0测到2k单条后，4k单条触及这个6.5 GiB限额，记录OOM并结束；这不等于4k耗尽16 GiB整卡。14398.0的四个短长度均返回有限的2048维向量，并记录实际attention算子。每个case先清空闲缓存、CUDA同步并单独重置峰值，长度由同源model.preprocess的attention_mask核对。

两次前置启动失败保留：14395.0因临时profile.py与标准库重名而导入失败，缺返回文件后held，已显式移除；14396.0因槽账户环境缺名称导致PyTorch默认缓存初始化失败，已原生结束。改为独立脚本名、实际槽账户名称和作业内缓存后再测，没有伪装交互用户或修改全机环境。14397.0／14398.0均原生completed，退出0表示标定程序完成，OOM case不算推理成功。

全部作业已结束，普通池7164 MiB、GPU名额、CPU/RAM恢复；共享服务health正常，identity和生产三项配置保持。全卡观察从开始约6643 MiB回到约6645 MiB，不把全卡数当模型独占用量。原证在项目 `artifacts/runs/20261115-embedding-vram/`，含curve、首轮有效结果、估计系数、探针和四次作业日志；无10k直接峰值。
