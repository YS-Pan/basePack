# 普通任务改用通用 Condor 节点容量

按用户要求，普通任务容量改由 HTCondor 配置直接维护，移除 basePack 专属预算属性、TOML 普通额度与 hash 发布。背景总预留9GiB；本机普通池为12CPU/24576MiB、7164MiB显存、4个同卡GPU名额，使用官方自定义消耗资源机制累计各作业申报显存。新增只读capacity，embedding自身额度迁入其配置节。

系统普通安装0.2.0 wheel，源码/包/安装22份文件一致，14项回归通过。真实原生作业验证了显存不足排队、4项同卡正确计算、第5项因名额排队、缺显存声明拒绝与CPU独立运行；普通客户端与最大embedding联合进展、取消隔离及回收通过。全部测试作业与模型已释放，轻量broker保留。详细依据、job ID、回执和限制见 [专项结果](../../tasks/20261107-resource-coordination/native-condor.md)。
