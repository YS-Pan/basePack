# basePack 防御性写作与防御式编程问题清单

- 评审对象：`YS-Pan/basePack` 0.6.4（commit `0566e76`）
- 评审方式：在一台干净的 Windows 机器上按公开文档实际部署（Python 3.13 + SurrealDB 4.0.0 + 文字记忆闭环全部跑通），并在 Python 3.14 上做了兼容性实测；随后逐条核对文档与源码
- 结论先说：**功能是好的，安装文档和代码里的"防御"是坏的。**

一句话概括问题：

> 项目把"作者没验证过"写成了"用户不可用"，把"我的机器是什么"写成了"你的准入门槛"。

---

## 0. 摘要

| # | 问题 | 典型位置 | 后果 |
|---|---|---|---|
| 1 | 用具体 GPU 型号/驱动版本代替能力条件 | `administrator.md:16`、`:141`、`README.md:12` | RTX 5060 明明能跑，却被文档判为"未验收"，用户不知道能不能用 |
| 2 | 把"验证边界"写进使用文档 | `administrator.md:7`、`:58`、`:122`、`:183`、`:221` | 用户要的是"怎么做"，读到的是"作者没验过什么" |
| 3 | 逐段免责声明，同一句"X 不能代替 Y"重复十余次 | 产品文档 793 行 | 读者丧失判别力，真正的警告被淹没 |
| 4 | 版本表当支持契约 | `administrator.md:9-16` | 任何新版本都被默认判为不确定 |
| 5 | Python 3.14 上限 pin 是防御性的，不是事实约束 | `pyproject.toml:12` | 实测 3.14 完全可用，用户却被拒绝安装 |
| 6 | 代码用兜底值把故障变成"正常值" | `jobs/client.py:67-70`、`:148-167`、`:226-234` | 真实故障被掩盖成 0、空集或"已确认" |

这些都不是孤立的措辞问题，它们**与项目自己写下的规则直接冲突**。

---

## 1. 判据：先看项目自己的规则

评审用的不是外部标准，是仓库里已经写好的三条：

**（1）`AGENTS.md:21`**

> 避免防御式编程，采用 `let it crash`：内部按明确契约调用，非预期错误直接抛出并保留原始信息；只捕获有明确处理办法的异常，不用默认值、静默回退、盲目重试或层层校验审阅掩盖失败。

**（2）`AGENTS.md:20`**

> 保持实现、文档和 prompt 简短。先跑通最短实际流程，再优化。

**（3）`devDoc/documentation.md:21`**

> 环境实测是有日期的观测，兼容性要求由依赖声明与实际验证支持。

第（3）条是最关键的：它自己规定了**"环境实测"是 devDoc 里有日期的观测，"兼容性"由依赖声明加实际验证支持**。可是 `administrator.md`（面向用户的安装文档）恰恰把作者机器的一次观测（RTX 4060 Ti / 驱动 617.42）写成了部署前置条件。这违反了项目自己的文档分层规则，不是外部口味问题。

---

## 2. 文档问题

### 2.1【P0】用具体型号/版本代替能力条件

这是最该改的一类。

| 位置 | 原文（节选） | 问题 |
|---|---|---|
| `administrator.md:16` | "NVIDIA 驱动…；**已测 617.42、RTX 4060 Ti 16380 MiB**" | 把一次本机观测当作支持矩阵 |
| `administrator.md:141` | "**当前已测硬件为一张 RTX 4060 Ti、16380 MiB；其它 GPU 和最低显存尚未验收。**" | 明确宣布"别的卡不行"，事实上没有依据 |
| `README.md:12` | "图文和作业的既有实测**使用作者机设施（RTX 4060 Ti 16 GB、CUDA 12.8）**。完整新机资源部署路径已提供，**仍待独立机器验收**" | 把"作者机器的型号"写进产品首页 |
| `devDoc/system/environment.md:100` | "GPU 元数据…返回 RTX 4060 Ti、16380 MiB" | 这行是**对的**——它待在 devDoc 的"环境实测"里，本来就该待在那里 |

**为什么这是防御性写作而不是严谨：**

