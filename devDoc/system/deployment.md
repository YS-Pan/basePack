# 项目配置与部署合同

更新：2026 年 11 月 10 日。当前唯一 active 路线为 [20261106-basepack](../../experiments/20261106-basepack/README.md)，源码面向 0.7.1。本文维护代码、业务实例、共享设施与升级边界；正式记忆安装状态见 [专项进度](../tasks/20261106-memory-system/progress.md)，共享资源基线见 [R9 结果](../archive/20261107-resource-coordination/r9-result.md)。操作从路线 README、[项目接入](../../experiments/20261106-basepack/docs/setup-project.md) 和 [管理员说明](../../experiments/20261106-basepack/docs/administrator.md) 进入。

## 位置与责任

| 内容 | 维护与运行责任 |
| --- | --- |
| 源码、依赖锁、模板、测试、产品文档、样例及产品 skill | 唯一维护源为 experiments/20261106-basepack；运行代码以普通 wheel 安装 |
| 项目配置、详细 instructions、项目知识和产物 | 属于对应项目，集中于其 .basepack/；业务原件沿业务布局 |
| 模型及 model.lock.json | 共享设施按组织/模型/revision 保存，多项目共用权重 |
| 机器配置 | 一份 schema 1 TOML，保存显式模型路径、服务地址与资源设施位置 |
| embedding 服务环境 | 独立共享 Python 3.13 环境，使用兼容 wheel 与锁定依赖，运行时不依赖源码或 tmp；0.6 客户端可沿用 0.5 服务 |
| SurrealDB 程序与项目库 | 官方发行 exe 可共用；每项目独立进程、端口与项目内物理目录，多聊天共用该项目进程 |
| 运行托管与日志 | 共享模型沿用 Shawl/SCM；项目库可由普通用户手动启动，也可选管理员 SCM；日志分别保存 |
| 普通作业容量与策略 | HTCondor 独立安装并唯一维护 |

本机共享服务沿 R9 使用 `C:/ProgramData/basepack/envs/service/`、`D:/AgentTools/bin/shawl-1.9.0/shawl.exe` 与 `D:/AgentTools/state/basepack/embedding/logs/`。SurrealDB 4.0.0 exe 位于 `D:/AgentTools/bin/surrealdb-4.0.0/surreal.exe`，项目各自保存数据库。本机客户端普通安装在稳定的 `D:/AgentTools/envs/basepack-client/`，系统 Python 与 0.5.0 共享模型环境保持原状；图文依赖仍在共享环境；当前客户端升级不要求重启兼容的 0.5 模型服务。这些是本机位置，公共代码通过配置定位设施；实测见 [环境说明](environment.md)。

根 file-structure、agent-team、engineering-judgment 独立维护，resources skill 归 active 实验，memory skill 随包安装并由 memory guide 定位。开发环境、构建缓存和夹具在根 tmp，交付及回滚 wheel 在实验 dist，选留原证在根 artifacts/runs；寿命见 [文档约定](../documentation.md)。

## 业务项目实例

```text
业务项目/
  AGENTS.md                      业务规则及 .basepack/instructions.md 短指针
  .gitignore                     忽略 /.basepack/
  .basepack/
    config.toml                  显式选择的项目配置
    instructions.md              实际 Python、配置与宿主操作入口
    jobs/                        提交材料、回执和作业输出
    memory/                      项目知识与维护材料
      store/                     本机原生 SurrealKV 目录
      assets/                    按 hash 保留的必要原图版本
      logs/                      项目数据库运行日志
```

init 从安装包模板生成配置和 instructions，保留业务内容并合并宿主短指针；memory init 再安装 schema、绑定项目 UUID 并加入 brief/skill 入口。支持 .basepack 内深层配置，project.root 按实际位置计算；调用显式传 config，不向父目录搜索。业务输出与明确指定的导出沿业务路径。

## 配置合同

项目格式保持 schema 2，机器格式保持 schema 1。各功能只读取自身所需节；当前模板是字段维护源：[project.toml](../../experiments/20261106-basepack/src/basepack/project/templates/project.toml)、[machine.toml](../../experiments/20261106-basepack/src/basepack/project/templates/machine.toml)。

