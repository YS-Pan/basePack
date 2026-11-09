# R8 维护与 0.4.0 部署结果

路径追溯（2026-11-09）：下文保留当时的运行路径；选留原证现归根 `artifacts/runs/<原批次>/`，原 dist 包现归 `experiments/20261106-basepack/dist/`，位置映射见[布局迁移结果](../20261109-project-layout/result.md)。

2026 年 11 月 8 日，按用户要求顺序完成 R8.0 → R8.1 → R8.2 → R8.3 → R8.4。当前状态只维护在 [进度](progress.md)，接口/路径与迁移合同见 [部署合同](../../system/deployment.md)。本轮没有修改项目纲领、机器容量、模型或 Condor 站点策略，没有推送远端。

## 源码交付

| 阶段 | 实际变化 | 检查与提交 |
| --- | --- | --- |
| R8.0 | JobSpec 用局部 cwd 副本；锁内拒绝重复活动 request_id | 跨项目复用、失败不变性、结果/取消/清理隔离；阶段全套 27 passed，9175b51 |
| R8.1 | project/ 唯一配置、初始化、诊断与模板；实例统一 .basepack/；按需读取功能节 | 深层配置、中文/空格、任意 cwd、业务指令及包根/模板；阶段全套 34 passed，dced9a4 |
| R8.2 | supervisor、Qwen3VLEmbedder、WorkerProcessOwner；transport/registry/identity/admin；机器管理入口 | 22 项 embedding 回归，阶段全套 51 passed，b698979 |
| R8.3 | jobs/CondorClient、schema 2/[jobs]；submit/_processes；单份 spec payload；wait 只观察 | 40 项 jobs 回归，阶段全套 74 passed，b256da8、bf90cfc |
| R8.4 | 显式 migrate、0.4.0 普通 wheel、项目迁移和产品/系统说明 | 配置/迁移 28 项，源码全套 92 passed；准备提交 aec4d44，部署证据如下 |

源码检查使用 `PYTHONPATH=src` 与仓库忽略目录的 pytest basetemp。临时目录 ACL 和受限 Condor SSPI/CIM 错误均保留；构建改用仓库内 TEMP/TMP，真实设施使用正常用户上下文，没有更改认证策略。阶段内按职责派工，主 agent 检查并提交；宿主未提供团队 token/主上下文计量，本轮不作成本比较。

## 普通安装与显式迁移

- wheel：`dist/basepack-0.4.0-py3-none-any.whl`，42319 字节，SHA256 `3322c8eebfcd0a12a4518639cf66e7a202fa76d6a47fa7b34be80cdecab15563`。
- 系统解释器：`C:/Program Files/Python313/python.exe`，包根 `C:/Program Files/Python313/Lib/site-packages/basepack`。30 份包文件与源码、wheel、安装逐字节一致，旧 config/setup/doctor、resources、broker/runtime/owned 源码入口不存在。
- 升级前实际队列为空，仅旧 broker 43200 存活且无模型 worker。使用仍安装的 0.3.0 API 停止并确认退出，随后通过 Windows 管理员令牌普通安装 0.4.0；没有混留 editable 或 user-site 安装。
- 六份已知源码外 basePack 试用配置显式迁移，原配置和宿主入口分别保存在所属项目 `.basepack/migration/<id>/files/`，mapping.json 保存映射。保留原解析项目根；不接管其他业务项目或旧数据库/授权。历史 artifacts 保留当时版本的证据，不作为活动调用方。
- 新验收目录 `D:/project/20261108-basepack-r8-acceptance/` 内两个项目使用默认与深层配置；中文/空格、任意 cwd、移动项目、只复制业务入口的新检出再 init 均通过。四份模板可从安装包读取，轻量操作不加载 Torch/Transformers/Pillow。
- 测试与必要 Condor 样例复制到源码外 verification/，以系统 Python `-I -m pytest` 验证普通安装，92 passed；源目录不在导入路径。

