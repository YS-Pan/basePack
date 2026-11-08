# 系统结构与边界

当前唯一 active 路线为 [20261106-basepack](../../experiments/20261106-basepack/README.md)，提供 0.4.0 公共入口与资源工具。记忆实现继续见 [记忆任务](../tasks/20261106-memory-system/plan.md)，实际安装与验收统一见 [资源进度](../tasks/20261107-resource-coordination/progress.md)，现行配置和安装边界见 [部署合同](deployment.md)。

## 当前组成

```text
AGENTS.md                         项目规则和阅读导航
README.md                         项目目标、active 路线和路线索引
skills/file-structure/            独立文件结构 skill 与按需参考
skills/agent-team/                使用宿主 subagent 的分层协作 skill
experiments/20261106-basepack/
  README.md                       路线和产品入口
  pyproject.toml                  本路线安装、依赖和构建声明
  src/basepack/
    project/                      唯一配置解析、init/migrate/doctor 及模板
    embedding/                    supervisor、模型 worker、客户端及机器管理
    jobs/                         CondorClient、提交材料与 UTF-8 worker
  tests/                          维护用回归与夹具
  docs/                           本路线用户与管理员说明
  examples/                       小样例和 Condor 配置维护源
  skills/resources/               共享 embedding 和普通重任务使用入口
  dist/                           交付和回滚包，Git 忽略
devDoc/                           根目录唯一开发文档树
  project-charter.md               用户目标与长期要求
  documentation.md                文档职责与维护规则
  terminology.md                  项目概念边界
  system/                         当前路线的实现、部署和环境说明
  tasks/                          活动计划、调查、进度与结果
  archive/                        已结束任务的保留材料，始终存在、允许为空
  change_log/                     按次记录的已发生变化
tmp/                              一次性工作区，内容默认可清除、Git 忽略
artifacts/runs/                    选留的运行、评测和迁移原证，Git 忽略
.gitattributes                    文本格式与原文字节保护
.gitignore                        本地数据、依赖和产物边界
```

从根 AGENTS 选择系统说明或任务入口，再按问题追溯依据；实现与详细依赖随路线组织，计划、进度和结论只在根 devDoc 维护。新路线实际开工后才创建实验工程，短期比较后收敛 active；退出路线保留必要代码和历史入口，需要长期独立演进时分为多个 project。

## 所有权与边界

- 本仓库维护项目目标和根开发文档；纲领正文按用户同意修改，原始快照保留原文。调研是带条件的观察，旧项目不提供本项目的运行状态或验收结论。
- `file-structure`、`agent-team` 是根目录可独立交付的通用技能。前者按具体授权选择、建议或整理布局；后者定义动态分工和交接，实际派发、权限与模型能力由宿主提供。
- 本路线的产品代码、声明、模板、用户文档和 resources skill 各有一个维护源。源码中的 project、embedding、jobs 是协作模块；运行包通过正常安装使用，业务项目不保存源码副本或 PYTHONPATH。
- 项目显式指定一份 schema 2 接入配置，绑定 Python 和 schema 1 机器配置；project.root 相对项目配置，受管理数据进入该业务项目 `.basepack/`。机器相对路径以机器配置为基准；模型、环境和服务状态在共享设施维护，通过配置定位。
- `init` 从安装包 project/templates 生成配置和详细 instructions，根 AGENTS 合并短指针；`migrate` 显式读取旧配置并保存项目内备份与映射。ProjectConfig 只解析公共绑定，各功能按需读取自身节；记忆检索与数据库尚未实现。
- embedding 由作业树外 supervisor 拥有一个模型 worker，项目客户端只连接；向量语义身份、RPC 协议与部署指纹分别维护。普通任务由 Condor 拥有进程树；普通容量和站点策略只由 Condor 维护，管理员为背景服务预留额度。详见 [资源模块](modules/resources.md)。
- 后续路线复用既有资源能力时使用明确版本的发行包或公开服务接口；兼容环境、权重和缓存可共享，项目知识和试验状态分别保存。路线不依靠另一条路线的可变源码或数据库隐式运行。

概念歧义查 [术语](../terminology.md)，机器观察和技能发现入口见 [环境说明](environment.md)。文件结构与记忆检索、建图能力属于不同层次。
