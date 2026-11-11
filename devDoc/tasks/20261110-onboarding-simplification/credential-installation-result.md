# 0.8.1 认证凭据自动读取与正式升级

2026-11-11。用户明确选择保留数据库认证、由客户端自动读取项目凭据后，共用轻客户端已普通升级至 **0.8.1**；basePack、array reconstruct、ppt memsys 三个项目已刷新配置与入口。原账号、密码、UUID、store、launcher 和数据库进程全部保留，七表所有记录逐字段不变。此前 0.8.0 免认证候选的[安装记录](installation-result.md)保留原版本身份，本次没有采用它切换正式库。

## 包与隔离验收

最终 wheel 为 `experiments/20261106-basepack/dist/credentials-0.8.1/basepack-0.8.1-py3-none-any.whl`，SHA256：

`5b823201fcdef46f7f22db13af624da6d80cd6f23f9937d4f14a382f6b19917f`

Python 3.14.10 隔离普通安装加载自己的 site-packages，38 个包文件与 wheel、当前源码逐字节一致。真实认证 SurrealDB 4.0.0 下全套 **369 passed、0 skipped**，111.41 秒，包含真实共享模型及原生恢复。全套期间仅 memory skill 同义文案变化；重包前后内容差异只有 `memory/SKILL.md` 和 wheel RECORD，产品代码与测试字节相同。按主 agent 决定不重复功能全套，最终重包重新普通安装、核全部包字节与无配置 `memory guide`。首次受测包 `eb90462a…cfb95` 保留在 `dist/credentials-0.8.1/first-tested/`。

新项目实际运行 19 条命令：init 不生成密码；一次性显式创建本地文件后，真实认证读写、三层成员及关系、vector/hybrid、brief、read、neighbors 通过。新 NoProfile PowerShell 从其它 cwd 清除全部 `*PASSWORD*` 环境变量，生成入口 brief、旧快照 read、prepare/apply/read 均直接使用合法文件成功。业务原件改写及删除后，CRLF 原始快照仍逐字相同。

HTTP 合法认证写入成功；匿名写返回 403，错误密码写返回 401，随后合法认证回查两种失败的 marker 数均为 0。缺失文件保留 FileNotFoundError，错误文件保留 HTTPError，config show 仅解析路径。首轮临时 driver 在创建探针表前检查不存在记录，收到原始 NotFound；修正探针顺序后第二轮完整通过，未改产品错误合同。两轮自有进程均退出，19221 端口关闭；全套自有 19220 进程也已退出。所选回执检查未含密码原文。

## 正式升级窗口与数据保护

主 agent 先停止维护，再为每个项目建立自己的忽略备份：`.basepack/memory/backups/credentials-0.8.1-20261111-final/`。其中保留原配置、instructions、launcher、自有包装器、原凭据字节、原生 export、完整七表只读记录及必要图片；export 前后记录完全相等。其它项目的原文、密码及 dump 未复制到本项目或 Git。原 0.7.1 wheel `ec8d8a4c…3f3b08` 继续保留，升级前 35 个包文件与其一致。

确认共用客户端无活动 Python 进程后，使用最终 hash 对 `D:/AgentTools/envs/basepack-client/Scripts/python.exe` 执行一次普通 `--no-deps` 升级。实际 Python 3.13.17，版本 0.8.1、mode=wheel，导入在该环境的 `Lib/site-packages/basepack/`，38 个文件与最终 wheel 一致。没有安装模型依赖、改机器配置或重启共享服务。

| 项目 | endpoint | 原 UUID | 七表计数¹ | 原 PID |
| --- | --- | --- | --- | --- |
| basePack | 18080 | `464948e9-d41e-420f-966b-ebaa602fd9bc` | 1 / 211 / 241 / 1541 / 22 / 194 / 2325 | 6232 |
| array reconstruct | 18089 | `3b76dcd5-2b05-46fa-b73d-d6e9e4ba9e7f` | 1 / 36 / 39 / 272 / 21 / 21 / 430 | 33428 |
| ppt memsys | 18081 | `ef685966-0442-4d93-8e6c-1c93efacca9a` | 1 / 7 / 9 / 34 / 0 / 2 / 60 | 1236 |

¹ 顺序为 meta、source、source_version、member、node、semantic、change。各表完整记录及每个字段的 digest 前后一致，包含 stale、retired、历史、更正、依据与向量。进程 PID 和创建时间均相同；原密码及 launcher 逐字节相同，未停库或清库重建。

三个配置只去掉旧 password_env，保留 username 和原凭据文件，并补上各自真实 Codex 宿主 project ID 与同 host 的 36 个其它注册根。配置读自正式窗口的最新文件，保留主 agent 刚登记的新测试 source_scope；Codex project ID 与上述 UUID 分开。此次只补配置，不重新采集或编码全历史；每任务按随包 skill 刷新注册清单。

每项目以新客户端执行 memory init 和实际默认向量检索、brief、版本 read；新的 NoProfile PowerShell 在其它 cwd、无密码环境变量时直接执行生成入口，全部 exit 0，mandatory 数为 3 / 1 / 2。刷新前后七表记录完全相等。client 继续连接原认证服务，准备阶段三个正式库匿名 SQL 均为 403。

## 手写入口与包装器

已删除本项目及 array instructions 在生成 marker 外的旧密码环境变量加载说明；array `devDoc/system/basepack.md` 改为当前 0.8.1 和自动文件调用；ppt `scripts/basepack.ps1` 删除可选文件读取与密码环境变量桥接。ppt 原生 `backup-memory.ps1` 继续设置 SurrealDB 原生认证变量，但从 config show 取得实际 username、memory_password_file、endpoint 和逻辑库参数。

两份 PowerShell 语法检查通过，ppt 包装器在无密码环境变量时正确返回 0.8.1 和凭据路径。修改后的原生备份脚本还实际成功执行：清空 legacy 密码和 SURREAL 变量后，完成原生 export、7 个登记来源复制/hash 校验及 assets 复制，产物在该项目 `.basepack/backups/20261111-095205/`。这次只读导出未改变数据库。

外部项目开始时均为干净 main。本验证分支修改 array 的 `devDoc/system/basepack.md` 及 ppt 的两份包装器；主 agent 另按业务项目约定补上 dated 升级实测与 ppt 试用记录后统一提交：array main `0439a9b`，ppt main `9b496d9`，两工作区均干净。相关 diff --check 通过；本验证分支没有提交 Git，也没有覆盖其它用户改动。

主 agent 独立复核稳定 0.8.1 的直接 brief 成功，mandatory 3、pending 426、compatible 1199。原待核状态保留，本轮升级没有把历史维护积压清零。

## 原证与边界

非秘密选留原证在 `artifacts/runs/20261111-memory-credentials/`：构建/普通安装与重包等价核验、全套 JUnit、认证及新 shell 回执、三项目 pre/post 计数和字段 digest、入口差异与实际备份日志、driver。完整秘密、原件、export 和 fresh-shell 知识正文保留在所属项目自己的忽略备份或本轮隔离 tmp，未进入 Git、wheel 或中央证据副本。

本轮复用共享 embedding，不重做 GPU/CPU 性能、Condor 或全历史聊天语义验收。正式升级已完成；远端发布未执行。长期凭据权限、备份保留及日常增量维护继续沿各项目既有运维约定。
