# 项目配置与部署合同

更新：2026 年 11 月 9 日。当前唯一 active 路线为 [20261106-basepack](../../experiments/20261106-basepack/README.md)，已交付 0.5.0。本文维护代码、业务实例和机器设施的归属及升级边界；实际安装、功能和回退验收见 [R9 结果](../archive/20261107-resource-coordination/r9-result.md)。产品安装与命令从路线 README、[项目接入](../../experiments/20261106-basepack/docs/setup-project.md) 和 [管理员说明](../../experiments/20261106-basepack/docs/administrator.md) 进入。

## 位置与责任

| 内容 | 维护与运行责任 |
| --- | --- |
| 源码、依赖声明/uv.lock、模板、测试、产品文档、样例和 resources skill | 唯一维护源为 experiments/20261106-basepack；运行代码以普通 wheel 安装 |
| 业务实例配置、详细 instructions、项目知识和工具产物 | 属于对应项目，集中于其 .basepack/；不复制产品代码或模型 |
| 模型与 model.lock.json | 共享设施按组织/模型/revision 保存，多项目复用同份本地权重 |
| 机器配置 | 机器级一份 schema 1 TOML，保存显式模型路径、服务地址、预算与 Condor 位置 |
| embedding 服务环境 | 独立共享 Python 3.13 环境，安装同版 wheel 与锁定依赖，运行时不依赖实验源码或 tmp |
| Windows 托管与日志 | Shawl 位于稳定机器目录；SCM 拥有服务，日志写入配置共享 state_dir 下的 embedding/logs |
| 普通作业容量、站点策略和原生状态 | HTCondor 独立安装并唯一维护 |
| 业务原件及用户指定导出 | 沿用业务布局；工具保存引用和必要派生内容 |

本机 R9 服务布局采用 `C:/ProgramData/basepack/envs/service/`、`D:/AgentTools/bin/shawl-1.9.0/shawl.exe` 与 `D:/AgentTools/state/basepack/embedding/logs/`。这些是本次部署位置，公共代码通过显式配置定位设施；环境准备和切换是否完成以资源进度为准。依赖放在 C 盘以减少已观察到的逐文件导入延迟，模型保持原共享位置。系统 Python 保留轻量 core/jobs 安装，图文模型及 LitServe 依赖进入共享服务环境，避免系统中无关可选库影响服务。

根 `skills/file-structure/`、`skills/agent-team/` 独立维护；resources skill 归 active 实验，`.agents/skills/` 的发现联接指向维护源。开发临时环境、构建缓存和夹具在根 tmp，交付及回退 wheel 在实验 dist，选留原证在根 artifacts/runs；寿命见 [文档约定](../documentation.md)。

## 业务项目实例

```text
业务项目/
  AGENTS.md                      保留业务指令，合并 .basepack/instructions.md 短指针
  .gitignore                     追加 /.basepack/
  .basepack/                     项目局部、Git 忽略
    config.toml                  显式选择的唯一项目配置
    instructions.md              实际 Python、配置位置与操作入口
    jobs/                        提交材料、回执、日志及任务输出
    memory/                      记忆任务启用后维护的项目数据
```

`init` 从安装包的 project/templates 生成接入配置及 instructions；只合并必要的宿主入口，保留已有业务内容。新检出重新 init，不复制本机配置或历史数据库。支持 `.basepack/` 内的深层配置，project.root 按真实配置位置计算；调用显式传 `--config`，不向父目录搜索。默认派生数据位于项目 `.basepack/`，业务程序输出和用户明确指定的导出遵循业务路径。

## 配置合同

项目格式保持 schema 2，机器格式保持 schema 1，按文件职责分别检查版本。项目只绑定 runtime.python、runtime.machine_config、project.root 和功能所需的项目局部节；普通作业使用 [jobs]。各功能不强制读取未启用的 memory 或其他设施配置。当前模板是字段维护源：[project.toml](../../experiments/20261106-basepack/src/basepack/project/templates/project.toml)、[machine.toml](../../experiments/20261106-basepack/src/basepack/project/templates/machine.toml)。