原始回执：`artifacts/r8/before.json`、`deployment.json`、`wheel-receipt.json`、`installed-files.json`、`installation-receipt.json`。源码与源码外 pytest 分别使用 `artifacts/r84-source-pytest/` 与验收目录 `verification/pytest/`。

11 月 8 日临时文件整理后，原 R8 验收目录收进本项目 `tmp/acceptance/20261108-basepack-r8-acceptance/`，测试夹具与构建缓存也移入 `tmp/`。长期复核所需的项目配置、图文输入输出、真实作业日志及迁移证据保存在 `artifacts/tmp-reorganization-20261108/evidence/`；完整源路径、临时位置和证据副本见 `artifacts/tmp-reorganization-20261108/moves.json`。历史回执不改写为新路径，已完成的验收结论保留原条件；临时目录清除后按证据副本复核。

## 实际功能与生命周期

| 场景 | 实际结果 |
| --- | --- |
| 冷加载隔离 | A 请求取消、另一 A 请求截止；B 排队后成功，同一模型 worker 存活 |
| CPU 14335.0 | sum(range(1000)) = 499500；中文、空格、引号及空参数完整，退出与回收成功 |
| 应用失败 14336.0 | 原始退出码 7 保留，业务回执和 stdout/stderr/events 均可读，回收确认 |
| GPU 14337.0 | CUDA 矩阵值 256、迭代进展与 Condor GPU 环境正确，完成后资源归还 |
| 联合 GPU 14338.0 | 4000 MiB 标准申请由 schedd 转为本站资源；wait 观察过期不撤销；真实图文 forward 期间有两条 CUDA 进展 |
| 图文结果 | 文本和合成图片均产生有限的 2048 维 L2 归一化向量；图片 hash、解码、缩放和视觉 token 回执正确 |
| 作业取消 | 14338.0 原生 removed、已知 PID 消失、日志和历史正确；关闭 A 客户端后 B 仍使用同一 worker |
| 已加载模型崩溃 | 只终止实时查询的 supervisor；Windows 所有权回收模型进程，登记锁释放；新 supervisor 冷恢复成功 |
| 正常停止 | 新管理入口停止已加载模型，supervisor/worker 均退出，marker 清理 |
| 空闲退出 | 未改 idle_seconds=300，真实模型空闲整进程退出；含加载的观察总计 308.7 秒，轻量 supervisor 保留 |

向量语义标识为 `Qwen3-VL:9b224ef380b04193c72819c7d13e689da1413739d3152e4a598e9ec6f13cc7ac`。部署指纹与协议身份独立，错代拒绝、启动身份固定、旧 marker 管理及语义/运行设置变化另有必要回归。

2026-11-08 17:07 北京时间最终检查：系统普通安装 0.4.0，supervisor 17804，无模型 worker，协议 1 且部署指纹匹配；Condor 队列为空，12 CPU、24576 MiB RAM、4 同卡名额和 7164 MiB 普通池全部归还。机器配置与 Condor 60/70 SHA256 与升级前相同，服务不是登录自启。

实际回执为 `artifacts/r8/runtime-receipt.json`、`lifecycle-crash.json`、`lifecycle-graceful.json`、`lifecycle-idle.json`、`final-state.json`；向量、业务产物、提交材料与日志留在各项目 `.basepack/`。小矩阵证明实际执行和资源记账，不代表分配全部申报显存或吞吐提升；额度/性能沿用未改变的 R6/R7 合同。

## 边界与后续

R8 无未完成验收项。旧 0.3.0 wheel 保留用于恢复；恢复步骤见 [管理员说明](../../../experiments/20261106-basepack/docs/administrator.md#升级与回滚)。完成历史 Condor ClassAd 保留原 BasePackPayload 绝对路径，迁址后的历史 status 不保证可用；通过备份、映射和日志回查，不将旧 payload 重新提交。

记忆数据库真实隔离和应用效果继续由 P1/P5 验收；本轮没有扩展记忆实现、通用后端或独立客户端发行版。远端推送和发布未执行。