1. **型号是无穷枚举，永远追不上。** 用户手上的卡可以是 3060、4060、4070、5060、A2000……每出一个新型号文档就要"再验收"一次。真正的约束是"能跑 cu128 的 FP16 运算"加"显存够容纳模型与峰值"，这是**能力条件**，可以一次写清，永不追加。
2. **型号清单会制造伪门槛。** 本机是 RTX 5060（8151 MiB）。按 `administrator.md:141` 的字面意思，它属于"其它 GPU，尚未验收"，也就是**文档宣布不可用**。可它与 4060 Ti 的差别只是显存更小，属于"跑不跑得起来"的预算问题，不是"支不支持"的问题。
3. **同一条规则已经写过了。** `administrator.md:141` 后半句就是能力条件："所选 NVIDIA GPU 必须能运行锁定的 PyTorch cu128 FP16 运算，且容纳下述实际负载。"既然这句已经完整表达了约束，前面的型号就是**冗余的门**——它不增加信息，只增加拒绝。

**建议改写：**

> 需要一块能运行 PyTorch cu128 FP16 的 NVIDIA GPU，并能容纳模型权重与峰值负载。
> 用 `nvidia-smi` 记录整卡显存 T，按下方预算表为 embedding 划出 E、为普通作业留出 G。
> 显存不足时的症状是加载失败或 OOM，处理方法见"首次准备图文模型"。

删掉型号、删掉驱动版本号、删掉"尚未验收"。驱动只写"安装该卡适用的、支持 CUDA 12.8 的版本"。若真要保留实测记录，放进 `devDoc/system/environment.md`，并且写成**日期 + 环境**的观测，不写进支持范围。

### 2.2【P0】把"验证边界"写进使用文档

| 位置 | 原文（节选） |
|---|---|
| `administrator.md:7` | "首次安装命令来自官方说明，**不表示已经完成空白机器重装**" |
| `administrator.md:58` | "doctor 的只读结果**不能代替**该验证" |
| `administrator.md:122` | "**PID、ready 或 doctor 各自都不能代替**这些后续调用" |
| `administrator.md:181` | "E 只控制 PyTorch 分配器，**不能代替**外部全卡峰值" |
| `administrator.md:183` | "**作者已有服务的结果不能代替这些检查**" |
| `administrator.md:221` | "只是**作者机的样例**，不能原样套到新机器" |
| `README.md:12` | "更广泛的质量、性能和费用收益**仍待评估**" |
| `resources.md:15` | "**管理员须按目标硬件验证这些负载**" |

这些句子的共同结构是：**先给步骤，再声明这个步骤不算数。**

站在读者角度，`administrator.md` 是"我要怎么装"，而每装完一步就被提醒"这不能证明任何事"。读者最后**无法判断自己是否成功**——因为文档拒绝承认任何成功的判据。这不是严谨，是**把作者的举证焦虑转嫁给了用户**。

**建议：**

- 使用文档只回答三件事：**需要什么条件、按什么步骤做、失败时看哪里**。
- "我验过什么、没验过什么、证据在哪"集中在 `devDoc/` 一处维护（那里已经有 `environment.md` 和任务结果页）。
- 若确有风险必须提示，写成**可观测的症状**而不是举证责任，例如"若日志出现 `VCRUNTIME140` 缺失，安装 VC++ 运行库"，而不是"作者未在空白机器验证过"。

### 2.3【P1】逐段免责声明，把警告稀释成噪音

对产品/使用文档（6 份、793 行）做词频统计：

| 措辞 | 次数 |
|---|---|
| `必须` | 9 |
| `仅` | 8 |
| `不能代替` | 5 |
| `尚未` | 4 |
| `不保证` | 3 |
| `不代表` | 2 |
| `待验` | 2 |

793 行里 33 处这类限定语，平均**每 24 行一次**。`resources.md` 连续三节以同样的句式收尾：

- `resources.md:79` "**不能**把 timeout 当作已释放"
- `resources.md:81` "'可匹配'**不等于**当前有空闲配额"
- `resources.md:83` "取消时**不保证**回传"

单看每句都对，连读则让人对**任何**结论都不再信任，包括真正危险的那些（例如 `:79` 的"timeout 不等于已释放"是必须让用户看见的）。

**建议：** 在文档开头一次性声明证据口径（例如"本文档只描述已实测的路径；未覆盖的条件会在对应小节标出"），正文只在**会造成数据损失或误判**的位置保留限定语，其余删除。判断标准：删掉这句，用户会不会做出错误操作？不会就删。

### 2.4【P1】版本表当成了支持契约

`administrator.md:9-16` 的表格标题是"工具及**已测版本**"，列出 Python 3.13.17、uv 0.13.7、SurrealDB 4.0.0、Shawl 1.9.0、HTCondor 25.4.0。

