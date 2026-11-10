# 安装与操作文档整改

本分支修改 [管理员说明](../../../experiments/20261106-basepack/docs/administrator.md)、[项目接入](../../../experiments/20261106-basepack/docs/setup-project.md)，并同步 [资源使用](../../../experiments/20261106-basepack/docs/resources.md) 与 resources skill 的 embedding 条件。记忆、jobs 与路线入口由各自 owner 集成；未升级客户端、修改正式服务或运行 skill 测试。

## 结果与职责

- 接入按生成配置、选择检索能力、启用独立数据库、一次实际检索组织；既有项目新 shell 加载凭据后直接查询，doctor 留在首次接入和设施变化时。
- 管理员维护服务账户、共享 CPU/GPU 预算和 Condor 站点策略；普通用户运行所选功能的一次编码或小作业。兼容回归、跨设备检索与峰值研究留在开发任务。
- 依实现合同写明新项目默认 vector、显式 text、旧 text 库先补向量再切换；查询只读已发布知识，维护从独立入口执行。0.7.0 升级执行 memory init 刷新 schema/入口，保留项目 UUID。
- CPU/CUDA 使用各自锁定 extra，auto 选择设备，同模型与精度复用索引。成功输出、连接/模型/认证失败动作和等待超时后推理仍可运行均在对应操作旁。
- 保留物理数据隔离、凭据不覆盖、同 store 单进程、进程树停止及原生 export/必要 assets/配置/业务原件恢复集合。

## 环境证据交接

以下来自整改前 `f8bb5b2:experiments/20261106-basepack/docs/administrator.md`，产品正文改为能力条件。环境维护由主 owner 接入 [现有环境文档](../../system/environment.md)；已经保留的证据无需重复抄写。

| 原位置 | 原事实与归属 |
| --- | --- |
| L11、L12、L19 | Python 3.13.17、uv 0.13.7，以及固定 uv 安装脚本；历史工具版本 |
| L16、L141 | 驱动 617.42、RTX 4060 Ti、16380 MiB；其它 GPU/最低显存未取得当时验收，属于观测范围 |
| L141 | CUDA 12.8 发行说明所列 Windows 驱动 570.65；这是旧官方引用，非本机观测 |
| L221 | 作者机样例 12 CPU、24576 MiB RAM、4 个同卡名额、7164 MiB 普通显存池；现有环境/R6/R7 已有对应记录 |
| L297 | LitServe 0.2.19 原生 `/shutdown` 在 Windows 小试有进程残留；SCM/Shawl 停止选择的历史依据，见 R9 |

## 检查与未决

最终静态范围为本轮未提交的 19 个 Markdown（`git diff --name-only -- '*.md'` 加本次新增结果），UTF-8、241 个本地链接/标题锚点和 40 个 PowerShell 代码块 AST 语法均通过。命令/输出字段与各模块源码及 owner 合同核对，本分支 Markdown 差异无空白错误。未执行文档中的安装、启动、作业命令或任何 skill 行为测试。

记忆源码整合 246 项、共享模型 3 项及恢复 1 项检查已通过；[记忆结果](memory-result.md) 维护查询、快照与发布依据。[embedding 结果](embedding-result.md) 维护 Python 普通安装、CPU 实推与双向跨设备索引复用证据和适用范围。最终普通 wheel 由主 owner 整合验证，文档静态检查不作为产品功能验收。
