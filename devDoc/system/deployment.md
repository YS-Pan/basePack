# 项目配置与部署合同

更新：2026年11月18日。唯一active路线为[20261106-basepack](../../experiments/20261106-basepack/README.md)。本页是实际安装版本、wheel与验收状态的唯一维护源：当前普通安装0.18.1[behavior]，同批真实材料复验进行中，不能据提示词修订宣布缺口已闭合或178范围已完成。正式18080/store-0.17、memory schema 3和共享embedding 0.15保持。业务处置与余项见[进度](../tasks/20261115-real-use-rectification/progress.md)，原证与执行过程见[实施记录](../tasks/20261115-real-use-rectification/execution.md)；0.16既有验收见[整改结果](../tasks/20261115-real-use-rectification/result.md)。操作从路线README、[项目接入](../../experiments/20261106-basepack/docs/setup-project.md)及[管理员说明](../../experiments/20261106-basepack/docs/administrator.md)进入，修改配置按[维护要点](../../experiments/20261106-basepack/docs/project-config-maintenance.md)同步。

## 位置与责任

| 内容 | 维护与运行责任 |
| --- | --- |
| 源码、依赖锁、模板、测试、产品文档、样例及产品 skill | 唯一维护源为 experiments/20261106-basepack；运行代码以普通 wheel 安装 |
| 项目配置、详细 instructions、项目知识和产物 | 属于对应项目，集中于其 .basepack/；业务原件沿业务布局 |
| 模型及 model.lock.json | 共享设施按组织/模型/revision 保存，多项目共用权重 |
| 机器配置 | 一份 schema 1 TOML，保存显式模型路径、服务地址与资源设施位置 |
| embedding 服务环境 | 独立共享 Python 3.13 环境，使用兼容 wheel 与锁定依赖，运行时不依赖源码或 tmp；新服务行为须部署对应包并重启后生效 |
| SurrealDB 程序与项目库 | 官方发行 exe 可共用；每项目独立进程、端口与项目内物理目录，多聊天共用该项目进程 |
| 运行托管与日志 | 共享模型沿用 Shawl/SCM；项目库可由普通用户手动启动，也可选管理员 SCM；日志分别保存 |
| 普通作业容量与策略 | HTCondor 独立安装并唯一维护 |

本机共享服务沿R9使用`C:/ProgramData/basepack/envs/service/`、`D:/AgentTools/bin/shawl-1.9.0/shawl.exe`与`D:/AgentTools/state/basepack/embedding/logs/`；SurrealDB4.0.0 exe为`D:/AgentTools/bin/surrealdb-4.0.0/surreal.exe`。2026-11-18核对，本项目稳定Python `D:/AgentTools/envs/basepack-client-0.10/Scripts/python.exe`已普通安装0.18.1[behavior]，目录名不表示包版本；当前wheel SHA256为`cf8f36029941925d0fa22328810bf5c8d96196ebf18f08243c189d90cd2a7047`。69个源码／wheel／实际site-packages文件的文件集及字节一致，pip check与136项prompt检查通过。该补丁修订defer、PowerShell .py helper及真实错误留痕指引，backend、schema与行为算法未变；安装通过不代替真实作者复验。

0.18.0真实小批已发布2来源／7成员，主任务逐项原文、版本、history及embedding metadata回读通过；另6无稿来源的37个gap没有持久化defer，连同已发布2来源的7个gap，现有metadata合计8来源、9成员、44个未匹配gap。依据代码和metadata推断它们会在后续重进semantic；尚未启动0.18.1新preflight，该结论不是实际重新入队观测。原wave已由父核通知恢复并close、固定closure已保存，原owner暂持有，准备同8来源复验；问题尚未证实修完，178范围未闭合。

此前0.18.0 wheel SHA256为`9ec178d95bfde63550f1696431866efb22cd7c4f9c7d49d2ac7abe70ae19117d`，源码提交a710e335；当时69文件三方字节一致、pip check与wave create help通过。全memory程序检查649 passed、6 skipped（1483.62秒），最后定向259 passed（8.91秒）；跳过2项原生导出及4项未启用共享模型专项，不据此宣称GPU专项重跑。纯文件宿主probe在该版已closed，由父按宿主事实完成通知恢复、owner=null；这是该轮结束截点，不能代替后续真实维护。

