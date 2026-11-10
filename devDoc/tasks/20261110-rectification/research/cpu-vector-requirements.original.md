# 建议为 basePack 增加 CPU 向量检索

我希望在不同电脑上使用 basePack 时，**项目记忆始终走向量检索**。有可用 CUDA 就用 CUDA 计算 embedding，没有可用 CUDA 就用 CPU 计算。同一个项目换一台电脑后，可以花更长时间，但应该查到相同的内容、按相同顺序返回，并引用相同的原文。

## 当前体验

我在没有可用 CUDA 的 Windows 电脑上部署了 basePack 0.6.3，使用 Python 3.13.17 和 SurrealDB 4.0.0。项目配置为 `memory.search_mode = 'text'`，已在独立测试库验证文字记忆的写入和检索。内置 Qwen3-VL 编码器在启动时检查 CUDA，指定 `device = 'cpu'` 会被拒绝。0.6.4 发布说明也注明运行包代码与 0.6.3 相同。 [0.6.3 发布说明](https://github.com/YS-Pan/basePack/releases/tag/v0.6.3) · [0.6.4 发布说明](https://github.com/YS-Pan/basePack/releases/tag/v0.6.4) · [编码器源码](https://github.com/YS-Pan/basePack/blob/v0.6.4/experiments/20261106-basepack/src/basepack/embedding/qwen3_vl.py#L30-L49)

## 期望行为

1. **统一检索入口。** 项目记忆的默认模式设为 `vector`，由运行环境自动选择 CPU 或 CUDA。`memory search` 的默认查询和 `memory brief --task` 中按任务找相关线索的步骤，都应走向量检索。用户用同一套配置和命令完成入库、检索与更新。 [当前 `brief` 实现](https://github.com/YS-Pan/basePack/blob/v0.6.4/experiments/20261106-basepack/src/basepack/memory/store.py#L495-L520)
2. **CPU 和 CUDA 生成的向量可互查。** 两端对相同的文本和图像采用同一模型版本、输入处理、向量维度和距离算法。CPU 建的索引可以在 CUDA 机器上查询，CUDA 建的索引也可以在 CPU 机器上查询。设备切换后应继续复用有效索引。当前向量兼容性由 `embedding_identity` 校验，其中包含数值精度。CPU 后端的精度方案需要和这个兼容规则一起设计。 [编码身份定义](https://github.com/YS-Pan/basePack/blob/v0.6.4/experiments/20261106-basepack/src/basepack/embedding/identity.py) · [向量兼容性检查](https://github.com/YS-Pan/basePack/blob/v0.6.4/experiments/20261106-basepack/src/basepack/memory/vectors.py#L70-L91)
3. **把一致性落实到查询结果。** 软件版本、原文版本、入库内容、配置和查询相同的情况下，返回的前 K 条记录、顺序、来源定位和过滤结果应一致。需要覆盖相似度非常接近、恰好落在第 K 条边界的记录。内部浮点差异应在统一的评分和排序规则内处理。
4. **提供已有项目的升级路径。** 已用 `text` 模式建库的项目，可以基于现有摘要和原文片段补建向量，保留来源和条目 ID。模型缺失或索引尚未建全时，显示具体状态与处理方法。纯文字结果或缺失向量导致的空结果不应作为一次成功的向量检索返回。

## 验收场景

| 场景 | 通过条件 |
| --- | --- |
| 无 CUDA 的 Windows 电脑首次使用 | 沿默认流程完成本地模型准备、向量建库和查询。测试资料写「每周导出数据库快照」，以「持久化数据多久备份一次」为问题，验证默认搜索和启动线索都通过向量检索找到该条目，并给出出处。 |
| 同一项目分别用 CPU 和 CUDA 建索引 | 对两份索引分别用 CPU、CUDA 发起同一组查询。四种组合的前 K 条记录、排序、过滤和来源一致。测试包含近似同分的候选。 |
| 在两台机器间搬迁已有项目 | 保留原文及记忆数据后可继续用原索引查询。修改原文并完成更新后，两台电脑都返回同样的新内容，旧版本按相同规则失效。 |
| 已有文字项目升级 | 可从已入库内容补建向量，保留条目 ID 和原文位置。构建期间可看到索引状态，建成后默认查询使用向量。 |