| 字段 | 解析或维护责任 |
| --- | --- |
| runtime.python、runtime.machine_config | 明确绝对路径 |
| project.root | 相对项目配置文件 |
| ai.default_tier、ai.retrieval_tier、ai.tiers | 项目维护用途默认等级及各等级模型和推理强度；宿主读取后派工 |
| memory.data_dir、jobs.jobs_dir | 相对项目根，受管理数据必须在该项目 .basepack 内 |
| 机器配置中的相对设施路径 | 相对机器配置文件 |
| embedding.endpoint | 显式共享 HTTP 地址，本机为 loopback 8765 |
| memory.endpoint/namespace/database | 显式项目原生数据库；逻辑库不代替物理隔离 |
| memory.project_id/password_env/source_scope | 随项目保留的 UUID、客户端凭据变量名和可选新增资料检查范围 |
| memory.search_mode | CLI 未显式传 --mode 时采用的 hybrid/vector；新项目默认 vector |
| memory.password_file | 可选密码文件，相对项目根或绝对路径；省略时为实际 memory_dir/password.txt |

机器 embedding 节沿用 R9 endpoint、service_name、queue_timeout 及模型/预算设置。凭据只通过环境交给客户端与原生进程，机器引导及秘密文件不进入源码。project_id 随移动或恢复保留，误连另一身份的库会失败。config show 和 doctor 只作诊断，不能替代真实功能验收。

## 环境与服务

依赖由 pyproject.toml 与 uv.lock 维护，CUDA 来源明确。系统环境不做清理式同步，共享服务环境不安装无关 MCP 集成。源码与 wheel 验证分别核导入位置；普通安装从源码外运行。

共享 embedding 沿用 Shawl/SCM，Manual、LocalSystem、no-restart/kill-process-tree；LitServe 单 worker 常驻，客户端超时只结束等待。本项目 SurrealDB 以普通用户隐藏手动进程运行，cwd、原生 store 与启动材料均在项目 memory 目录，loopback 18080 供多个聊天共用。serve.ps1 从本机 password.txt 读取环境后调用稳定 exe，产品不增加凭据 provider。SCM 是管理员可选方式，本轮未配置。basepack 只连接，停止项目库不停止共享模型。

搬迁先停止该项目库并确认进程退出，再移动完整项目、调整启动 cwd/日志/endpoint，保留 UUID 后复核。在线备份使用原生 export；恢复集合含 export、配置、业务原件与必要 assets。已接受语义与更正必须恢复，向量可以从保留表示重建。长期备份位置和保留周期由业务项目确定，Git 忽略和本机目录不代替备份。

## 升级与回退

0.7.0 将查询与维护分离：查询读取已发布内容及依据快照，维护候选在所选模式的向量准备好后原子发布。知识表与项目/机器配置 schema 保持现有格式；升级保留 UUID、数据及显式检索模式，运行 memory init 刷新 schema 和生成入口。0.7.1 删除独立 text 模式；旧 text 项目复用或补齐兼容向量后切换 vector/hybrid，保留知识、ID 和来源。新项目默认 vector。

轻客户端要求 Python >=3.13，CPU/CUDA 模型依赖由各自 extra 选择。共享 embedding 的协议和语义身份未变，现有 0.5.0 CUDA 服务可继续运行；CPU 服务按自动设备选择启动，保持相同模型与 FP16。Condor 继续维护准入和排队，capacity 只作观测。更老项目缺少检索模式或 `[ai]` 时按[项目接入](../../experiments/20261106-basepack/docs/setup-project.md#版本升级)补齐。

升级保留新旧 wheel、配置和知识备份，核安装来源并在源码外验证受影响流程。底座或知识 schema 变化须验证原生恢复；回退客户端保留项目数据，旧资源版不提供记忆能力。只有服务实现或资源协议确需改变时，才按管理员流程排空、停止并切换相应服务。

0.4 → 0.5 的资源接口切换与回退见 [R9 结果](../archive/20261107-resource-coordination/r9-result.md)，旧 RPC 与取消/关闭协议已退役。更早 schema 1 项目先用保留的 0.4.0 显式 migrate，原配置和映射保留在各项目；历史迁移见 [R8 结果](../archive/20261107-resource-coordination/maintenance-result.md)。