问题不在记录版本，而在**它被当作准入条件使用**：表格里没有的版本，读者只能理解为"未验收 → 风险自负"。这与 `pyproject.toml:12` 的精确 pin 叠加，形成双重封锁：

```toml
requires-python = ">=3.13,<3.14"
```

**建议：** 安装文档写"最低要求 + 已知不兼容"，例如"Python ≥3.13（3.14 见下）；SurrealDB ≥4.0"。具体测过的版本号标注为"本次验证使用"，并说明"更高版本通常可用，遇到问题先回退到此版本"。

### 2.5【P1】要求用户自证作者已经证过的事

`administrator.md:183`：

> 验证后多个项目可连接这一份模型。新机器从头下载、首次模型加载及 GPU 并存**仍须在目标硬件执行**；**作者已有服务的结果不能代替这些检查**。

这句话的实践含义是：**用户必须重做作者做过的全部验收，才算完成部署。** 但用户没有作者的验收清单、采样脚本和判定标准，所以永远达不到文档要求的证据等级——最后只能靠"我觉得它好了"来结束，这正是文档想避免的。

**建议：** 把验收改写为**冒烟测试**（一段能跑通的命令 + 预期输出），而不是"请重新验证峰值显存"。作者的完整标定过程留在 devDoc；用户只需要知道"跑这条命令，看到 2048 维向量就算通"。

### 2.6【P0】Python 3.14 的上限 pin 是防御性的，已被实测证伪

`pyproject.toml:12`：`requires-python = ">=3.13,<3.14"`

我在这台机器上做了对照实测：

| 检查 | 3.13 | 3.14 |
|---|---|---|
| 测试套件 | 148 通过 / 10 失败 / 43 跳过 | **完全相同**，失败的 10 个 ID 一致 |
| 失败原因 | 缺 embedding extra（torch/PIL/sentence-transformers） | 同左，与解释器版本无关 |
| `init` / `config show` / `doctor` | 通过 | 通过 |
| 记忆完整闭环 prepare→apply→search→read→neighbors | — | **exit 0**，中文分块/检索/读原文正常 |
| `memory init` / `guide` / `brief` | 通过 | 通过 |
| 弃用告警（`-W error::DeprecationWarning`） | — | 仍 148 通过，**自有代码零告警** |
| 移除的 stdlib API（distutils/pkg_resources/imp/cgi/audioop…） | — | 源码中**无匹配** |

安装时被挡住的只有元数据：

```
ERROR: Package 'basepack' requires a different Python: 3.14.10 not in '<3.14,>=3.13'
```

**这不是"3.14 不支持"，是"作者没在 3.14 上试过，于是禁止"。** 按 `documentation.md:21` 自己的规则，兼容性应由依赖声明与实际验证支持——现在两者都支持 3.14，只有 pin 在反对。

**建议：** 改为 `>=3.13,<3.15`，重新生成 `uv.lock`，并把 README 的"支持范围为 Windows、Python 3.13"改成"Python ≥3.13"。

---

## 3. 代码问题

以下均经我实际阅读核对（行号为当前 `experiments/20261106-basepack/src/basepack/` 下的真实行号）。

### 3.1【P1】缺失字段被兜底成 0，与"没有资源"无法区分

`jobs/client.py:67-70`

```python
"total": {key: slot.get("TotalSlot" + attribute, 0) if key == "gpus"
          else slot["TotalSlot" + attribute] for key, attribute in resources.items()},
"available": {key: slot.get(attribute, 0) if key == "gpus"
              else slot[attribute] for key, attribute in resources.items()}})
```

注意这个不对称：非 GPU 字段用 `slot[...]`（缺失即崩溃，正确），GPU 字段用 `.get(..., 0)`。于是**站点根本没有定义 GPU 资源**时，`capacity()` 会平静地报告 `total: 0, available: 0`，与"这台机器有 0 张卡"完全同形。用户看到的是"容量为 0"，不是"你的 Condor 没配置 GPU 资源"。

按 `let it crash`，这里应该和上面一行一样直接 `slot[...]`。

### 3.2【P1】提交响应丢失后，用反查把失败改写为成功

`jobs/client.py:93-106`

```python
try:
    result = self._call("condor_submit", "-terse", submit)
except (RuntimeError, subprocess.TimeoutExpired) as error:
    # A lost submit response does not authorize another submission.
    matches = self._ads("condor_q", "-constraint", f'BasePackSubmissionId == "{token}"')
    ...
    submitted["submit_response_error"] = str(error)
```

