# 2026-11-07 · 英文化两个 skill 并注册项目级 agent-team

按用户要求，用 `writing-for-agents` 及其 skill 编写分支指导 [file-structure](../../../skills/file-structure/SKILL.md) 和 [agent-team](../../../skills/agent-team/SKILL.md) 的英文重写，包括触发说明、正文、布局参考与 UI 元数据。保留按条件读取、清晰完成标准、必要背景和简短交接；协作仍以能力及成果质量为目标，允许增加用量换取更好的结果。

在项目 `.agents/skills/agent-team` 建立指向仓库维护源的 junction，与 `file-structure` 一样只作项目级发现。本机联接由 `.gitignore` 排除，两个 skill 均无用户级入口。[环境说明](../../system/environment.md#项目-skill-的本机入口) 更新两者的本机入口与新检出建立方法；旧变更记录的标题锚点同步修复。

检查：两个 skill 的标准验证、六份技能文件的英文覆盖与 UTF-8、UI YAML、本地链接和锚点、差异检查通过；参考文献 URL 保持原样。实际 Codex `skills/list` 在项目根目录及 `devDoc` 子目录发现两个英文 skill，均为 `scope=repo`、`enabled=true`；项目外未发现，三处均无发现错误。原始结果留在忽略目录 `artifacts/skills-english/`。

本次为语言与发现入口调整，未重跑大规模性能对照。用户已有的纲领修改保持原样，未纳入本次提交。
