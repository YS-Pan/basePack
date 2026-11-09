# 交付共享 embedding 与 Condor 薄入口

从旧 VL runtime 提取固定本地模型、图文预处理、归一化与批处理，交付作业外机器 broker、单模型 worker、跨项目客户端和请求局部取消/截止。保留实例创建锁，移除旧整卡排他锁和13GiB空闲门槛；broker 自有进程树与 Condor 作业独立。

实现普通任务 run/submit/status/wait/cancel、预算片段生成/实际发布核对、明确单位、原生与客户端时限、应用退出/产物与进程树回收报告。真实 Windows 探针发现参数转换丢空值，改为随包薄 worker 读取 UTF-8 参数文件；submit 其他字段分别编码，保留 starter 的 GPU 可见性。

真实最大输入确定 E9216/S2048/B5116 MiB；Condor 为12 CPU/24576 MiB，包含桌面及服务预留。机器配置为唯一来源，片段安装并 peaceful 重启 startd 后核实际值。跨项目图文、请求隔离、空闲/崩溃生命周期、真实 CPU/GPU、复杂参数/传输、应用失败及取消/执行时限已运行；完整联合与 wheel 交付继续见 [进度](../../archive/20261107-resource-coordination/progress.md)。使用文档、管理员文档和 resources skill 随代码交付，原始证据留忽略目录 artifacts。