注释本身是对的（不能重复提交），但实现把"提交命令失败"降级成了一个附注字段 `submit_response_error`，然后继续当作**提交成功**走完全流程。如果 `condor_q` 与 `condor_history` 恰好都查不到（时序、权限、AUTHENTICATE 失败都可能导致），才 `raise`。

也就是说：**大多数情况下故障被记录成一行备注，而不是失败。** 建议：只有反查**确实拿到 job ID** 才算成功，并在返回值里明确 `state: "unverified_submit"`，让上层决定是否继续；否则原样抛出，不做补救。

### 3.3【P1】用字符串猜作业状态

`jobs/client.py:140-142`

```python
if (ad.get("HoldReasonCode") in (46, 47) or
        "periodicremove" in (ad.get("RemoveReason") or "").lower().replace("_", "")):
    result["timeout"] = "execution" if ad.get("JobCurrentStartExecutingDate") else "queue"
```

以及 `:197`

```python
if "execution time" in (result["reason"] or "").lower():
```

超时判定依赖 **Condor 的英文提示文本**。这既脆弱（换语言、换版本、改措辞就失效），又掩盖了真实状态：判定不出来时不是报错，而是**不设 `timeout` 字段**，让调用方以为一切正常。

建议：只依赖 `HoldReasonCode` 等结构化字段；无法判定时显式返回"未知终止原因"并保留原始 `reason`，不静默留空。

### 3.4【P2】清理确认会在无 PID 时"空集通过"

`jobs/client.py:226-234`

```python
def _worker_pids(ad: dict) -> set[int]:
    if "BasePackPayload" not in ad:
        return set()
    ...
    if not receipt.exists():
        return set()
```

空集进入 `_confirm_cleanup`（`:148-167`）后，`worker_gone` 恒为 `True`，只要历史记录存在就返回：

```python
return {"cleanup_confirmed": True, "cleanup_scope": "known_processes_and_condor_history", ...}
```

**"我没找到进程"被当成了"进程已退出"。** 如果 worker 回执文件恰好还没写出或路径失效，清理会被确认为成功，而实际进程可能仍在跑。建议：把"无 PID 可核"单独返回为 `cleanup_scope: "condor_history_only"`，与真正核过 PID 的情况区分开。

### 3.5【P2】用 `max(0, …)` 抹平时间异常

`jobs/client.py:127-129`

```python
"elapsed_seconds": max(0, end - ad["QDate"]) if end is not None else None,
"queued_seconds": max(0, (started or end) - ad["QDate"]) if started or end is not None else None,
"running_seconds": max(0, end - started) if started and end is not None else (None if started else 0),
```

时间出现负数意味着时钟、时区或 ClassAd 字段出了问题——这是**应该暴露的信号**，却用 `max(0, …)` 压成了 0。同时 `running_seconds` 在从未启动时返回 `0`，与"瞬间跑完"无法区分。建议：负数直接暴露原始值（或抛错），未启动返回 `None`。

### 3.6【P2】doctor 在缺 `nvidia-smi` 时静默通过

`project/doctor.py:30-32`

```python
smi = shutil.which("nvidia-smi")
if smi:
    checks["gpu"] = subprocess.check_output([...])
```

`--facility embedding` 的意义是"这个环境能不能跑图文"，但**没有任何 NVIDIA 驱动时 doctor 依然成功返回**，只是少一个 `gpu` 字段。这与文档 `administrator.md:58/122` 反复声明"doctor 不能证明任何事"互为因果：代码不敢断言，文档只好不停免责。

建议：`facility in ("embedding", "all")` 时，缺 `nvidia-smi` 直接报 `FileNotFoundError`，与同函数里 `model_root` 缺失的处理保持一致（那里就是直接抛的）。

### 3.7【P2】客户端重复校验 Condor 的职责

`jobs/client.py:82-86`

```python
requested = {"cpus": spec.cpus, "memory_mib": spec.memory_mib}
capacity = self.capacity()
if not any(all(slot["total"][key] >= amount for key, amount in requested.items())
           for slot in capacity["slots"]):
    raise ValueError(f"Job request {requested} exceeds local Condor slot capacity: ...")
```