| 字段 | 解析基准 |
| --- | --- |
| runtime.python、runtime.machine_config | 明确绝对路径 |
| project.root | 项目配置文件所在目录 |
| memory.data_dir、jobs.jobs_dir | 解析后的项目根，受管理数据在其 .basepack/ 内 |
| 机器配置中的相对设施路径 | 机器配置文件所在目录 |
| embedding.endpoint | 显式本机 HTTP 地址，项目客户端与服务共用 |

R9 机器 embedding 节新增 endpoint、service_name 和 queue_timeout，移除 idle_seconds；模型、设备、线程、请求内批次、输入限制和 allocator 预算继续由该节给出。本站 endpoint 为 `http://127.0.0.1:8765`、SCM 服务名 BasepackEmbedding；具体值以实际机器 TOML 为准。机器状态目录保存共享服务日志，服务发现直接使用 endpoint，不再通过 broker marker 和锁。

`config show` 描述实际解析路径及安装来源，`doctor` 只读诊断设施。它们不另存一份有效配置，也不代表推理或作业功能已验收。项目整体移动后按新位置解析配置；已生成作业材料中的绝对路径仍须复核，完成的 Condor 历史保留原提交路径。

## 环境与服务

依赖由 pyproject.toml 与 uv.lock 维护，torch/torchvision 的 CUDA 12.8 发行源显式声明；用原生 uv 命令准备独立共享服务环境，再普通安装本次 wheel。系统环境不做清理式同步，服务环境不安装无关 MCP 集成。源码回归和 wheel 验证分别核导入位置，后者从源码外运行；构建与测试入口见路线 README。

Shawl 通过 SCM 托管 LitServe，服务采用 Manual、LocalSystem 及 `--no-restart --kill-process-tree --stop-timeout 3000`。LitServe setup 加载一份常驻模型，单设备、单推理 worker；worker 故障按原生 restart_workers 重建，主进程或 Shawl 故障则停止，管理员手动启动。管理员停止后保持停止。客户端超时只结束等待，排队期限不打断已开始的推理，详见 [资源模块](modules/resources.md)。

`embedding ... serve` 是前台服务入口，生产由 Shawl 调用；`status` 使用原生健康和信息端点，`stop` 向 SCM 发送停止请求。SCM 接受控制请求后仍须观察 Stopped 和进程回收，不能把命令成功当作资源已释放。安装、停止、升级和卸载的原生命令只在管理员说明维护。

## 升级与回退

0.5.0 直接升级支持 0.4.0 的项目 schema 2。已知六份旧试用配置在 R8 完成迁移，原配置和映射留于所属项目；当时范围与证据见 [R8 结果](../archive/20261107-resource-coordination/maintenance-result.md)。项目 schema 1 先用保留的 0.4.0 wheel 执行显式 migrate，再升级至 0.5.0；0.5.0 已退役该迁移模块与 CLI。机器 schema 1 继续使用。

升级先准备新旧 wheel、机器配置与服务定义备份，核实际调用方及在途工作；用旧入口停止旧服务，再安装本次包与依赖、修改共享服务配置并切换调用方。保留项目数据和 Condor 站点策略，核源码外图文、普通 CPU/GPU、共享隔离、日志及进程回收后恢复使用。回退时停止新服务，恢复对应包、机器配置及服务定义；实际版本、结果和回退证据由资源任务记录。

0.5.0 的客户端和服务接口同批切换。旧 tokens_only、request_id、请求取消/关闭、私有 RPC、逐请求回执、部署代码指纹和旧生命周期模块已退役。新向量身份包含 Sentence Transformers 与实际 FP16 归一化合同，记忆 P2 须核索引身份并按需要重建；安装路径变化本身不改变向量语义。

R8 的旧源码映射、schema 1 项目迁移和私有服务机制保留在历史任务材料，不再作为当前安装合同维护。
