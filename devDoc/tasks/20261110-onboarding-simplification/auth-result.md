# 配置、免认证隔离验证与命令收敛结果

2026-11-10（北京时间）。从 main `08bb5e8` 的0.7.1产品基线接续，目标版本0.8.0本地候选。本文负责计划 B、C 的配置/命令分支与 F 的配置接入；memory 实现及其回归由记忆 owner 整合。认证合同在浏览器实测后交主 agent 征求用户选择，下面的免认证结果均为隔离证据，正式项目尚未切换。

## 已实现的配置与入口

- `load_project_config` 在唯一配置边界限定 memory endpoint 为 HTTP(S) 与显式回环 IP；DNS/localhost 别名、通配和局域网地址、URL 凭据及额外路径/query/fragment 被拒绝。IPv4 回环与 `::1` 可用。
- 项目模板移除 `memory.username/password_env/password_file`，配置类和 `config show` 移除 `memory_password_file`；机器模板、配置属性与回显移除无消费者的 `[shared].state_dir`。没有移动机器日志或作业产物，也没有改正式机器配置。
- `memory guide/rank/stop` 在解析项目配置前分派；无 config 或无关坏 config 不影响自身职责，评分/控制文件错误保留。其它项目命令继续要求显式 config。
- F 保存 `[memory.codex]` 的 `project_id/other_project_roots/registry_complete`，分别区别宿主项目身份、其它已注册项目根和清单是否完整；basePack UUID 独立生成。`init` 支持宿主自动传入这三项，生成 instructions 让宿主取得当前聊天项目与完整注册清单，并在维护前刷新。未取得元数据保留缺口，不把空清单当已知完整；这不是 F 采集/语义完成的验收结论。

## 实际检查与证据

配置及命令回归 `test_config.py` 为 **70 passed**。覆盖默认/显式 Codex 绑定与 Unicode 路径、允许与拒绝的 endpoint、无配置三命令、坏输入错误、需要项目配置的动作；`git diff --check` 通过。另清理三份 memory 测试中的旧认证夹具与原生 export/import 参数，将原生恢复对照补为七表；在独立免认证 SurrealDB 与真实共享模型下，HTTP 错误及原生恢复/向量重建回归 **3 passed**。其它 memory 回归由记忆 owner 和最终普通 wheel 验证接续。

无凭据产品闭环使用系统 Python 3.13、本轮源码、SurrealDB 4.0.0 的隔离内存实例及现有真实共享 embedding 服务。进程环境去除 PASSWORD 变量和 `SURREAL_USER/PASS`，项目没有 password.txt，完成 `init → memory init → prepare/apply → brief → hybrid/vector search → read → neighbors`，发布 3 个 member、1 个 node 与 1 条 semantic 边；3 个向量均匹配当前 identity。改写并删除业务原件后，旧快照精确读取保持；生成入口在新的 Windows PowerShell 进程、无关 cwd、中文/emoji 项目路径下成功 brief；错误 UUID 和非回环 endpoint 均实际拒绝。最终驱动 exit 0，完整回执和可供普通 wheel 复跑的驱动在 `artifacts/runs/20261110-onboarding-simplification/auth/product/`。

现有正式库仅作原生只读导出，恢复到独立目录/端口，以免认证启动；导出前后正式库与隔离恢复库的七表完整记录按稳定字段顺序逐条比较，而非只比数量：meta 1、source 210、source_version 240、member 1539、node 22、semantic 194、change 2323，均逐字段相等。UUID 保持；238 份文字快照 hash 全部匹配，2 张图片的原字节与 hash 相等；样例快照原文、关系端点和真实共享向量查询已核，原库与恢复库 top 5 及距离完全一致。原生导出、assets、驱动、回执和日志在 `artifacts/runs/20261110-onboarding-simplification/auth/restore/`，恢复不需要重新总结或编码已有成员。

## 浏览器实测改变的风险判断

SurrealDB 4.0.0 以 `--unauthenticated --bind 127.0.0.1:18760 --allow-origin http://127.0.0.1` 启动；真实 Edge 157 页面分别来自允许 origin `http://127.0.0.1` 与不匹配的 `http://127.0.0.1:18762`。不匹配页面发送 `Content-Type: text/plain` 简单 POST，SQL 正文使用 `USE NS/DB` 后 CREATE；浏览器报 CORS `TypeError: Failed to fetch`，服务器直接查询却证明记录已经写入。允许 origin 读写成功。预检请求的不可读结果不被当成“请求已执行”的证据。

因此原生 `--allow-origin` 不能充当浏览器来源写权限边界；恶意网页也可能触达仅回环监听的免认证数据库。此事实已报主 agent，不能只凭缺少跨域响应头声称写入被阻断。完整请求、浏览器回执、数据库状态及实测版本在 `artifacts/runs/20261110-onboarding-simplification/auth/cors/`，主证入口为该目录 `result.json`。

## 状态与交接

隔离服务均已停止，18184 连接拒绝，正式 18080 `/ready` 保持 200。没有停止或切换任何正式项目，没有普通升级共用客户端，没有删除正式凭据。认证产品合同待用户选择；若继续免认证，正式三项目仍需独立迁移窗口与新旧客户端一致切换。

已知仓外审计发现 array/ppt 没有被删除 Python 接口的消费者；正式项目配置和生成入口仍有旧认证字段，另有 ppt 的 `scripts/basepack.ps1` 与 array 的手写项目说明读密码/提示。它们须按正式迁移授权同步处理。`D:/AgentTools/basepack.toml` 的旧 `[shared].state_dir` 不在本轮正式设施修改范围。普通 wheel/new shell 和完整回归由主 agent 的验证分支接续；F 聊天采集、E 维护与 C 的 memory 输出接口另看记忆结果，不能由本报告推定完成。

运行原证包含项目原文与知识，均在 Git 忽略的 artifacts 中；归档范围、hash 及服务状态见 `artifacts/runs/20261110-onboarding-simplification/auth/manifest.md`。临时工作在 `tmp/20261110-onboarding-simplification/auth-*`，可清除；不提交数据、原生导出或数据库目录。