此前0.17.4 wheel的SHA256为`49e9884a11f7be85c78d3a41f2c9945144497376ce423cf1ecc7d57dcc9c50a9`，当时66个包文件逐字节一致、pip check通过。0.17.2同步等待、固定稿、范围和dispositions提示词合同；0.17.3新增共享prepare输出读取合同，139项相关测试及49项安装/渲染检查通过，实际读取效果沿后续阶段观察。0.17.4因实际reader误派新增完整spawn_arguments，最终139相关测试及142安装/渲染静态检查通过；后续干净小批4reader的requested与actual均为Luna/max，4批发布完成9来源，uv.lock部分留续；该样本不保证所有未来host调用。0.17.1修复历史pin闭包，其wheel SHA256为`cd9c12b9b590c8b95f95eada65319b56e4344e9a84db0b96fbdc9142bb80d4bb`，当时65文件逐字节一致、pip check及原失败语义稿freeze通过。0.17.0首次wheel SHA256为`902aaec7f5e426f35636b063fac2939d23fc714a67eadee360cdfd744aea216f`，源码提交`9d3e479`及此前记录提交`73613d7`保留为历史样本。实际修复与维护进展见[实施记录](../tasks/20261115-real-use-rectification/execution.md)，推广事实见[迁移结果](../tasks/20261115-real-use-rectification/migration-result.md)。共享embedding仍为0.15.0/PID31000，未重启或更换模型，原identity、依赖版本和Shawl定义沿用。

本项目正式`.basepack/config.toml`现连接18080及`.basepack/memory/store-0.17`，launcher PID 48740、数据库PID 115116。旧`.basepack/memory/store-0.13`保留但不运行；旧18174及临时18176端口均已关闭。保留的`.basepack/staging-0.17.toml`仅将endpoint改到18080，data_dir仍为本项目`.basepack/memory`，不再表示独立暂存服务。普通memory init已刷新受管根入口，块外业务正文按迁移结果保留。切换前后、init后及配置指针修改后均为J=compiled J=2、C=26、模型`3c69a1307fa077bfb0860ff26277bb78daec95c92afa2aa699fc673d3e64791f`且owner=null；没有合成交付或重训。独立只读验收通过brief、8250/8250兼容内容向量、文本/图片回读、history与实际图边neighbors。首批100候选实际维护已完成，完整全项目维护及其最终恢复点尚待完成。其它项目共用的`D:/AgentTools/envs/basepack-client/`及其数据库未代迁；公共代码通过配置定位，不写死这些本机位置。

根 file-structure、agent-team、engineering-judgment 独立维护，resources skill 归 active 实验。memory skill 与英文角色提示词随包安装；`memory guide`无需配置，显式配置的`memory prompt`只渲染唯一协调者，`memory wave worker-prompt/task-prompt`按本地wave／固定任务渲染Luna指令。这些只读渲染入口不要求数据库、密码文件或模型在线。独立技能选择完整目录复制到项目 `.agents/skills/`，或联接已有项目原件；同名冲突保留并报告，正确入口复用。`init` 与 core doctor 不安装或验收它们；忽略的本机联接在新检出后重建，核宿主实际发现。开发环境、构建缓存和夹具在根 tmp，交付及回滚 wheel 在实验 dist，选留原证在根 artifacts/runs；寿命见 [文档约定](../documentation.md)。

## 业务项目实例

```text
业务项目/
  AGENTS.md                      业务规则及basePack关键动作/详情链接
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
      behavior/                  0.17不可变行为模型，<sha256>.json，纳入恢复集合
      maintenance/               owner、稳定控制及机械/语义/采集回执
      logs/                      项目数据库运行日志
```

init 从安装包模板生成配置和 instructions，保留业务内容并合并AGENTS关键动作；memory init安装schema、绑定原UUID并刷新两份托管入口。支持 .basepack 内深层配置，project.root 按实际位置计算；调用显式传 config，不向父目录搜索。业务输出与明确指定的导出沿业务路径。

## 配置合同

项目格式保持 schema 2，机器格式保持 schema 1。各功能只读取自身所需节；当前模板是字段维护源：[project.toml](../../experiments/20261106-basepack/src/basepack/project/templates/project.toml)、[machine.toml](../../experiments/20261106-basepack/src/basepack/project/templates/machine.toml)。

