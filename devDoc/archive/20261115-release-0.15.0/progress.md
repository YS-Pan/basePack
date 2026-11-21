# 0.15.0发行进度

## 结案

2026-11-19 按用户要求归档。0.15.0 的固定范围维护、客户端安装验收和公开发行均已完成，验收依据见[发行结果](result.md)。当前安装与版本以[部署合同](../../system/deployment.md)为准。受限 shell 的 SQLite 权限反馈继续沿[记忆专项进度](../../tasks/20261106-memory-system/progress.md)跟踪。

## 发行记录

2026-11-15。普通task自动退役规则已清除；ongoing只承接简单有界的顺手整改，复杂判断、调查和批量整理交普通任务，原到期归档合同保留。规则、结构skill及框图同步，文档检查通过。

显式维护已完成固定217/217来源（109 initial、108 existing_change），76个成功批次、4条原待决关系已处理；另4个关联来源用于必要共读/依据接续。作者均结束，已stop，确认无在途/未明发布后release，最终owner=null。JSON回执选择反馈已随实际修复及部署验证结案；受限shell的SQLite权限反馈仍pending，正常用户入口成功不冒充其已修复。原采集缺口和截点外新材料保留。详见[result.md](result.md)。

最终wheel从796416d隔离构建，包装、普通安装及稳定客户端59文件验证通过，依赖检查及实际freshness成功。共享embedding沿此前0.15部署继续运行。本地21项提交已正常快进推送；2026-11-15北京时间16:49:24公开[0.15.0](https://github.com/YS-Pan/basePack/releases/tag/v0.15.0)，非prerelease并设Latest，标签为70be61b。草稿与公开后3附件均下载校验通过，标签/说明/附件及工程tree一致；main随后补本发行回执和README版本。
