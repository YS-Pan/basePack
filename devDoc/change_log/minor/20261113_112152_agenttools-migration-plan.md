# 三工具 AgentTools 迁移评估与计划

根据用户要求，重新评估 AIGC、TTS 的系统 Python 迁移，并纳入 Codex 用量统计，形成 [计划](../../archive/20261113-agenttools-migration/plan.md) 与 [进度](../../archive/20261113-agenttools-migration/progress.md)。推荐复用现有 basePack 资源入口，独立维护和普通安装三工具；先验证系统依赖与功能，再切换路径和调用方。

本轮核对源码、依赖与本机安装元数据、已知调用方及官方上游，确认实际接口/版本和持久路径问题；只修改本仓库计划文档及入口，未执行外部工具迁移或环境变更。实际检查与 basePack 启动失败/自动维护收尾见进度记录。