| 字段 | 解析或维护责任 |
| --- | --- |
| runtime.python、runtime.machine_config | 明确绝对路径 |
| project.root | 相对项目配置文件 |
| ai.default_tier、ai.retrieval_tier、ai.tiers | 项目维护用途默认等级及各等级模型和推理强度；宿主读取后派工 |
| ai.max_concurrent_subagents、ai.concurrency_source | 安装agent采集的不含主agent、包含后代的容量及依据；config set-concurrency显式刷新，旧项目不猜默认。实时空闲额度另传本轮，配置快照不等于空闲数 |
| memory.data_dir、jobs.jobs_dir | 相对项目根，受管理数据必须在该项目 .basepack 内 |
| 机器配置中的相对设施路径 | 相对机器配置文件 |
| embedding.endpoint | 显式共享 HTTP 地址，本机为 loopback 8765 |
| embedding.gpu_memory_mib | 可按机器调整的软目标；模板9216 MiB，0关闭按目标释放空闲缓存，不设置分配器硬上限或作为CUDA启动正预算门槛 |
| memory.endpoint/namespace/database | HTTP(S) 显式回环 IP（127/8 或 ::1），拒绝域名/通配/远端及额外 URL 成分；逻辑库不代替物理隔离 |
| memory.username/password_file | 用户名及唯一 UTF-8 密码文件；路径相对项目根或绝对，省略时为 memory_dir/password.txt |
| memory.project_id/source_scope | 随项目保留的 UUID；source_scope 在 Git 项目中增加显式包含项，在非 Git 项目中声明新文件发现范围 |
| memory.private_scope | 额外私有项目相对文件／目录，默认空；`.`为全项目。根private始终私有，分类不增加摄入；规则变化进入来源版本并使未提交旧稿明确冲突 |
| memory.codex.project_id/other_project_roots/registry_complete | Codex 宿主项目绑定和完整注册根证据，独立于 basePack UUID；未取得时明确聊天缺口 |
| memory.search_mode | CLI 未显式传 --mode 时采用的 hybrid/vector；新项目默认 vector |

`memory guide/rank` 在项目配置解析前分派；stop/owner/release/recover-owner读配置定位状态但不读凭据。memory prompt渲染唯一协调者；memory wave worker-prompt/task-prompt只读本地wave与固定任务，retrieval-dispatch/retrieval-prompt仅读配置和请求，均不连库或模型。机器配置不再维护无消费者的 `[shared].state_dir`；模型日志由 SCM/Shawl 服务定义中的显式路径管理，jobs 材料仍归项目 jobs_dir。

机器 embedding 节沿用 endpoint、service_name、queue_timeout 与模型设置；模型适配层单处维护32768-token上限，移除旧机器 `max_length`。客户端以 username 和自动读取的 password_file 建立 Basic Authorization；config show 返回 memory_password_file 绝对路径而不读取或显示 secret。password_env 与手工 shell 桥退出。instructions 保留固定 Python、绝对配置和 brief 调用；guide/rank不读配置或凭据；owner/stop/release/recover-owner需配置但不读凭据或连库。project_id 随移动或恢复保留，误连另一身份的库会失败。config show 和 doctor 只作诊断，不能替代真实功能验收。

## 环境与服务

项目 `.basepack` 的推荐内部结构、生产状态与临时/选留材料的边界见[本机数据目录约定](project-data-layout.md)；现行工作包进入根tmp，历史保留例外和已执行清理在该页区分。

依赖由[pyproject.toml](../../experiments/20261106-basepack/pyproject.toml)与uv.lock维护，CUDA来源明确。0.17的behavior extra提供numpy、scipy及锁定的scikit-learn 1.9.1，仅实际训练KL-NMF需要；基础采集、发布、检索及既有模型回读不要求安装训练依赖。系统环境不做清理式同步，共享服务环境不安装无关MCP集成。源码与wheel验证分别核导入位置；普通安装从源码外运行。

