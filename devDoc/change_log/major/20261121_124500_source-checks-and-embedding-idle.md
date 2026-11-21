# 实施记忆来源检查和共享 embedding 空闲回收

0.18.9 增加 `memory check-codex-capture` 和 `memory check-file-changes` 两个主名称，沿用已有处理入口兼容旧名称。命令帮助按职责分组。检索提示和产品文档明确 Windows Codex 检查所需的单次 Auto Review。

CUDA worker 空闲 60 秒清理可回收缓存。Windows 用户任务空闲 30 分钟后关闭准入并正常退出进程树，排队和推理计为活动。退出前短暂保留监听给出明确拒绝，宿主可按需唤醒同一模型并继续使用现有向量索引。

回归、Windows/CUDA 实机联验及候选包校验见[后续开发进度](../../tasks/20261120-follow-up/progress.md)。
