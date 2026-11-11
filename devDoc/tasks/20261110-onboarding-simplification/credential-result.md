# 认证保留与凭据自动加载结果

2026-11-11（北京时间）。用户在了解免认证跨源写入风险与替代流程后明确要求实施保留认证、简化凭据流程。本轮从 main `64e8c2a` 的 0.8.0 候选接续，目标版本 0.8.1；旧 [免认证隔离结果](auth-result.md) 保持其版本与证据身份，不覆盖为认证结果。本文记录认证实现分支；普通 wheel 及正式三项目升级由主 agent 的安装验证分支接续。

## 已实现合同

项目模板将 `[memory].username` 设为 root；可选 `password_file` 是密码的唯一项目来源，相对路径从项目根解析，省略时为实际 `memory_dir/password.txt`。`ProjectConfig.memory_password_file` 和 `config show` 返回解析后的绝对路径；配置加载与展示不读取密码，普通 init、jobs-only 及无需配置的 memory guide/rank/stop 也不创建或读取密码文件。

每次构造 `Memory` 客户端时读取该文件，使用标准 UTF-8 codec 识别可选 BOM，并保留 CRLF 与首尾空白；不 strip、不进行编码回退。以用户名和原文密码构造 HTTP Basic Authorization，CLI 与 Python 调用共用此实现。没有 password_env、环境凭据回退、免认证分支、缺文件补建或自动重试；已构造的客户端使用该次加载的凭据，新进程/新客户端重新读取文件。

缺文件与无权读取分别保留原始 FileNotFoundError、PermissionError；空文件/错误内容交数据库认证，HTTPError 与服务端响应按既有错误合同保留。生成 instructions 继续是显式 Python、绝对 config 和一次 brief 调用，只说明客户端自动加载密码文件，不指示 agent 原文读取密码或设置 shell 密码变量。

新库仅在显式部署步骤用 CSPRNG 一次生成密码，并以 exclusive-create 写入；已有文件保留，已有 store 缺文件时恢复原凭据而不是生成替代密钥。产品 init 本身不做部署或秘密生成。launcher 的文档样例从同一配置和文件读取用户名/密码，通过 SurrealDB 原生入口启动认证服务，仅回环监听；不使用 `--unauthenticated`。已有认证库保持原存储账户、密码、UUID 与服务，无需因客户端自动加载而重启。更换启动环境值或文件内容不会轮换已有库内账户，轮换须另行显式执行。

## 实际验证

最终源码专项在独立认证 SurrealDB 4.0.0 上 **110 passed**，涵盖配置、CLI、错误与新增凭据回归。缺文件在网络访问前失败；Windows 文件 ACL 实际拒绝读取时抛出 PermissionError，合成夹具随后删除。HTTP 401 回归核对单次请求、无盲重试、空内容、首尾空白、LF/CRLF、UTF-8 有/无 BOM，确认客户端 header 与 launcher 文本合同一致。已有 guide/rank/stop 无配置和坏配置行为保持，新增有效配置但无秘密文件的覆盖。

真实数据库拒写回归用与此前风险测试相同的简单请求形式：text/plain、Origin、SQL 正文 `USE NS/DB` 后 CREATE，不带 Authorization。认证服务返回 **403**，正文为 `Anonymous access not allowed`；错误文件密码返回 **401**。分别以正确认证再次查表，两次均没有写入记录。正确项目文件可用，即使进程故意设置错误的旧 password 环境变量也不影响。这是服务器认证/权限边界验证，没有重测公网 HTTPS 页面、LNA 权限或混合内容行为。

新项目产品闭环使用真实共享 embedding，完成 init、memory init、prepare/apply、brief、hybrid/vector search、read 与 neighbors，发布 3 个 member、1 个 node 和 1 条关系，3 个向量均匹配当前 identity。launcher 和客户端使用同一个临时项目密码文件，客户端进程及新的 Windows PowerShell 中清除密码环境变量；从无关 cwd、中文/emoji 路径直接运行生成入口成功。原件改写和删除后仍精确读取旧 snapshot；错误 UUID 与非回环 endpoint 实际拒绝。驱动 exit 0，并确认密码首次生成后再次 exclusive-create 拒绝且原字节未变。

另一个独立认证数据库上，七个受影响记忆模块 **100 passed**，包括原生 export/import 七表恢复对照、文字与图片快照、真实共享图文向量、发布、维护与检索覆盖；原生 CLI 只在子进程环境中从指定文件加载凭据，参数与日志不包含密码。两组为不同测试范围，不替代最终全套和普通 wheel 验证。

## 原证与交接

选留原证在 `artifacts/runs/20261111-auth-credentials/`：`authentication-result.json` 为真实 403/401 和无写入回执，`source-product-receipt.json` 保存完整命令和回源断言，`source-tests.log` 为最终 110 项日志，`lifecycle.json` 记录自有隔离进程停止及密码生成约束；另留产品与夹具驱动。此目录受 Git 忽略，不含密码文件、Basic header 或正式库副本。临时源位于 `tmp/20261111-auth-credentials/`，其中测试密码仅用于已停止的隔离库，不随提交分发。

本分支未修改正式配置、共享安装或正式数据库进程，没有轮换或删除任何正式凭据；只停止自有隔离进程。现有三项目普通升级、手写旧密码提醒/包装的清理以及最终 source/wheel 回归由主 agent 与安装验证 owner 负责。新增 `test_memory_credentials.py` 需登记本项目 source_scope；本分支不改版本/锁、不提交，由主 agent 统一审查与提交。
