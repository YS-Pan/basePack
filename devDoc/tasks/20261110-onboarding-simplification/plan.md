# 接入闭环与运行简化修改计划

2026-11-10（北京时间）。状态：待实施；本轮只制定计划，不修改产品、安装、正式数据库或外部项目。实施范围与取舍以本文为准，状态在 [进度](progress.md) 接续。

## 依据与当前基线

- [技能发现调查讨论](codex://threads/01a1c54c-f714-7601-b442-22db64e27948)及[调查报告](../20261106-rebuild/research/array-skill-discovery.md)：array reconstruct 的旧版迁移复制了技能原件，但遗漏 `.agents/skills/` 发现入口；当前 `init`、core doctor 也不安装或验收独立技能。完整外部安装说明是在迁移之后补入的，不能倒推当时已有该流程。
- [冗余与密码评估讨论](codex://threads/01a1c556-ef6d-7b32-8c84-f8878a31ed05)：提出配置无关命令、双返回格式、失用配置/接口及重复编码逻辑的简化；最后只评估了可信本机免认证，尚未授权或执行数据库切换。
- 当前 main 为 `8fa500d`，源码及共用客户端为 0.7.1。[整改结果](../20261110-rectification/result.md)已交付删除纯 text 模式、三个项目迁移和普通 wheel 回归。本文以此为基线；保留 vector、hybrid 与 `hybrid --literal`，不重复实施已完成项。
- 本轮共读当前生产代码、调用方、测试与文档，确认下列候选仍存在。仓外 Python 脚本对旧返回格式和旧接口的依赖尚未核实。
- 接续用户质疑完成[自动维护调查](research/memory-maintenance-audit.md)：确认派工/判断遗漏、426项的实际含义和来源，并原生复现来源基准前移后的维护发现盲区。建议先按该报告第5节纠偏维护派工、澄清输入与完成信号，再接续本计划；调查与拟修正不代表产品已修复。

## 目标与范围

完整项目接入应使所选技能可被宿主发现；新 shell 使用记忆无需手工装载密码；命令只加载实际需要的配置；检索输出与内部编码逻辑各保留必要的合同。

拟将数据库收敛为**可信本机、仅回环监听、免认证**这一种运行方式，删除产品密码机制。该方案意味着能连接端口的本机程序具有数据库管理权限；项目 UUID 负责防误连。此处记录拟实施取舍，现行带密码流程在实施前继续有效。

保留独立技能的维护位置与按需使用、项目独立数据库与 UUID、原生备份、已发布快照回源、版本标识、stale/retired、向量补建及 jobs 的 run/submit/wait。项目纲领正文保持原文。

## A．补齐技能接入闭环

1. 在[项目接入](../../../experiments/20261106-basepack/docs/setup-project.md)加入完整步骤：选择所需技能 → 安装完整目录或建立项目内发现联接 → 核对入口与引用 → 核对宿主实际发现。`init` 生成程序接入材料，core doctor 检查其既有范围；两者成功不代表独立技能已安装。
2. 通用技能仍从根 `skills/` 获取，resources 从实验工程获取；保留现有 wheel 合同。新项目优先把所选完整目录放入 `.agents/skills/<name>/`。已有 `skills/<name>/` 维护原件的项目建立指向它的 junction，保持一个维护源。
3. 重复执行先核已有目录及目标；正确入口直接复用，同名用户技能或不同目标联接保留原状并报告冲突。说明复制目录随项目保存，忽略的本机 junction 在新检出后需重建。只用 wheel 的使用者另取配套源码中的独立技能，无需因此重装客户端。
4. 同步根 README、路线 README 与接入说明，修正路线 README 的“两项通用 skills”；将 resources skill 中复制后失效的 `../../docs/...` 改为仓库公开文档链接。随包记忆 skill 继续由 `memory guide` 和 instructions 直接到达。
5. 外部修复方案：在 array reconstruct 已有两项原件上补 `.agents/skills` 入口，沿该项目约定记录及核对实际发现。新增加的 engineering-judgment 是否选用独立决定，不因本次修复自动加入。

**完成条件：** 所选技能文件及同目录参考完整，指针可达；真实目标项目的宿主列表或新聊天显示所选技能的名称与项目作用域。宿主结果不可取得时如实记为待核。这里验收安装与发现，不安排技能行为、触发、效果、收益或专门测试项目。

本批采用现有复制/联接方式和实际宿主验收，不新增安装平台、技能清单状态、默认全装或 wheel 打包机制。

## B．删除产品密码机制

### 实现与文档

1. 在唯一配置边界限定 memory endpoint 为明确的回环地址，launcher 显式使用回环 `--bind` 和 `--unauthenticated`。禁止把免认证服务绑定到通配或局域网地址；共享 embedding、Condor 的认证与部署合同不在此次改动内。
2. 删除 `memory.username/password_env/password_file` 模板字段、`ProjectConfig.memory_password_file`、config show 对应输出、客户端 Basic Authorization 及只服务于它们的导入和测试分支。同步 launcher 中的 SURREAL_USER/PASS 设置。
3. 将 `memory init` 生成入口缩短为显式 Python、绝对配置与一次 brief 调用，保留 UTF-8 和原始失败。删除新 shell 读取配置再加载凭据的桥接；更新随包 memory skill、两级 README、接入/管理员/记忆文档及现行 system 说明。
4. 用 SurrealDB 原生 `--allow-origin` 收紧默认跨域范围，并验证实际浏览器请求行为。CORS 不能代替访问认证；不能只凭缺少响应头宣称写请求已被阻断。仅可信本机使用的边界须写在部署动作旁。

官方已提供[免认证模式](https://surrealdb.com/docs/reference/cli/db/commands/start#unauthenticated-mode)和[监听与 CORS 参数](https://surrealdb.com/docs/reference/cli/db/commands/start#command-help)，本机 SurrealDB 4.0.0 帮助也已核对。免认证下 guest 具备 root OWNER 权限。现有库读写、导出及浏览器行为本轮未实测。

### 迁移顺序

1. 先在一次性库验证无凭据 init → apply → brief/search/read/neighbors，以及原生 export/import；再用既有版本备份恢复集合，保留旧 wheel、配置、launcher 和必要回退凭据。
2. 将一个现有库的原生导出恢复到独立目录/端口，验证免认证后的旧快照、图、图片和兼容向量。核对 UUID 及七表（meta/source/source_version/member/node/semantic/change）逐记录逐字段，不能只比计数。
3. 确认共用客户端的全部在用项目和调用方，安排每项目短暂停写。先停止自动维护及相关调用，再停止该项目数据库进程；确认监听和进程树退出后，以原 store、原 UUID 和免认证 launcher 重启。一次只迁一个项目，不并行打开同一 store。
4. 在受控迁移窗口普通升级共用客户端，删除在用配置的旧凭据字段并刷新入口；新旧客户端与服务认证方式必须在业务恢复前一致。失败保留原错，按已保留的 wheel/配置/launcher 回退，不通过清库重建绕过。
5. 新进程在无密码环境变量、无运行时密码文件的条件下读写成功后，再恢复业务。确认回退资料后移除原在用密码文件；历史备份中的恢复材料按其保留约定管理。保留原 UUID、目录、知识、ID、来源、快照及 stale/retired 状态，无需重新建库、总结或编码未变向量。

**完成条件：** 上述无凭据闭环、原生恢复、误连 UUID 拒绝和非回环 endpoint 拒绝均有实证；新 shell/新聊天可直接 brief；正式项目数据保持，回退路径可定位。产品只保留免认证合同，不再新增自动找密码或双认证模式。

## C．收敛命令、输出与失用接口

| 项目 | 修改与主要位置 | 完成条件 |
| --- | --- | --- |
| 无配置工具命令 | `src/basepack/__main__.py` 在配置解析之前分派 `memory guide/rank/stop`；`memory/cli.py` 保留它们的实际职责 | 不传 config，或无关配置文件不可用时，三项仍按自身输入完成；需要项目的命令继续明确要求 config；坏评分文件/控制文件错误保留 |
| 检索返回合同 | `memory/vectors.py`、store 包装及 CLI 删除 `include_coverage`，统一 `{matches, vector_coverage}` | vector/hybrid、空库、无兼容索引和 literal 的既有语义保持；仓内调用与样例统一读取 matches |
| brief 输出 | 删除恒空 `changes/change_count` 和重复 `vector_pending/vector_pending_count`，清理 coverage 必赋值后失用的 None 分支 | 保留 `vector_coverage` 的总量、兼容量、待建量与定位，以及知识 pending、coverage_gaps 和 `change_check`；保持现有明细范围，brief 继续不扫描原件 |
| 无消费者的状态目录 | 删除 `MachineConfig.state_dir`、模板 `[shared].state_dir`、describe 回显及对应测试；修正 system/diagrams 的失真连线 | 删除后 embedding 与 jobs 仍使用实际配置的日志/产物位置；不搬日志或机器目录 |
| 失用当前原件读取接口 | 删除 `memory/content.py` 的 `MemberContent/read_member` 及专属测试 | 保留 read_source 等 prepare 所需能力；改用真实快照读取回归证明原件改写/删除后仍可读指定旧版本 |

本表源码相对 active 工程。修改同步到受影响的产品与 system 文档，历史结果保留其版本条件。Python 旧调用方需按新的返回合同修改；先查已知外部使用记录，升级说明列出删除的字段和接口，不保留无人使用的兼容包装。底层文字匹配仍供 hybrid 使用。

## D．合并编码调用中的实际重复

在 B/C 接口稳定后，仅提取 `candidate_vectors.py` 与 `vectors.py` 共同的“一批输入调用服务并核对 identity/返回数量”逻辑，必要时共用文字/图片输入构造。先确认净减少重复和维护位置，再决定是否提取；两行分批循环无需单独框架。

候选发布继续检查任务 stop、修改候选字典并在 apply 中原子提交；`memory embed` 继续用 SQL 筛兼容成员、核原图 hash、独立更新向量并返回 embedded/reused/pending。原 HTTP 错误及所属批次上下文保留；两套事务和回执各归其 owner。

**完成条件：** 模型身份变化、缺失/错数量、已有向量复用、图片补建、编码期间 stop 和过期候选冲突的已有行为回归通过。若合并反而增加模式参数或跨层状态，本批保留必要重复并记录理由。

## 实施组织、检查与交付

主 agent 负责最终契约、跨文件整合、普通安装及 main 提交。A 可由文档/接入 owner 独立推进；B 的配置、存储和入口由一个 owner 贯通，C/D 接续同一记忆 owner，避免并写 cli/config/store。外部项目修复与数据库切换沿对应项目授权和记录约定执行；实施后在原技能调查处补结果指针，保留调查当时的事实。

建议按 A → B → C → D 分为可独立完成的提交；A 与 B 的准备可并行。每批完成相关检查后在 main 提交实现、文档与 change_log，保留用户已有改动。没有实际收益的 D 可以据证据不做。

- A：核完整目录、引用、目标项目入口与实际宿主发现；遵守独立 skill 不做效果测试的既定要求。
- B：先隔离免认证闭环与旧库恢复，再做正式迁移；保留真实密码机制删除所需回归，含新 shell、UUID 误连和非回环拒绝。
- C/D：运行受影响的配置、CLI、快照、向量、发布停止与原生恢复回归；删除只保护失用接口的测试，保留它们仍有价值的行为覆盖。
- 最终构建普通 wheel，在源码外核导入位置与相关完整回归；用新项目和迁移项目各走一次真实记忆流程，记录所用设施、跳过项和未核范围。不重做已交付的 CPU/CUDA 性能或技能收益对照。

实施时同步 system/deployment、overview、memory/resources 模块及 diagrams 中实际改变的合同，更新本任务进度与重建总入口；必要新源码/测试登记 source_scope。临时材料放 `tmp/20261110-onboarding-simplification/`，选留原证归 `artifacts/runs/20261110-onboarding-simplification/`，结果记录版本、行为证据、限制与回退位置。远端发布按届时明确指令处理。
