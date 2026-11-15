# 高效 attention 可行性与显存对照

官方路线比较加本机隔离实验确认：保留现有框架显式选择cuDNN即可跑通10k×4，实测张量峰约6.02 GiB，旧math的平方增长外推不适用于该后端。记录后端优先序/GQA限制、近线性曲线、小样本数值比较与未验范围；生产未切换。依据和实际检查见[实验结果](../../tasks/20261106-memory-system/research/efficient-attention-20261115.md)。
