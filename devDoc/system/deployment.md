# 项目配置与部署合同

更新：2026 年 11 月 11 日。当前唯一 active 路线为 [20261106-basepack](../../experiments/20261106-basepack/README.md)，源码面向 0.9.0。本文维护代码、业务实例、共享设施与升级边界。本机稳定客户端已通过普通 no-deps 安装升级为 0.9.0，42 个安装文件与最终 wheel 字节一致；本项目沿用原 UUID 和知识，刷新入口后经新的 NoProfile PowerShell 验证 brief。本轮未验收其它项目的 0.9.0 功能，安装与保留数据证据见 [本轮进度](../tasks/20261111-memory-worker-prompts/progress.md)，实测和历史观察见 [环境记录](environment.md)。共享资源基线见 [R9 结果](../archive/20261107-resource-coordination/r9-result.md)。操作从路线 README、[项目接入](../../experiments/20261106-basepack/docs/setup-project.md) 和 [管理员说明](../../experiments/20261106-basepack/docs/administrator.md) 进入。

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

根 file-structure、agent-team、engineering-judgment 独立维护，resources skill 归 active 实验。memory skill 与英文 coordinator/reader 提示词随包安装，分别通过无需配置的 `memory guide` 和显式配置的 `memory prompt` 使用；提示词渲染不要求数据库、密码文件或模型在线。独立技能选择完整目录复制到项目 `.agents/skills/`，或联接已有项目原件；同名冲突保留并报告，正确入口复用。`init` 与 core doctor 不安装或验收它们；忽略的本机联接在新检出后重建，核宿主实际发现。开发环境、构建缓存和夹具在根 tmp，交付及回滚 wheel 在实验 dist，选留原证在根 artifacts/runs；寿命见 [文档约定](../documentation.md)。

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
      password.txt               默认唯一密码文件，忽略并受控备份
      store/                     本机原生 SurrealKV 目录
      assets/                    按 hash 保留的必要原图版本
      codex/                     受管聊天 UTF-8 原文导出
      codex-attachments/         可读取的受支持聊天原图，按 hash 保留
      maintenance/               机械/语义/聊天采集回执
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
| memory.endpoint/namespace/database | HTTP(S) 显式回环 IP（127/8 或 ::1），拒绝域名/通配/远端及额外 URL 成分；逻辑库不代替物理隔离 |
| memory.username/password_file | 用户名及唯一 UTF-8 密码文件；路径相对项目根或绝对，省略时为 memory_dir/password.txt |
| memory.project_id/source_scope | 随项目保留的 UUID；source_scope 在 Git 项目中增加显式包含项，在非 Git 项目中声明新文件发现范围 |
| memory.codex.project_id/other_project_roots/registry_complete | Codex 宿主项目绑定和完整注册根证据，独立于 basePack UUID；未取得时明确聊天缺口 |
| memory.search_mode | CLI 未显式传 --mode 时采用的 hybrid/vector；新项目默认 vector |

`memory guide/rank/stop` 只处理自身输入，在项目配置解析前分派。机器配置不再维护无消费者的 `[shared].state_dir`；模型日志由 SCM/Shawl 服务定义中的显式路径管理，jobs 材料仍归项目 jobs_dir。

机器 embedding 节沿用 R9 endpoint、service_name、queue_timeout 及模型/预算设置。客户端以 username 和自动读取的 password_file 建立 Basic Authorization；config show 返回 memory_password_file 绝对路径而不读取或显示 secret。password_env 与手工 shell 桥退出。instructions 保留固定 Python、绝对配置和 brief 调用；guide/rank/stop 不读配置或凭据。project_id 随移动或恢复保留，误连另一身份的库会失败。config show 和 doctor 只作诊断，不能替代真实功能验收。

## 环境与服务

依赖由 pyproject.toml 与 uv.lock 维护，CUDA 来源明确。系统环境不做清理式同步，共享服务环境不安装无关 MCP 集成。源码与 wheel 验证分别核导入位置；普通安装从源码外运行。

