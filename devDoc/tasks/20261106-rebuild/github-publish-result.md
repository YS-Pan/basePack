# basePack 0.6.3 首次发布结果

2026 年 11 月 10 日（北京时间）。本任务按 [发布计划](github-publish-plan.md) 准备 [YS-Pan/basePack](https://github.com/YS-Pan/basePack) 的首次源码发布。用户明确要求当前项目的记忆留在本机。

## 当前交付

0.6.3 源码已推送至 [GitHub main](https://github.com/YS-Pan/basePack)，[v0.6.3 开发版](https://github.com/YS-Pan/basePack/releases/tag/v0.6.3) 于北京时间 2026-11-10 13:39 发布。tag 指向 `5759cde`，包含已验收的实现和安装说明；main 后续补发布回执。源码回归、纯净安装、真实 agent 增量维护、新 shell、新聊天及远端 clone 使用闭环通过。

- 新项目默认 `memory.search_mode = 'text'`，显式 `--mode` 优先；`doctor` 默认 core。已有项目需明确补配置项，按同一 UUID 执行 `memory init` 刷新记忆入口。
- 生成入口按当前配置定位凭据文件及环境变量，每个新进程重新加载，并定位数据库 launcher、cwd 和日志。原业务正文保留。
- README 提供从 clone 开始的轻量安装、按能力准备设施和 skills 分发。管理员文档补官方来源、模型固定 revision 下载与锁生成、Condor 首次安装及本机预算；开发试用、问题记录与外部 Issue 草稿入口已落实。
- 首次 0.6.3 发布时尚未选择本项目许可证；此后用户明确选择 MIT，许可补丁见文末 0.6.4 记录。第三方声明保留，项目记忆、数据库、配置、密码、模型与运行原证不随 Git 分发。

## 实际检查

| 项目 | 结果与条件 |
| --- | --- |
| 源码回归 | Python 3.13.17、pytest 9.2.0，201 passed、0 skipped。实际导入 active 工程 src；独立全新 SurrealDB 4.0.0 目录/端口，包含原生读写与恢复、4 项既有共享 embedding 检查、Condor 原生离线策略和模型准备回归。 |
| 普通安装 | 全新轻量环境仅有 basepack 0.6.3 与 psutil 7.2.2；源码外 `-I`、CLI 和 console entry 通过，33 个包文件与本次 wheel 及源码逐字节一致，模板、schema 和 memory skill 齐全。 |
| 可选设施隔离 | 无 embedding/Condor 节的最小 schema 1 机器配置可完成 init/config show/default core doctor；客户端环境不含 torch、Pillow、Sentence Transformers 或 LitServe。 |
| 真实 agent 试用 | 检索等级实际为 tier1（gpt-6-luna/max）。同读两份合成业务材料，完成分块、摘要、跨材料关系、实际评分和 rank；将一份原文阈值从 18% 改为 20%，维护后新值可回读，旧值不再作为当前命中，另一份原件及其知识保持。自然语言长问句首轮无命中，经后续文字关键词检索取回依据；不据此宣称整体召回或质量优势。 |
| 干净新 shell | Windows PowerShell 5.1、NoProfile、源码外 cwd，清除先前相关环境后，仅执行生成的记忆入口；凭据加载、brief、默认 core doctor 和未传 --mode 的文字检索通过，召回当前 20% 条件。 |
| 独立新聊天 | 干净上下文 tier3（gpt-6.1-sol/ultra）仅接收业务项目 AGENTS 路径和使用目标，自主加载入口与凭据，brief 成功且 changes/pending 为 0；默认文字查询经短词取回依据，回读两份当前原文，答出 20%、雨日重计及滤网台账批准前提。 |
| 远端 clone | 从 GitHub clone `5759cde`，严格按 README 用 venv 和 pip 安装；新 UUID、独立数据目录及端口完成 ready/init/brief、公开最小示例的 prepare/apply/search/read/neighbors，随后新 Windows PowerShell 默认文字检索通过。两项通用 skills 按公开步骤复制并读取。 |
| 远端安装一致性 | 33 个安装包文件逐字节匹配该 clone 的 src；按 Git 换行归一后，与 Release 的 33 个文本内容一致，路线 README 与 Release METADATA 正文一致。源码本地重新构建的 zip 字节不同，单独记录，不冒充下载附件。 |
| 依赖与文档 | uv 0.13.7 的离线锁检查通过，共 67 包；本次变更的 UTF-8、相对路径、锚点、PowerShell 语法与 Git 差异检查通过。 |

wheel 为 `basepack-0.6.3-py3-none-any.whl`，58,361 字节，SHA256：

```text
a1bd975e199d3e6ae2a9e7ef493a979a467631d6dac58f765f2792cbae926730
```

SurrealDB 使用官方重新下载的 4.0.0 原生 EXE，286,956,032 字节，SHA256 为 `0184ff8ac150a968e86d551960455f1b3f5825767bb755f572d3f987f366773b`。本次测试库与本项目正式库分离。源码回归进程、两套文字试用的 launcher/server 树均已退出，18164/18165 无监听；控制台 Ctrl-C 后仍有树成员时采用精确 PID 终止收尾，因此只声明资源回收完成，不宣称原生 graceful shutdown 全过程完成。正式项目库和共享服务保持原实例。

Release 仅上传上述 58,361 字节 wheel 和 99 字节 `SHA256SUMS.txt`，为公开 prerelease、非草稿。两附件已从 GitHub 重新下载，wheel SHA256 与已验收包一致，校验和文本逐字节一致。

首次测试环境缺少 Sentence Transformers 发行元数据，补充只读引用既有服务依赖后复核；中间一轮验收脚本重启旧临时 store 却换了密码，修正为每轮独立 store 后全套通过。失败日志保留在本机验证原证。受限宿主会回收隐藏 launcher；相同临时库在获准的正常用户上下文启动后，跨调用 ready/init/brief 通过，未改变正式服务。

## 支持与待验边界

本次验证发生在作者 Windows 机器的独立环境和全新数据目录，测试依赖及四项向量检查复用已有共享设施。未取得可用的空白 Windows 实机/虚拟机，因此空白操作系统、完整模型首次下载与新服务部署、新 Condor pool 及首次 GPU 预算/并存尚待独立机器验收。公开文档与开发版状态保持这一边界。

分层协作质量对照、大语料、长期使用和费用净收益仍沿原专项结论；本轮发布准备不扩写这些成果。

本轮采用主 agent 与项目接续、资源、产品文档、验证分支直接协作；实际语义试用由干净上下文的订阅 worker 完成。主上下文、团队总 tokens 与费用均不可核，不以测试数、字符数或工具轮次代替使用收益。

## 发布边界核查

发布准备提交 `cf96ec0` 的完整树为 203 文件、993,185 字节；全部可达历史 78 次提交、872 blobs，最大单对象 63,666 字节。路径及有限凭据模式检查未发现真实项目记忆、数据库、私有配置、凭据、模型、环境或运行产物进入 Git；`.basepack/` 及本地原证被忽略。后续发布回执只更新相关文档，推送前核对最终清单。

首次实际推送 `5759cde` 为 203 文件、995,661 字节，GitHub API 完整树未截断，私有数据路径检查为空。远端 clone 也未取得作者的项目记忆。GitHub 附件只来自路线 dist 中明确列出的 wheel 和校验和，未上传本地原证或记忆目录。

原始脚本、日志和回执在本机 `tmp/github-publish-validation/`，已按复核需要选留至 `artifacts/runs/20261110-github-publish/`，这些目录均被 Git 忽略。选留前核对未包含测试凭据；原证包括 source/wheel/new-shell/remote-verification、实际语义批次、评分、回读及问题草稿。当前项目自己的记忆与维护材料仅保留在 `.basepack/`。

## MIT 许可补丁 0.6.4

用户于 2026-11-10 明确选择 MIT。根 [LICENSE](../../../LICENSE) 为项目自有源码、skills 与文档提供许可，独立工程 [LICENSE](../../../experiments/20261106-basepack/LICENSE) 保持相同字节以供包内分发；Qwen 的 Apache 许可及 NOTICE 原样保留。当前适配器调用外部 Sentence Transformers 实现，模型及依赖遵循各自许可。

0.6.4 为许可与元数据补丁，保留已发布 0.6.3 的标签与附件。构建声明采用 SPDX MIT 与三条 License-File，并将 setuptools 下限设为 77.0.3。0.6.4 wheel 为 64,272 字节，SHA256 为 `ef522d809518548ac51e4dcf604a3b72c2f718a870fc7ce052161b1fb50121ef`，发布到 [v0.6.4 开发版](https://github.com/YS-Pan/basePack/releases/tag/v0.6.4)。

定向检查确认根、工程、wheel 和普通安装中的 MIT 全文一致；两份 Qwen 声明在包资源和 dist-info/licenses 中均存在且与 0.6.3 原字节一致。33 个运行包文件与 0.6.3 完全相同，纯净客户端普通安装、pip check、模块 CLI 与 console entry 通过；本次没有重跑此前 201 项功能矩阵或启停数据库/共享服务。当前为已构建并验收、待发布状态。