提交前先查一次容量，再让 Condor 自己判断。这在**多作业并发**时会给出错误结论：此刻容量不足是正常的（本来就该排队），却被客户端拒绝。文档 `resources.md:66` 也写了"资源暂时不足的有效申请排队"——**代码与文档在这里互相打架**。建议删掉这段预检，把排队交给 Condor，只在 `capacity` 命令里展示信息。

### 3.8 需要澄清：这些**不是**问题

为避免误伤，以下几处我核对后认为应保留：

- `project/config.py:11-23`：schema_version、绝对路径校验，直接 `raise`，符合 let it crash。
- `project/init.py:27-30`：配置或入口已存在直接 `FileExistsError`，不做覆盖，正确。
- `memory/store.py:95-104`：`except HTTPError` 后 `add_note` 再 `raise`，保留了原始错误，正确。
- `memory/store.py:135-140`：`FileNotFoundError` 仅在**已登记来源**时转成 `deleted`，这是有明确处理办法的捕获，正确。
- `resources.md` 的多处 Condor 语义说明（`:79` timeout≠已释放、`:81` 可匹配≠空闲）：这些是**会导致误判**的限定语，属于 2.3 节建议保留的那一类。

---

## 4. 建议的写作/编程准则（可直接并入 `AGENTS.md`）

1. **能力条件优先于型号清单。** 文档描述"需要什么能力"，不描述"作者有什么机器"。型号、驱动号、内存容量一律进 devDoc 的日期化观测。
2. **使用文档不承担举证责任。** 用户文档回答"条件、步骤、失败症状"；"我验过什么"属于 devDoc。
3. **限定语按后果保留。** 删掉这句用户会不会做错事？不会就删。每份文档开头声明一次证据口径即可。
4. **版本用区间，不用点。** 写最低要求 + 已知不兼容；"已测版本"只作为"本次验证使用"的附注。
5. **声明支持就要能装。** `requires-python`、依赖 pin 与实际验证必须一致；新增上限前先跑一遍测试套件，用结果说话。
6. **兜底值只能用于外部可选字段。** 内部契约字段缺失时崩溃，不返回 0、空集、空字符串。
7. **不猜状态。** 结构化的东西用结构化字段判断；猜不出来就报"未知"，不要留空让调用方误判。
8. **"没找到" ≠ "已清理"。** 无法核实的成功必须显式降级标注，不能与其他成功同形。
9. **客户端不替服务端做决定。** Condor/SurrealDB 的准入与排队是它们的职责；客户端重复校验会与文档冲突（见 3.7）。

---

## 5. 附：本次复现方式

- 部署：GitHub 直连不通 → `ghproxy.net` 镜像 clone；Python 3.13.17（winget）；`pip install ./experiments/20261106-basepack`；SurrealDB 4.0.0 官方 CDN 下载；`memory init` + 完整闭环通过。
- 3.14 实测：`pip install --ignore-requires-python` 后运行上述全部检查；测试命令：
  `pytest -c experiments/20261106-basepack/pyproject.toml experiments/20261106-basepack/tests -q`
- 词频统计：对 `README.md`、`experiments/20261106-basepack/README.md`、`docs/*.md` 共 6 文件 793 行做字符串计数（Python，非人工估算）。
- 行号核对：全部引用均以当前仓库文件为准；`Get-Content` 在 Windows 上计数与真实行号存在偏差，统计与引用使用 Python `splitlines()` 与 ripgrep 复核。

### 评审覆盖范围（诚实声明，避免本文档自己也过度声明）

- **逐行读过**：`project/config.py`、`project/init.py`、`project/doctor.py`、`jobs/client.py`、`jobs/submit.py`、`memory/vectors.py`、`memory/content.py`（`detect_changes` 部分）、`memory/store.py`（执行与来源加载部分）、`embedding/qwen3_vl.py`。
- **未逐行复核**：`embedding/service.py`、`embedding/admin.py`、`embedding/identity.py`、`embedding/client.py`、`jobs/worker.py`、各 `cli.py`、`__main__.py`。
- 在第 3 节给出问题的同时，必须说明：**上述已读模块中，除了列出的条目，其余实现是克制的**——`submit.py` 的字段校验、`vectors.py` 的来源版本核对、`store.py` 的 `add_note` 后重抛、`init.py` 的已存在即报错，都符合 `let it crash`。防御性问题不是"全部代码都这样"，而是**集中在文档和 Condor 观测层**。这一点如果不写清楚，这份评审本身也会变成过度声明。
