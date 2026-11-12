# F 编码失败诊断与 G 文件输入边界

2026-11-12（北京时间）。依据[计划 F/G](plan.md#fgh按实际故障补齐交付)，完成冻结输入查因、输入错误呈现修复及失败不发布回归；没有修改外部阵列项目或其数据库，也没有升级、重启共享 embedding 服务。

## 原因与复现

原服务日志在 09:04:03 记录 `actual tokens [2192,2145,360,337] exceed max_length=2048; no forward performed`，随后 `/predict` 返回 HTTP500。冻结批次的 geometry CSV 原文块超出已明确的 token 输入合同；不是由这条错误证明的显存、数据库或模型 forward 故障。`no forward performed` 只指失败的内部子批次，前一 HTTP 请求已经成功计算过向量。

已按失败时 0.10 wheel 的真实组装规则，核对 8 个来源的指定 SHA256，重建 36 条准确编码输入及输入版本。对当前已变化的两份原件，从原项目升级前恢复集合只读取得匹配版本。以服务现有本地 AutoProcessor 离线预处理，不加载模型权重、不重投请求，得到与原服务日志逐项完全相同的四元 token 签名；前一请求的两个子批次也均在限额内，与日志 POST200 吻合。

在 36 项均未命中缓存的重建条件下，第二 HTTP 请求的首个内部子批次按长度排序为：

| 候选序号 | 成员 | 原行范围 | 实际 token |
| --- | --- | --- | ---: |
| 16 | `sim-reference-geometry-csv-file-chunk-02` | 65–128 | 2192 |
| 15 | `sim-reference-geometry-csv-file-chunk-01` | 1–64 | 2145 |
| 9 | `sim-thesis-methods-policy-file-chunk-04` | 138–164 | 360 |
| 11 | `sim-validation-policy-file-chunk-01` | 1–31 | 337 |

全部 16 个 geometry CSV 原文块的离线计数均超限；后续块的计数是本轮预处理观察，不能称为原服务曾经调用的结果。原 trace 没有保存服务 uid、HTTP 正文或当刻缓存查询；时间链、精确输入签名和升级前后静态缓存证据强支持上述关联，但不冒充当刻抓包。实际 processor 默认附加特殊 token，简化为 `tokenizer.apply_chat_template` 会每项少 1，本轮没有用手工补数替代真实预处理。

## 实际修改

- `embedding/qwen3_vl.py` 区分已知输入合同错误与非预期模型错误。保持原 forward 前 token 检查；只在超限失败时再按原请求顺序预处理，报告从 0 开始的超限输入索引及每项 token 数，不重投模型、不截断原文。
- `embedding/service.py` 仅将该已知输入错误映射为 HTTP422，并返回不含输入正文的限额诊断；其它模型异常继续抛出。
- `embedding/client.py` 保留原 `HTTPError`、状态和可读响应流，附上最多 4096 字节响应正文。旧 LitServe 把普通 ValueError 隐藏为通用500，客户端无法凭通用正文恢复服务内部信息。
- `memory/candidate_vectors.py` 在原 HTTP 错误上附该请求的索引、成员 key、来源路径及行范围，方便作者定位并在语义边界拆块或缩短摘要后重新准备。未改变输入、缓存复用及发布事务。
- 资源模块说明和产品资源文档补充这一接续合同；维护批次写作约束由并行入口分支在随包 memory skill 的单一维护源补入。

G/BP-T22 当前版已经在 `Memory.prepare` 访问数据库前拒绝目录，报错明确要求文件及 `Get-ChildItem -File`，已有真实回归。本轮运行该回归通过，不重复修改 content 或增加目录递归能力。

## 实际检查

开发 Python 为 `tmp/basepack-dev/Scripts/python.exe`，已核 `basepack.__file__` 指向本路线 `src/basepack`。README 的 locked uv sync 遇网络重试，离线缓存又缺基础 torch wheel；停止该安装后复用本机已有开发依赖（Python3.13.17、PyTorch2.10.0+cu128、Transformers5.22.1、Sentence Transformers6.2.0、LitServe0.2.19），没有修改系统或服务安装。

- `test_embedding_client.py`、`test_embedding_model.py`、`test_memory_errors.py`、`test_memory_content.py`：**25 passed**。覆盖原 HTTP 错误/正文保留、无重投、原请求索引映射、已知输入422与内部异常原样抛出，以及当前目录输入边界。
- 隔离内存 SurrealDB4.0.0、端口18193，`test_memory_publication.py`：**7 passed**。新增两条回归分别在第一、第二编码请求抛 HTTP 错误；第二条先成功算出部分候选向量，再失败。两条均核 source、source_version、member（含向量）、node、semantic、change 全部保持发布前原值，并保留同一异常及成员定位，没有重试。
- 初次沙箱隐藏 launcher 未跨调用存活，7项 native 检查均在 setup 连接被拒，未计为功能失败或通过。随后仅将自有一次性测试 server 放到获准普通上下文，独立 `/ready=200` 后重跑通过；已停止并确认 launcher、surreal、conhost 三个已知 PID 全部退出。
- 冻结输入/原件哈希、精确 processor token 签名断言和 `git diff --check` 通过。未跑共享模型真实推理；原服务日志已给拒绝位置，不重复推送已知超限请求。

## 证据与余项

本机原证在根 [encoding 选留目录](../../../artifacts/runs/20261112-usage-rectification/encoding/)（Git忽略）：`service-evidence.md/json`、`input-reconstruction.md`、`frozen-input-{sources,candidates,strings,tokenizer-check}.json`、实际脚本、原服务日志选段及原版本代码。该目录另选留原 batch 与 trace；SHA256 分别为 `51916ea0264ea396fc3f98a52193f67f9f35b2d15318a974be1900157d7a9aa6`、`1782fd0c08c624b356d8c7c00152e270a78c3becb4ebdca3feea59a488dc4bfb`。临时测试、日志和 launcher 在根 `tmp/20261112-usage-rectification/encoding/`。

当前共享服务仍是0.5.0，保持原安装和限额；HTTP422与原请求索引只有管理员后续按普通升级流程安装服务包后才生效，本轮交付源码与隔离检查。原阵列冻结 batch 仍含超限块，需要其作者按 token 诊断拆分16个几何块，重新prepare/接受后再发布；本轮未修改或重提该外部批次，不能宣称原业务批次已成功入库。输入超限原因及呈现缺口已有复现和修复证据，原请求身份与瞬时缓存实录的缺口保留。