共享 embedding 沿用 Shawl/SCM，Manual、LocalSystem、no-restart/kill-process-tree；LitServe 单 worker 常驻，客户端超时只结束等待。项目 SurrealDB 可沿用已有普通用户隐藏手动认证进程。cwd、原生 store、日志与启动材料在项目 memory 目录；serve.ps1 从同一配置取得显式回环地址、username 和密码文件，设置原生认证入口后调用稳定 exe，不启用 unauthenticated。新库一次安全随机生成文件，已有库缺文件时恢复原凭据；launcher 不生成密码。SCM 是管理员可选方式，本轮未配置。basepack 只连接，停止项目库不停止共享模型。

改写密码文件不会轮换数据库内的存储账户；轮换由管理员显式更新账户并同步同一文件。访问和认证失败保留原错，客户端不回退无认证。操作见 [管理员部署](../../experiments/20261106-basepack/docs/administrator.md#项目-surrealdb)。

搬迁先停止该项目库并确认进程退出，再移动完整项目、调整启动 cwd/日志/endpoint，保留 UUID 后复核。在线备份使用原生 export；恢复集合含 export、配置、原凭据文件、业务原件、受管聊天导出、codex-attachments 原件与定位回执、必要 assets。已接受语义与更正必须恢复，向量可以从保留表示重建。长期备份位置和保留周期由业务项目确定，Git 忽略和本机目录不代替备份。

## 升级与回退

0.9.0 增加随 wheel 安装的英文维护模板与纯 `memory prompt` 渲染入口。默认 Git 清单加 source_scope 显式包含项取代仅按 source_scope 发现，非 Git 仍按声明范围；历史已登记及未接受来源保持全局接续。maintain 短结果增加发现边界、control 与协调者派工元数据，宿主按返回命令交接，刷新生成入口和自有包装。模型映射由项目 [ai] 解析，宿主实际设置；数据库 schema、原凭据、UUID、向量身份与共享服务沿用既有合同。安装、构建和真实使用结果分别按专项进度核实。

0.7.0 将查询与维护分离：查询读取已发布内容及依据快照，维护候选在所选模式的向量准备好后原子发布。知识表与项目/机器配置 schema 保持现有格式；升级保留 UUID、数据及显式检索模式，运行 memory init 刷新 schema 和生成入口。0.7.1 删除独立 text 模式；旧 text 项目复用或补齐兼容向量后切换 vector/hybrid，保留知识、ID 和来源。新项目默认 vector。

0.8.1 保留既有认证库和原用户名/密码文件，删除 password_env 手工桥。升级前备份 wheel、配置、密码文件和完整恢复集合，等待在途客户端调用结束后普通更新客户端，刷新 instructions 与自有包装。服务、物理目录、端口和 UUID 保持，通常无需重启或迁库；新 shell 直接核 brief/search/read/neighbors。失败按原错误恢复凭据或回退客户端，不清库、不重新总结。

0.8.0 将维护入口收敛为 `memory maintain` 的确定性预检与余下语义交接，默认读取 source_scope，采集可归属聊天后按来源接续。检索统一 `{matches, vector_coverage}`，Python 调用方需删除 `include_coverage` 并读取 matches；brief 删除 `changes/change_count/vector_pending/vector_pending_count`。删除无消费者的 MachineConfig.state_dir 和旧 MemberContent/read_member 原件接口，快照回源保持。独立 skills 仍从配套源码取得，未改 wheel 发行范围。

轻客户端要求 Python >=3.13，CPU/CUDA 模型依赖由各自 extra 选择。共享 embedding 的协议和语义身份未变，现有 0.5.0 CUDA 服务可继续运行；CPU 服务按自动设备选择启动，保持相同模型与 FP16。Condor 继续维护准入和排队，capacity 只作观测。更老项目缺少检索模式或 `[ai]` 时按[项目接入](../../experiments/20261106-basepack/docs/setup-project.md#版本升级)补齐。

升级保留新旧 wheel、配置和知识备份，核安装来源并在源码外验证受影响流程。底座或知识 schema 变化须验证原生恢复；回退客户端保留项目数据，旧资源版不提供记忆能力。只有服务实现或资源协议确需改变时，才按管理员流程排空、停止并切换相应服务。

0.4 → 0.5 的资源接口切换与回退见 [R9 结果](../archive/20261107-resource-coordination/r9-result.md)，旧 RPC 与取消/关闭协议已退役。更早 schema 1 项目先用保留的 0.4.0 显式 migrate，原配置和映射保留在各项目；历史迁移见 [R8 结果](../archive/20261107-resource-coordination/maintenance-result.md)。
