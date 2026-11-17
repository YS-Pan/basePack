# Gaussian连续降权与完整系统比较图

2026-11-17。用户最新选择Gaussian相似度，长期未用材料只降到很低权重，始终保留。本次更新[长期计划](../../tasks/20261115-real-use-rectification/plan.md)、[唯一数值合同](../../tasks/20261115-real-use-rectification/target-architecture.md)、[选择与总图](../../tasks/20261115-real-use-rectification/forgetting-options.md)及相关入口；上一版线性默认、低效用退出、引用GC、forgotten、防重建、训练库存过滤和为GC新增的请求保护不再执行。语义纠错/退役、mandatory和既有发布所有权继续沿原合同。

Gaussian逐原始anchor求核再加权，以稀疏锚点质量H/R及精确版本标量基准累计；unknown不当零、不重归一。修正线性M累计与O(pr)承诺、Gaussian正交尾部和半衰说明；保留首次接受先验、真实hits、精确版本奖励及冻结模型重放。低权重不导致材料丧失基础检索资格，也不承诺存储自动收缩。

[完整系统前后图](../../tasks/20261115-real-use-rectification/diagrams/README.md)分别描述已部署0.16与待实施目标，使用同一份节点、坐标和连线定义。固定颜色区分main agent、subagent、代码和数据，变化槽位另标；提供可编辑SVG、同源PNG/PDF。实际渲染、打开检查并根据视觉和语义问题迭代，校核未改动对象的完整XML相同。

实际检查：独立数学审阅通过；标准库合成事件核对中最大年龄误差3.33e-16、权重误差2.22e-16，覆盖空/重复/冲突交付、partial/unknown、never-hit首次接受、精确版本与模型重放。文档UTF-8、局部链接/锚点、围栏及Git差异检查沿本批原证记录。图的轮次、最终导出检查和同源对象数量见图源说明。原证/可重跑数值脚本在`artifacts/runs/20261117-gaussian-diagrams/`，不作为NMF、并发、性能或业务效果证明。

本次未实现N0—N5、改产品代码/配置/数据库、安装客户端、发布或修改纲领；外部项目只读图形方法参照，没有写入。例行automatic在语义派工前遇既有Codex SQLite14，自清理后owner=null；收尾stop返回非当前owner，独立复查仍null，无需重复release。维护失败未阻止本轮计划和图交付。
