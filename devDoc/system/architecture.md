# 系统结构与边界

本页描述公共入口与已交付资源工具；记忆实现继续见 [记忆任务](../tasks/20261106-memory-system/plan.md)，资源验收见 [资源结果](../tasks/20261107-resource-coordination/result.md)。

## 当前组成

```text
AGENTS.md                  开发入口与阅读导航
pyproject.toml             安装、构建、依赖和模板声明
src/basepack/              Python 命令组合与包入口
src/basepack/project/      唯一配置解析、init/doctor 及随包模板
src/basepack/embedding/    supervisor、单模型worker、图文客户端及独立管理入口
src/basepack/jobs/    Condor薄入口、UTF-8参数worker与生命周期
docs/                     使用者接入说明
skills/file-structure/     独立文件结构 skill 与按需参考
skills/agent-team/         使用宿主 subagent 的分层协作 skill
skills/resources/          使用共享embedding和普通重任务工具
devDoc/
  project-charter.md        用户目标与长期要求
  documentation.md         文档职责与维护规则
  terminology.md           项目概念边界
  system/                  系统实现、架构与环境说明
  tasks/
    20261106-rebuild/      重建总览、公共历史和 skill 工作
    20261106-memory-system/  记忆系统计划与进度
    20261107-resource-coordination/  资源协调计划、部署、调研与进度
  change_log/              按次记录的已发生变化
artifacts/                 本机验证材料、辅助脚本、日志与输出，Git 忽略
.gitattributes             文本格式与原文字节保护
.gitignore                 本地数据、依赖和产物排除规则
```

当前开发流程是：从 AGENTS 选择目标、系统说明或相关任务入口，按问题追溯证据；完成修改后更新受影响的说明、进度和变更记录。文档结构与检索、建图产品能力属于不同层次。

## 所有权与边界

- 本仓库维护开发文档和项目目标；纲领正文按用户同意修改，原始快照保留原文。
- 调研报告是观察与解释，直接依据仍保留在其引用的材料中。旧项目继续作为参考，不导入其运行状态和验收结论。
- 机器共享环境与模型位于仓库外。本次可见状态及限制见 [环境核验](environment.md)，资料可见不代表已接入产品。
- `skills/file-structure/` 是可独立使用的文件结构建议工具。入口按任务选择开发文档或实验分包参考，agent 在具体授权范围内建议或整理；它不依赖记忆数据库或模型 API。
- `skills/agent-team/` 定义动态分工、协调、上下文分配和交接；实际派发、消息、等待、权限与模型可选项由宿主提供。它不自建 agent 服务或保存跨项目任务状态，模型与推理强度不写死在 skill 中。
- 项目显式指定一份接入配置，绑定 Python 和机器配置；project.root 相对项目配置，数据目录相对 project.root，机器路径相对机器文件。不搜索父目录，也不合并环境变量或多层配置。共享模型与机器状态在项目外，项目资料和作业记录在本项目。
- `init` 从 project/templates 生成 `.basepack/` 内的配置和详细 instructions，根 AGENTS 合并短指针，Git 忽略整 `.basepack/`；`config show` 显示实际包根安装，`doctor` 按设施只读检查。公共配置不强制解析未启用功能的节；记忆检索与数据库尚未实现。
- 共享 embedding 由作业树外 supervisor 拥有，项目客户端只连接，机器管理入口直接读取机器配置；向量语义身份、RPC 协议与部署指纹分别维护。普通任务由 Condor 拥有进程树。普通容量在通用 Condor 节点配置维护，basePack 读取实际 slot 并提交普通资源申请；管理员为背景服务预留额度。状态与资源边界见 [资源模块](modules/resources.md)。

涉及来源、片段、节点和索引时查 [项目术语](../terminology.md)。模块实现后，其说明需明确输入输出、维护责任、数据来源、可重建内容和重要约束，并链接对应代码或配置。
