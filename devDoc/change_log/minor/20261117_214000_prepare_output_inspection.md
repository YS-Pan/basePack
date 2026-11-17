# 避免元数据投影意外重复正文

实际0.17.2维护中，solo作者的元数据投影保留previous嵌套正文，随后又读相同当前正文，至少6067原文字符重复进入可见输出。0.17.3新增单一共享读取合同并渲染进三个维护角色：元数据采用显式字段白名单，核版本与正文hash后相同正文展示一次；不同版本、关系共读和必要修复回读继续执行。canonical prepare、固定hash、存储及并发guard不变。

普通安装66文件与源码/wheel一致、pip check通过；既有130项prompt与9项project-entry测试、49项安装/渲染检查通过。新身份实际执行与净效果继续随维护观察，字符量未换算为token或费用。阶段65/113实际处置、九项祖先head冲突和用量证据见[执行记录](../../tasks/20261115-real-use-rectification/execution.md#正式端点全项目维护首个有限阶段)及[调查](../../tasks/20261115-real-use-rectification/research/terra-usage-20261117.md)。
