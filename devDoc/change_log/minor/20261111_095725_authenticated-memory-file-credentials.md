# 保留认证并自动读取项目凭据

按用户明确选择交付0.8.1：数据库保留认证，客户端创建时从唯一项目密码文件读取并携带HTTP Basic认证，CLI/Python共用；新shell直接调用，不再手工设置password_env。保留UTF-8 BOM、CRLF和首尾空白；缺文件、权限及认证错误原样失败，不自动换密钥、回退免认证或重试。新库在部署阶段一次生成秘密，已有项目复用原账户和文件。

普通安装全套369项通过、无跳过；真实匿名写403、错密401且无写入，新进程和旧快照通过。最终仅同义SKILL变更重包，代码与测试不变，38文件重新字节核验。共用客户端及basePack/array/PPT已升级，三个项目七表逐字段一致、原凭据及数据库进程保持；外部入口与PPT原生备份已实际验证。

原免认证候选保留历史证据，未切换正式库为免认证。实际范围、备份/回退资料、外部提交及原证见[正式升级结果](../../archive/20261110-onboarding-simplification/credential-installation-result.md)和[实现结果](../../archive/20261110-onboarding-simplification/credential-result.md)。没有推送或发布远端。
