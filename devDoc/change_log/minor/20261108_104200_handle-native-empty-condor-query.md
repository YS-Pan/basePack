# 按原生空查询合同解析 Condor 输出

源码外普通wheel验收发现：本机Condor25.4对无匹配job的成功查询返回空文本，而非JSON空数组。上一批收尾删除空输出处理后，已完成作业无法接续查询history；修复为仅将成功空查询解释为无匹配，非空无效JSON仍直接抛错。保留对应回归，原始实证及中断测试回收见 `artifacts/r5/interrupted-cleanup.json`。测试GPU作业14294原生历史exit0，launcher/应用及测试broker/worker均已确认退出。

重新构建普通wheel并执行完整源码外验收，结果由 [资源任务](../../archive/20261107-resource-coordination/progress.md) 维护；本记录不把部分已完成计算当作最终验收通过。
