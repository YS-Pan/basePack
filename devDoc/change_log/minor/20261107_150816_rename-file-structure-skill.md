# 文件结构技能改名

按用户指定，将技能 `project-layouts` 改名为 `file-structure`：源码目录迁至 `skills/file-structure/`，frontmatter、正文标题与 UI 显示名同步更新。本机项目级发现联接改为 `.agents/skills/file-structure`，仍指向唯一源码；AGENTS、开发说明、任务材料、历史记录中的现用引用及 Git 忽略规则同步更新。

功能与两份布局参考保持原样，纲领及原始计划快照未修改。历史验证目录和原始回执保留当时的名称，改名后的检查材料存放于本机忽略目录 `artifacts/file-structure-rename/`。

检查：标准 skill 验证、UI YAML、60 份 Markdown 的 186 处项目内链接（含 26 处标题锚点、15 处行号引用）、Git 忽略规则与差异检查通过。四份技能源码核对仅含名称元数据变化，纲领与原始计划快照 SHA-256 不变。实际 `skills/list` 强制刷新后，项目根目录及子目录均发现新名称且为 `scope=repo`、`enabled=true`，旧名未发现；项目外用户目录未发现该技能，三处均无发现错误。
