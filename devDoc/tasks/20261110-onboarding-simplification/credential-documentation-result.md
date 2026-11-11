# 0.8.1 认证与自动凭据文档结果

2026-11-11。按用户已决定的“保留认证并简化凭据”更新现行产品与系统说明；0.8.0 免认证候选的计划、结果与运行原证保持历史，未改写为本次结论。本文只记录文档交付与相关检查；源码、普通包与三个正式项目升级的功能验收由各 owner 记录。

## 交付

- 两份 README 保持英文，版本与启用步骤改为 0.8.1 认证服务和自动密码文件读取；去除候选免认证的现行使用说明。
- [项目接入](../../../experiments/20261106-basepack/docs/setup-project.md#新-shell-接续)、[管理员步骤](../../../experiments/20261106-basepack/docs/administrator.md#项目-surrealdb)、[记忆使用](../../../experiments/20261106-basepack/docs/memory.md) 与随包 memory skill 统一为 username + 唯一 password_file。可选文件路径相对项目根或绝对，省略时为实际 memory_dir/password.txt；新 CLI/Python 客户端自动读 UTF-8 文本（兼容 BOM，保留 CRLF/首尾空白），config show 只显示解析路径。guide/rank/stop 不需配置或 secret，普通 init/jobs-only 不生成密码。
- 新库首次显式生成安全随机文件并 exclusive 写入，已有文件保留；已有 store 缺文件时拒绝生成并要求恢复原凭据。launcher 读取同一配置、用户名与文件，认证并回环监听。缺文件、权限和认证错误保留；不 trim、不重试、不自动补建或回退无认证。修改文件不等于轮换数据库保存的账户。
- 既有认证项目保留原凭据、数据库目录、端口与 UUID，主要升级普通客户端、刷新 instructions 和手写包装；通常无需重启或迁库。新 shell 直接 brief，不再手工加载 password_env。原生 SurrealDB CLI 的 export/import 单独按其官方认证环境运行，不把这段放入客户端启动入口；恢复集合包含原凭据文件。
- overview、deployment、architecture、diagrams 与 memory/resources 模块同步现行职责和数据责任；机器环境保留既有日期记录，并接续 2026-11-11 的正式 0.8.1 安装实测。

## 检查与边界

`tmp/20261111-auth-credentials/docs-check.py` 对 15 份 Markdown（含本文） 完成 UTF-8、围栏、README 英文正文和 227 个本地链接/锚点检查；6 段新库准备、launcher、启动、检查、SCM 与原生导出 PowerShell 示例均经原生语法解析。相关 Git 差异检查在包内冻结及最终环境补记后完成。临时材料只在本任务 tmp；没有打印、复制到报告或提交密码原文。

本分支只读准备外部手写入口方案；validation 已完成实际入口更新，外部提交由 root 统一处理。本分支不修改正式配置、数据库或客户端，也不运行独立 skill 效果测试。最终普通 wheel 和三个项目的新 shell 读写、原凭据/launcher/PID 及七表逐字段一致证据见 [安装结果](credential-installation-result.md)，环境当前状态见 [日期实测](../../system/environment.md#2026-11-11-081-认证凭据与普通安装)。此后只补非包内记录，README/SKILL/template 字节未再改；文档检查不代替功能验收。
