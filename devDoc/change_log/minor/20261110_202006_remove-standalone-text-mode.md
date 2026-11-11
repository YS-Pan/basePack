# 删除独立纯 text 模式

用户经[另一聊天](codex://threads/01a1c556-ef6d-7b32-8c84-f8878a31ed05)明确要求在本轮执行，接续已完成的0.7.0整改交付0.7.1。配置与CLI仅支持vector/hybrid；候选成员统一准备向量，模型或兼容索引缺失保留明确错误。hybrid保留文字匹配，`--literal`优先路径、标题和正文子串命中，并报告词法来源；vector与literal组合明确拒绝。

三个旧text项目已复用全部有效发布向量后切换vector，知识、ID、来源、历史及既有stale/retired不变；最终客户端和生成入口核验见[安装结果](../../archive/20261110-rectification/installation-result.md)。文档、示例、随包memory skill及关系旧版本回源指令同步收敛。

源码CLI/config67项、隔离记忆124项通过；最终普通wheel在Python3.14源码外完整266项通过、无跳过，含真实共享模型及原生恢复。工程取舍skill保留且未做效果测试。详细实际条件和最终交付见[整改结果](../../archive/20261110-rectification/result.md)。
