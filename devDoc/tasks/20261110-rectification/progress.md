# 整改实施进度

2026-11-10。已按[计划](plan.md)启动实施。用户补充：保留 engineering-judgment skill，不做技能测试，效果在长期使用中观察。

## 当前分工

- 主 agent：总体取舍、文档整合、版本构建、普通安装及 main 提交。
- 记忆 coordinator：prepare/413、查询与维护解耦、版本快照与小批发布、任务停止、search/brief 向量路径。
- embedding owner：CPU/CUDA、语义身份、配置/doctor、Python 兼容与依赖。
- jobs owner：Condor 观测、准入职责与相关实际用例。
- 文档 owner：管理员与项目接入流程；skill owner：独立技能和发现入口。

各 owner 完成所属修改与必要产品回归，主 agent 统一核差异、构建和提交。正式库与共享服务暂保持运行；稳定客户端只在检查共用调用结束后统一升级。skill 不进入测试或收益对照。

## 接续信息

本轮入口 brief 保留三项有效 mandatory；已发现5项 pending、9项变化，未以清空积压为业务前提。正式客户端当前为0.6.2，源码为0.6.4，包含尚未普通安装的退役成员修复。正式库不得用清理历史绕过该问题。

产品回归与一次性资料放根 `tmp/rectification-*`，需保留的结论和原证在结束前记录位置。远端推送与 Release 沿计划另行授权。
