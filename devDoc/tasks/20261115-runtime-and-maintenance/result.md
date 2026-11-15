# 运行与维护交付结果

2026-11-15（北京时间）。按[最终计划](plan.md)实施，源码、普通wheel、本项目稳定客户端与共享embedding服务均为 **0.15.0**。E和项目局部ongoing已启用；没有增加通用runner、状态机、定时归档或自动返工队列。实际检查与生命周期见[进度](progress.md)。

## 已交付

- **Embedding：** CUDA显式cuDNN attention；适配层统一按预处理后的实际attention_mask限制32768 token，包含模板、指令和图像token。超限在所属推理批forward前返回422，不截断，并保留原请求索引与计数。移除机器max_length、64 KiB文本限制、分配器硬限和正硬预算启动门槛。纯文本batch4、含图batch1保持。
- **柔性显存：** 本机gpu_memory_mib仍为9216 MiB（9 GiB），作为运行目标。请求后仅在未用缓存超过目标时尝试释放，不逐请求清空；OOM和底层错误继续交调用agent处理。普通Condor作业的资源申报合同保持。
- **E：** 新增`basepack.memory.publish`与同源`memory publish`，从有序完成稿引用核文件hash、freeze／validate、独占保存frozen并调用原apply，一次返回紧凑结果并保存详细数据库回执投影。原prepare／read／neighbors／freeze／apply仍直接可用，agent可用普通Python自由组合。固定稿接续保持batch ID／UUID；真实修稿重新prepare／阅读／freeze。
- **Ongoing：** [索引](../ongoing/README.md)、两个主题、AGENTS短指针和文档约定已建立。created_at为`2026-11-15T12:59:18+08:00`，expires_at为`2026-11-22T12:59:18+08:00`。到期即失效，下次正常读索引时整目录归档，保留时间、原因和未完范围；普通编辑不续期。

## 实际验证

源码全套正常用户上下文649 passed、5 skipped；为5项显式提供真实模型和SurrealDB程序后，4项通过，1项旧2048超限样例更新为32768合同后单项通过，合计654项均有通过记录。保留受限环境初次失败、旧样例失败与复验日志，不把它们隐去或计作一轮零跳过。最终文档UTF-8／局部链接和差异检查通过。

GPU作业 **14404.0** 实际执行当前适配层，源码SHA与回执一致，6组均通过。混长batch4及图文追踪到`aten::_scaled_dot_product_cudnn_attention`／`aten::_cudnn_attention_forward`。math对照最低余弦相似度分别为0.99999641／0.99998852，存在FP16数值差异；不据此承诺所有输入或全库排序完全一致。

| 探针 | 结果与PyTorch口径 |
| --- | --- |
| 实际32768-token单项 | 成功，peak allocated／reserved 5748.09／6360 MiB |
| 32769 token | 拒绝，原索引[1]，该推理批forward_calls=0 |
| 66000字节合法文本 | 实际11020 token，成功，移除旧字节限制生效 |
| 10240 token × 4 | 成功，peak allocated／reserved 6168.10／6706 MiB；探针软目标5500时请求后reserved降至4084 MiB |

探针仅为遵守普通池申报设置6912 MiB分配器上限，产品没有该硬限。nvidia-smi进程显存返回N/A，以上不代表进程／全卡峰值。未测32k×4，未作99%百分位统计。

普通wheel在源码外独立环境、`-I`、非editable下完成E真实闭环：prepare→完成稿→CLI publish→原文回读→helper／CLI同frozen幂等→另一来源原freeze／apply→匹配向量，3个成员，最后stop／release。完成稿接受大小写SHA。专项155项通过，覆盖scope、hash、固定稿幂等与本地结果写失败后按原frozen恢复。初次临时环境缺websocket-client，离线补已有依赖wheel后成功，原冻结稿实际接续。

Ongoing以临时有效／精确到期夹具核整目录归档、附件指纹和原时间保留、未完标记、索引及直接链接修复；未把真实尚有效主题提前归档。

## 本机部署与恢复

本项目稳定客户端原位普通安装0.15.0并刷新memory受管入口；管理员UAC脚本升级SCM共享服务并重启，真实`/info`为0.15.0／cuda:0／FP16／CUDNN_ATTENTION／32768／9216 soft_target。66000字节文本、混长4条、图及图文实际HTTP200；32769实际HTTP422、原索引[1]与计数[21,32769]；空输入422。

模型revision、前处理、pooling和embedding_identity保持`Qwen3-VL:4e32ece7973113a13abd40dcbe5e5e4c8592f172f75535dc087f74f5269bba9e`。服务依赖比对仅basepack由0.13.0.dev1变为0.15.0；机器配置仅删除embedding.max_length。新服务编码查询原索引返回3条，抽查5条原向量及输入版本指纹前后一致，没有数据库迁移或全量重编码。

Wheel为`experiments/20261106-basepack/dist/basepack-0.15.0-py3-none-any.whl`，SHA256 `60b10ae4427bb043afee2f7043c036edea2153355fd4ee1a367d98584ea73b28`，59个包内文件与源码／服务普通安装一致。旧服务wheel仍在同dist，旧客户端wheel在`dist/0.14.0/`；配置备份、依赖快照、客户端原包和升级脚本选留于`artifacts/runs/20261115-runtime-implementation/`。回退沿已有管理员流程替回旧wheel／配置并重启，不自动回退或修改数据库。

最终原证选留于该artifacts目录的embedding／wheel-smoke／tests／service子目录；临时夹具和工作环境在`tmp/20261115-runtime-implementation/`。本轮只做本机交付，GitHub已公开发行仍为0.14.0。验证库2113已停止，生产数据库18080和共享服务8765保持健康，自有维护owner已释放，普通作业资源已归还。

## 边界与后续

9 GiB下约99%是实际使用目标，少数超标／OOM允许；长期显存分布、协调者token节省比例与所有检索排序均未量化。E减少确定性发布往返，仍保留作者修订、跨scope判断及宿主派工的灵活性；后续真实维护按新prompt使用，不为证明收益另开维护。自动维护积压和受限shell访问Codex状态库的既有反馈沿进度接续。
