# 记忆整改结果

2026-11-10，源码版本以本轮提交为准；普通 wheel、跨设备及宿主生命周期核验由整合工作继续。测试使用隔离临时数据库，不访问正式项目数据库。

## 当前证据

- prepare 接受项目相对文件，目录入口报错并指导枚举；数据库实际 HTTP 413 保留原异常，附唯一序列化请求字节数与手动分批要求。隔离 HTTP 服务及 content 相关回归 18 项通过。
- 查询读取已发布知识和依据快照，brief 不扫描或触发维护；旧文字与图片版本按保存的来源版本及位置回读。隔离 SurrealDB 4.0 上 store 与快照回归 13 项通过，覆盖文字/图片、稳定 ID 复用后的旧行号、跨来源、缺快照和退役过滤。
- text 库补建、部分覆盖、按默认 vector 的 brief/search、继续补齐，隔离 SurrealDB 与模拟编码下 4 项通过；覆盖、identity 切换、补建及 record ID 回归 40 项通过、1 项可选真实模型跳过，CLI/config 等模拟回归 65 项通过。相同 identity/revision 而向量缺失时会补建。真实 CPU/CUDA 互用、普通安装与完整回归由整合验证，不以模拟编码代替。
- 宿主维护入口使用任务独有 control 文件同步停止与提交资格；候选编码及版本核对在事务前，内容和匹配向量同批提交。实际宿主探针在 19141 隔离库让 worker 阻塞于编码，业务侧 stop 在 226 ms 返回且不等待编码；`interrupt_agent` 返回前状态为 running。随后释放编码并读取，仍为旧已发布证据，worker 进程已不存在。控制结果与查询记录位于 `tmp/rectification-memory/host-probe/stop-result.json`、`after.json`，脚本为同目录 `host_probe.py`；独立 SurrealDB 4 的维护与发布回归 17 项通过，覆盖编码阻塞时 stop/原件变化不发布、内容向量同事务及复用、changes 与新接受交错、仅登记更正和退役；完整产品回归由整合继续。

隔离测试服务为 `tmp/rectification-memory/start-test-surreal.ps1` 所启动的临时内存实例，结果不涉及正式数据库或共享服务。工具模型、token 和费用不可核；未进行 skill 测试或对照。
