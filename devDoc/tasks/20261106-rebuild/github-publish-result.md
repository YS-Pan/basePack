# basePack 0.6.3 首次发布结果

2026 年 11 月 10 日（北京时间）。本任务按 [发布计划](github-publish-plan.md) 准备 [YS-Pan/basePack](https://github.com/YS-Pan/basePack) 的首次源码发布。用户明确要求当前项目的记忆留在本机。

## 当前交付

0.6.3 源码、产品文档与 wheel 已完成准备，源码回归通过；纯文字新项目与新聊天接续正在收尾，远端发布尚待执行。

- 新项目默认 `memory.search_mode = 'text'`，显式 `--mode` 优先；`doctor` 默认 core。已有项目需明确补配置项，按同一 UUID 执行 `memory init` 刷新记忆入口。
- 生成入口按当前配置定位凭据文件及环境变量，每个新进程重新加载，并定位数据库 launcher、cwd 和日志。原业务正文保留。
- README 提供从 clone 开始的轻量安装、按能力准备设施和 skills 分发。管理员文档补官方来源、模型固定 revision 下载与锁生成、Condor 首次安装及本机预算；开发试用、问题记录与外部 Issue 草稿入口已落实。
- 当前未指定本项目的开源许可证，README 明确许可状态；第三方声明保留。项目记忆、数据库、配置、密码、模型与运行原证不随 Git 分发。

## 实际检查

| 项目 | 结果与条件 |
| --- | --- |
| 源码回归 | Python 3.13.17、pytest 9.2.0，201 passed、0 skipped。实际导入 active 工程 src；独立全新 SurrealDB 4.0.0 目录/端口，包含原生读写与恢复、4 项既有共享 embedding 检查、Condor 原生离线策略和模型准备回归。 |
| 普通安装 | 全新轻量环境仅有 basepack 0.6.3 与 psutil 7.2.2；源码外 `-I`、CLI 和 console entry 通过，33 个包文件与本次 wheel 及源码逐字节一致，模板、schema 和 memory skill 齐全。 |
| 可选设施隔离 | 无 embedding/Condor 节的最小 schema 1 机器配置可完成 init/config show/default core doctor；客户端环境不含 torch、Pillow、Sentence Transformers 或 LitServe。 |
| 依赖与文档 | uv 0.13.7 的离线锁检查通过，共 67 包；本次变更的 UTF-8、相对路径、锚点、PowerShell 语法与 Git 差异检查通过。 |

wheel 为 `basepack-0.6.3-py3-none-any.whl`，58,293 字节，SHA256：

```text
6553481d998863373bc9f9d2ff1db7a618ebfe0f00a8fa23cb6fdd31885592af
```

SurrealDB 使用官方重新下载的 4.0.0 原生 EXE，286,956,032 字节，SHA256 为 `0184ff8ac150a968e86d551960455f1b3f5825767bb755f572d3f987f366773b`。本次测试库与本项目正式库分离，源码回归进程已退出。

首次测试环境缺少 Sentence Transformers 发行元数据，补充只读引用既有服务依赖后复核；中间一轮验收脚本重启旧临时 store 却换了密码，修正为每轮独立 store 后全套通过。失败日志保留在本机验证原证。受限宿主会回收隐藏 launcher；相同临时库在获准的正常用户上下文启动后，跨调用 ready/init/brief 通过，未改变正式服务。

## 支持与待验边界

本次验证发生在作者 Windows 机器的独立环境和全新数据目录，测试依赖及四项向量检查复用已有共享设施。未取得可用的空白 Windows 实机/虚拟机，因此空白操作系统、完整模型首次下载与新服务部署、新 Condor pool 及首次 GPU 预算/并存尚待独立机器验收。公开文档与开发版状态保持这一边界。

分层协作质量对照、大语料、长期使用和费用净收益仍沿原专项结论；本轮发布准备不扩写这些成果。

原始脚本、日志和回执在本机 `tmp/github-publish-validation/`，结案时按需要选留至 `artifacts/runs/20261110-github-publish/`，这些目录均被 Git 忽略。当前项目自己的记忆与维护材料仅保留在 `.basepack/`。
