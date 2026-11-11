# engineering-judgment 交付结果

2026-11-10。已编写、保留并接入独立 engineering-judgment 技能。用户指定效果在长期真实使用中逐渐感受；本轮按此完成交付，不声称已经证明收益。

## 文件与使用

- [技能正文](../../../skills/engineering-judgment/SKILL.md)：按用户目标、契约责任、证据范围与使用负担指导工程取舍。
- [相关案例](../../../skills/engineering-judgment/references/cases.md)：说明何时保留处理、限制和操作说明，何时修正责任与多余负担。
- [计划](plan.md)和[进度](progress.md)：记录本轮决定、完成范围及后续反馈入口。

完整技能目录可复制到宿主支持的 skills 位置，自动使用条件在 description 中，也可显式调用 `$engineering-judgment`。使用项目提供当前契约、授权和产品状态；技能没有运行时依赖。

## 实际核对与边界

已核对上述五个交付文件的严格 UTF-8 解码、相对文件链接、尾部空白和技能 frontmatter；计划的 `git diff --check` 通过。计划涉及的现有标题锚点已共读确认。

本机 `.agents/skills/engineering-judgment` 沿已有技能方式以 junction 指向 `skills/engineering-judgment`，已静态核对其目标。最初直接创建被只读沙箱拒绝，主 agent 随后通过受限路径批准完成。根 `AGENTS.md`、`README.md` 与本机入口忽略规则已由主 agent 整合，并已读取核对。

本轮没有运行行为测试、对照、触发探针、测试项目发现试验或收益验收。静态核对仅说明文件与接入状态，长期效果留待真实使用反馈。
