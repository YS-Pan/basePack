# 标准 GPU 提交与 Condor 站点策略解耦

R7已交付basePack0.3.0普通wheel、本机60/70配置、使用/管理员说明及resources skill。普通客户端只发送官方request_gpus/gpus_minimum_memory；schedd原生JOB_TRANSFORM统一生成内部显存申请并保留原匹配条件，容量和资源名完全由Condor维护。capacity通用发现MachineResources，保留标准CPU/RAM准入；缺显存预订整池，非法/超池/多GPU以官方参数拒绝。

保持12CPU/24576MiB、单卡4共享名额、7164MiB普通池与9216MiB背景预留。空队列、提交暂停及旧服务退出后成对升级包和策略，备份保留；最终恢复无模型驻留的独立broker。未修改项目纲领。

源码与源码外安装回归均22项通过，22份包内文件与源码/安装一致。真实CLI/Python CLI、四+第五、显存不足、默认整池、CPU、原筛选、拒绝与取消归还全部通过；4×2048 token embedding期间有6个正确CUDA进展点，取消后同worker继续。最终空队列、全部资源归还。

定位25.4离线转换工具退出1的源码原因并留原始证据；修正该版提交拒绝规则的JOB作用域和Windows未发布Swap数量处理，保留对应回归。小矩阵只验证调度记账；Python通过官方CLI，未验证不兼容的cp39绑定。完整证据、版本、wheel校验与边界见 [R7回执](../../tasks/20261107-resource-coordination/standard-submit-result.md)。
