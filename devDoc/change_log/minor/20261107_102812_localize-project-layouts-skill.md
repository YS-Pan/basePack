# 2026-11-07 · 将文件结构 skill 改为项目级发现

按用户希望局部生效的要求，移除本机 `~/.codex/skills/project-layouts` 用户级 junction，在本项目 `.agents/skills/project-layouts` 建立指向仓库维护源的 junction。四份 skill 源文件保持原样；本机联接由 `.gitignore` 排除，不重复入库。

[环境说明](../../current/environment.md#项目-skill-的本机入口) 已更新当前作用域和新检出时的项目级入口建立方法；AGENTS.md 继续直接引用仓库源文件。

检查：实际 Codex `skills/list` 在本项目返回 `scope=repo`、`enabled=true`，项目外用户目录未发现此 skill，两处均无发现错误；原用户级联接不存在。联接调整前后四份源码 SHA-256 相同，本地链接、UTF-8、忽略规则与差异检查通过。用户已有的纲领修改保持原样，未纳入本次提交。
