# 普通作业回归Condor原生生命周期

按用户选择，作业限时、停止与清理由Condor原生策略负责，接受其生效时效。删除客户端重复作业计时、超时自动cancel、PID/worker回执及cleanup_confirmed，移除失去消费者的psutil依赖。保留JSON argv封装、退出码、submission token不确定提交查询恢复和原生限时提交字段。

调用者wait到期返回observation_expired，作业继续运行；held、取消请求与原生终态分别呈现，命令错误保留原错。资源skill、用户文档及系统模块同步更新。

相关62项回归通过；隔离普通wheel在正常用户上下文实际执行CPU作业14393.0和14394.0：参数逐项保真、观察到期仍在queue、显式取消后进入history。两项新作业均收尾，原证在`artifacts/runs/20261114-delivery-closeout/condor/`。源码外安装、客户端/库及共享服务总体交付继续见[收尾进度](../../tasks/20261114-delivery-closeout/progress.md)，不据此声称新机部署或收益已验证。
