# 调查外部项目缺少 skill 发现入口

核对 array reconstruct 的 0.6.2 接入、迁移聊天和当前 basePack 源码，确认两项 skill 原件完整，但未建立 `.agents/skills`。两条隔离 init/core doctor 均成功且未生成或检查技能入口；README 外部安装步骤晚于迁移加入，调查保留这一时间边界。

结论、原证、修复建议与未提交的 Issue 草稿见[调查记录](../../tasks/20261106-rebuild/research/array-skill-discovery.md)。本次只保存调查，不改变产品、外部项目、已安装客户端或共享设施。实际检查包括 6 个文件哈希、历史提交、保留 wheel 的静态核对、两次隔离初始化及文档链接与差异检查。