共享 embedding 沿用 Shawl/SCM，Manual、LocalSystem、no-restart/kill-process-tree；LitServe 单 worker 常驻，客户端超时只结束等待。项目 SurrealDB 可沿用已有普通用户隐藏手动认证进程。cwd、原生 store、日志与启动材料在项目 memory 目录；serve.ps1 从同一配置取得显式回环地址、username 和密码文件，设置原生认证入口后调用稳定 exe，不启用 unauthenticated。新库一次安全随机生成文件，已有库缺文件时恢复原凭据；launcher 不生成密码。SCM 是管理员可选方式，本轮未配置。basepack 只连接，停止项目库不停止共享模型。

改写密码文件不会轮换数据库内的存储账户；轮换由管理员显式更新账户并同步同一文件。访问和认证失败保留原错，客户端不回退无认证。操作见 [管理员部署](../../experiments/20261106-basepack/docs/administrator.md#项目-surrealdb)。

搬迁先停止该项目库并确认进程退出，再移动完整项目、调整启动cwd/日志/endpoint，保留UUID后复核。在线备份用原生export；恢复集合含export、配置、原凭据文件、业务原件、受管聊天导出、附件原件/定位回执和必要assets。0.17还须保留memory_dir/behavior/<sha256>.json与其引用的数据库事实/模型元数据；模型工件按hash核字节，缺失或损坏明确失败。已接受语义、更正、真实交付及原始锚点必须恢复，行为投影可重放，内容向量可从保留表示重建。数值模型和原生导出仍属项目限制分发资料，不因无正文而自动可公开。备份位置和保留周期由项目确定，Git忽略和本机目录不代替备份。

## 升级与回退

0.18系列维护采用有限本地wave和两段Terra；实际安装和各批验收以上文为准，发布少量知识不表示所有gap已持久化处置或完整维护完成。该调整不改变memory schema 3、行为算法、项目UUID、知识版本或向量。接入前先在自然边界固定旧轮接受／未发稿及余项，结束旧worker并核发布终态，由原父正确关闭旧轮；新包不把旧receipt自动解释为新组织。安装后刷新托管入口并保留Terra恢复名额，按[产品接入](../../experiments/20261106-basepack/docs/setup-project.md#升级到-018有限任务池)核实际宿主操作；不能以CLI单元成功代替宿主生命周期。活动`maintenance/wave.json`、固定初始化／执行回执、通知宿主证据、publication intent及未发稿与原owner/control一起保留恢复，未明状态不释放。

0.17.0新增严格memory_schema_version=3标记，保持项目配置schema 2、机器schema 1和member identity 2。新库memory init写入3，已绑定且缺失或不符标记的库由新版init及普通读写明确拒绝，须先完成离线桥。独立collect与显式collection/retained替代maintain内采集及skip-codex-collection；scope实际限制来源工作集，作者提案引用固定prepare并由程序编译，检索使用请求专属身份及严格交付context。新J从切换基点开始，首次空/非空确认均推进，非空机会C另计；新版init只在不存在时创建事实头，不重置已有J。读API不隐式写行为投影。客户端升级不要求更新共享embedding服务或重算未变向量。

旧库按停写后的新鲜export恢复到独立物理实例，使用保留的0.16客户端运行离线[migration.py](../../experiments/20261106-basepack/src/basepack/memory/migration.py)：migrate转换事实，finalize内部执行verify逐字段/模式/索引/事件核等价，通过后显式写入schema 3交接标记；随后新版memory init安装schema且保留J。验证恢复与受影响功能后才同步切换客户端和库，不把源码测试或预备导出当成正式切换。保留旧wheel、配置/凭据、原库和完整恢复集合；0.16未提交作者稿按新prepare重做，已提交batch先核原数据库receipt，保持原身份避免重复发布。旧delivery保留原清单、非空顺序及原context，不伪造新J或原始锚点；旧context无新锚点时按unknown重放，仍可训练真实共交付。旧知识版本无法证明j_enter时保留未知，另记observed_j=0及age_origin=legacy_cutover，只表示从切换处观察，h=0不冒充命中，重训不移动起点。迁移策略与本项目实际执行见[实施记录](../tasks/20261115-real-use-rectification/execution.md)。

0.16.0增加大源快照分消息、显式跳过新聊天采集、有界协作与同轮干净阶段、原位私有范围。客户端升级前结束自有维护并保留旧wheel／配置／凭据／原生export及既有完整恢复链；普通安装后`memory init`保留UUID、配置及托管块外业务内容。无需迁库、重算未变向量或升级共享服务。已提交receipt先恢复；0.15固定稿仅在两规则字段同时缺失且当前额外私有范围为空时沿已知根private合同接续，非空新规则明确冲突。阶段文件、handoff、原receipt、固定稿及结果需一起保留，owner.json.stage是唯一当前阶段指针；宿主负责实际旧组结束和fresh spawn。恢复材料边界与实测见[本轮结果](../tasks/20261115-real-use-rectification/result.md)。

0.15.0 新增同源 `memory publish` Python helper／薄CLI，顺序组合完成稿hash核对、freeze/validate、固定稿保存和原apply；原子工具、scope／版本／owner合同及数据库receipt权威保持。客户端升级后刷新托管入口和提示词，固定稿接续保持原batch_id与UUID；本地结果投影失败不新建batch。共享服务须另部署并重启，才启用CUDA显式cuDNN、实际32768-token上限、无文本字节硬限和柔性显存目标；纯文本batch4、含图batch1，超限422且不截断，合法输入仍可能OOM。请求结束后仅在reserved超正目标且有空闲缓存时释放。运行设置不改变向量身份，未变旧输入继续复用，实际分块／输入改变才重新编码；本版不迁库或全量重算。约99%落在目标内是经验目标，未作统计验收。升级保留原wheel／配置及已有恢复链，移除旧 `max_length`，核 `/info` 后端／上限／软目标及实际图文、旧索引查询；操作见[管理员流程](../../experiments/20261106-basepack/docs/administrator.md#升级与回滚)。

0.14.0 将根 `private/` 独立 Git 的已跟踪及未忽略资料默认纳入同一项目，按来源、固定版本依据与端点写入 `private` 布尔标记；显式 scope 仍仅控制本轮新文件发现。沿用项目配置 schema 2、成员身份版本 2、UUID、数据库和向量输入；源码变更不要求共享 embedding 服务同步升级。普通安装后刷新 memory 托管入口，存量补标在结束旧维护并保存恢复集合后按可确认版本作元数据升级，不改知识身份或向量。无标记的旧记录保留未核含义，完整恢复备份须包含数据库及必要原件/图片等文件。独立私有 Git 不复用公共 remote，公开分享副本另行处理；本版没有自动净化导出命令。

0.13.0.dev1的member身份版本为2，普通init/apply/查询拒绝未迁移库。先隔离安装新wheel，再停写、保存完整恢复集合并将原生导出迁入独立物理库；迁移统一转换当前/退役/历史身份及结构化引用、版本/访问派生键和delivery清单，保留知识版本、原证、向量与事件含义。完整比对与功能回读通过后才设置新标记、同时切换客户端和库并恢复写入。旧库、旧wheel和冻结映射只作恢复材料；正常运行没有旧协议或在线别名。具体停写、回执作废与恢复工具见[项目升级](../../experiments/20261106-basepack/docs/setup-project.md#版本升级)和[本轮交付](../archive/20261114-delivery-closeout/result.md)。项目配置schema 2、UUID和凭据保持。

同版jobs退役PID回执/cleanup_confirmed、psutil依赖和客户端重复限时；执行worker与客户端一起更新，原生Condor策略与站点配置保持。共享embedding诊断生效需要管理员只替换服务包及必要websocket依赖并重启原服务；保留模型、锁、identity、配置、Shawl定义和其它模型依赖版本，按更新前基线核正常图文及422原索引诊断。实际安装状态见本轮交付，不从源码版本推断服务已更新。

0.12.0.dev1 新增知识版本归档同步事件、access_state/delivery 和全局交付序号，沿用项目配置 schema 2、UUID、凭据及向量身份。升级先结束旧维护并保存原生 export、新旧 wheel、配置及必要原证/managed 文件；普通安装后 memory init 更新 schema 和托管入口，不要求重算向量或重写全库知识。恢复需保留精确知识版本、全局事件、访问状态及原 delivery_id；存量未保存的历史不补造。代码/模板、数据和共享设施的恢复范围见[配置维护要点](../../experiments/20261106-basepack/docs/project-config-maintenance.md#按变化边界准备恢复集合)。服务端输入422改进仅在对应服务包部署后生效；本轮沿用0.5共享服务，不自动重启。

0.11.0.dev1增加时长入口判断、容量快照、固定布局和名称及独立检索派工。先收尾旧维护，保留UUID/凭据/知识后普通升级；旧项目运行config set-concurrency补容量和来源，再memory init刷新托管入口。仅托管块自动刷新，块外旧路径另行核对。容量或模型映射修改影响新一轮，已有回执layout保持；旧无layout回执先结束旧轮，不隐式重算续派。并发快照随宿主/profile改变显式同步，不建设每会话全量核查或监视器。操作见配置维护要点。

0.9.1 修复维护依赖与空来源处理、聊天附件出处交接、历史快照回读及检索去重。新来源快照保存接受时路径并将路径纳入版本身份；旧快照保留同来源读取合同，跨来源以成员历史证明归属，不要求逐版本的成员接受记录。旧快照缺路径时仅使用可核的唯一路径，不强迁或重写已有知识。配置、UUID、原凭据、embedding 身份和共享服务保持既有合同，实际安装与验证沿 [本轮进度](../archive/20261111-consistency-review/progress.md) 接续。

0.9.0 增加随 wheel 安装的英文维护模板与纯 `memory prompt` 渲染入口。默认 Git 清单加 source_scope 显式包含项取代仅按 source_scope 发现，非 Git 仍按声明范围；历史已登记及未接受来源保持全局接续。maintain 短结果增加发现边界、control 与协调者派工元数据，宿主按返回命令交接，刷新生成入口和自有包装。模型映射由项目 [ai] 解析，宿主实际设置；数据库 schema、原凭据、UUID、向量身份与共享服务沿用既有合同。安装、构建和真实使用结果分别按专项进度核实。

0.7.0 将查询与维护分离：查询读取已发布内容及依据快照，维护候选在所选模式的向量准备好后原子发布。知识表与项目/机器配置 schema 保持现有格式；升级保留 UUID、数据及显式检索模式，运行 memory init 刷新 schema 和生成入口。0.7.1 删除独立 text 模式；旧 text 项目复用或补齐兼容向量后切换 vector/hybrid，保留知识、ID 和来源。新项目默认 vector。

0.8.1 保留既有认证库和原用户名/密码文件，删除 password_env 手工桥。升级前备份 wheel、配置、密码文件和完整恢复集合，等待在途客户端调用结束后普通更新客户端，刷新 instructions 与自有包装。服务、物理目录、端口和 UUID 保持，通常无需重启或迁库；新 shell 直接核 brief/search/read/neighbors。失败按原错误恢复凭据或回退客户端，不清库、不重新总结。

0.8.0 将维护入口收敛为 `memory maintain` 的确定性预检与余下语义交接，默认读取 source_scope，采集可归属聊天后按来源接续。CLI search 与 Python `Memory.vector_search`、`Memory.hybrid_search` 统一 `{matches, vector_coverage}`，两项 Python 方法删除 `include_coverage`，调用方读取 matches；brief 删除 `changes/change_count/vector_pending/vector_pending_count`。删除无消费者的 MachineConfig.state_dir 和旧 MemberContent/read_member 原件接口，快照回源保持。独立 skills 仍从配套源码取得，未改 wheel 发行范围。

轻客户端要求 Python >=3.13，CPU/CUDA 模型依赖由各自 extra 选择。共享 embedding 的协议和语义身份未变，旧服务可继续提供其原有能力；新后端、上限和软目标需对应服务包部署后生效。CPU 服务按自动设备选择启动，保持相同模型与 FP16。Condor 继续维护准入和排队，capacity 只作观测。更老项目缺少检索模式或 `[ai]` 时按[项目接入](../../experiments/20261106-basepack/docs/setup-project.md#版本升级)补齐。

升级保留新旧 wheel、配置和知识备份，核安装来源并在源码外验证受影响流程。底座或知识 schema 变化须验证原生恢复；回退客户端保留项目数据，旧资源版不提供记忆能力。只有服务实现或资源协议确需改变时，才按管理员流程排空、停止并切换相应服务。

0.4 → 0.5 的资源接口切换与回退见 [R9 结果](../archive/20261107-resource-coordination/r9-result.md)，旧 RPC 与取消/关闭协议已退役。更早 schema 1 项目先用保留的 0.4.0 显式 migrate，原配置和映射保留在各项目；历史迁移见 [R8 结果](../archive/20261107-resource-coordination/maintenance-result.md)。
