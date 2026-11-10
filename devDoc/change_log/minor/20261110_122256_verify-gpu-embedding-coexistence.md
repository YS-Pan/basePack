# GPU 小作业与共享 embedding 并存复核

以普通安装的 0.6.2 客户端在正常用户上下文完成 GPU 作业 `14350.0`：真实 CUDA 矩阵结果正确，作业运行期间共享 embedding 正常返回向量，实时 slot 配额扣减及结束后资源归还均通过。现行证据与边界见 [环境说明](../../system/environment.md#2026-11-10-062-gpu-作业与共享-embedding-并存复核)。

首轮 `14349.0` 的验收 UUID 格式假设错误已保留，确认回收后修正核对并显式提交成功轮。未修改产品代码、机器配置或服务；本次只证明小负载及请求时段并存，不证明物理 kernel 同时执行、吞吐收益或最大负载承载。

成功回执及输入、CUDA 时间线、向量、原生资源/队列/事件和进程回收记录位于 `artifacts/runs/20261110-condor-gpu-embedding-verified/`；首轮原证保留在 `artifacts/runs/20261110-condor-gpu-embedding/`。
