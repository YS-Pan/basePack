# 明确低并发维护由 coord 兼做 reader

2026-11-12（北京时间）。根据用户关于较少并发席位的反馈，更新[计划](../../tasks/20261106-memory-system/task-duration-and-worker-naming-plan.md)：整轮维护预算为1至3时默认仅`bp_mem_coord_0`完成阅读、生成和发布，不再另开reader；高预算仍按实际收益组织reader与手动多队。

补充官方Codex配置口径、零reader流程及实际验收，专项进度同步。仅修改计划文档，未实施入口、提示词或安装变更；检查UTF-8、相关本地链接与差异。
