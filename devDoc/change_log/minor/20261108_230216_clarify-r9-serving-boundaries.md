# 明确 R9 模型与服务职责

用户确认维持 Sentence Transformers＋LitServe＋Shawl。已更新 [R9 计划](../../archive/20261107-resource-coordination/plan.md#r9-复用优先的资源实现) 及两处进度入口，继续沿这一路线验证，不增加框架比较阶段。

首版采用单推理 worker、setup 常驻加载和 Sentence Transformers 请求内批处理；跨请求合批按实际吞吐需求再启用。区分排队 timeout、客户端等待与执行中断，补清 worker 故障处置及 Windows 全部辅助进程和显存回收的验收范围。已在 [调查](../../archive/20261107-resource-coordination/research/reuse-options.md#litserve-的实施边界) 保存 0.2.19 一手源码、停机问题线索和未实测边界。

检查：修改文件 UTF-8、相对链接与标题锚点、Git 差异检查通过。仅维护文档，未安装依赖、运行新服务或修改项目纲领、源码与部署。
