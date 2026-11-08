# 资源使用

先读项目 `basepack.toml`，用其中 runtime.python 启动工具，每次显式传配置绝对路径。以下 `python` 均指该解释器。机器已完成 [首次部署](administrator.md)；新项目先按 [项目接入](setup-project.md) 初始化。

## 共享 embedding

```powershell
python -m basepack --config '<project-config>' embed --text '待编码文本' --output '<project>/vectors.json'
python -m basepack --config '<project-config>' embed --image '<absolute-image>' --caption '图片说明' --output '<project>/image-vector.json'
python -m basepack --config '<project-config>' embedding status
```

多条输入可重复 `--text`，或用 `--inputs inputs.json` 传 UTF-8 JSON 数组，元素为字符串或 `{"text":"...","image":"<absolute-local-image>"}`。返回向量、模型/预处理身份、共享 PID 与输入回执。建库型批量输入和查询型单条输入使用同一客户端，不另起模型。

本版每请求 1–8 项；文本每项至多 64 KiB，实际含模板 token 上限由机器配置 max_length 固定，超限报错并保留原文，不截断。本机标定配置为 2048 token、纯文本 batch 4；含图输入逐项运行。每项最多一张静态图，原文件至多 32 MiB、4000 万源像素，预处理按 max_pixels 缩放，本机为 1048576。模型固定为 Qwen3-VL-Embedding-2B、FP16、2048 维 L2 归一化向量。

`--timeout` 覆盖排队、加载和推理等待。请求过期只结束本次调用；当前 forward 可继续到完成并丢弃结果。其他项目继续复用服务。客户端不启动 broker；未启动时按错误定位请管理员启动。

Python 可并发调用并只取消自己的请求：

```python
from basepack.config import load_config
from basepack.embedding.client import EmbeddingClient

client = EmbeddingClient(load_config("<absolute-project-config>"))
result = client.embed(["text"], timeout=120, request_id="my-request")
# 另一执行线程可调用 client.cancel("my-request")。
client.close()  # 只取消该客户端仍活动的请求。
```

## 普通重任务

把任务写为 UTF-8 JSON，再一次提交并等待。`executable` 使用明确绝对路径，`arguments` 是参数数组；`cwd` 相对项目根，省略时为项目根。例如：

```json
{
  "executable": "C:/Program Files/Python313/python.exe",
  "arguments": ["-c", "from pathlib import Path; Path('result.txt').write_text(str(sum(range(1000))))"],
  "cwd": ".",
  "cpus": 1,
  "memory_mib": 512,
  "disk_mib": 64,
  "queue_timeout": 300,
  "run_timeout": 600
}
```

```powershell
python -m basepack --config '<project-config>' resources capacity
python -m basepack --config '<project-config>' resources run --spec '<project>/job.json'
```

`capacity` 只读查询本机父 slot 的总容量与当前剩余量，来源是 HTCondor 实际发布的资源。`cpus`、`memory_mib`、`gpus` 为标准键；`MachineResources` 中其余资源在总量和剩余数量均有发布时，按原名和原生单位展示。本机 `gpus` 表示同卡共享名额。客户端按标准总容量核 CPU/RAM，GPU 申请由 Condor 站点策略判断，当前资源不足时排队。`run` 返回 job ID、终态、应用退出码及 stdout/stderr/event log 定位；应用失败、超时或未确认回收时 CLI 退出 1，原始应用退出码保留在 JSON。检查实际产物内容，应用退出 0 只说明正常退出。轻任务可直接运行，无需全部接入。

`memory_mib`、`disk_mib`、`gpu_memory_mib` 均用 MiB；disk 是执行 scratch 需求，提交前也查项目输出盘容量。GPU 任务增加正的 `gpu_memory_mib`，声明整个应用进程树的峰值，含 CUDA context、框架缓存和 workspace，并自行限制预分配。适配器只将它转换为官方 `request_gpus = 1` 与 `gpus_minimum_memory = <峰值> MB`。Condor 按本站点策略预订显存，并在名额和显存均足够时安排同卡共享。声明额度不等于驱动硬隔离，也不保证多作业加速。保留 Condor 分配的 CUDA_VISIBLE_DEVICES。

原生 Condor 用户无需安装 basePack，也使用相同官方字段，例如向自己的 submit 文件添加：

```ini
request_gpus = 1
gpus_minimum_memory = 3000 MB
```

`gpus_minimum_memory` 的官方含义仍是设备显存容量下限，原有 `requirements` 和 `require_gpus` 筛选继续生效。本站点额外把它作为作业的显存预订量，由提交节点统一转换；其他 Condor 站点是否采用此约定由当地管理员决定。原生申报须在提交时解析为正数，官方单位 `MB` 表示 MiB、`GB` 表示 GiB，预订量向上取整到整 MiB。依赖执行节点 `TARGET` 的动态表达式不支持。

本站申请 GPU 而省略显存时预订整个普通池，与其他 GPU 作业串行；显式 `undefined`、零、负值、不支持的表达式、超过全池或 `request_gpus > 1` 在提交时拒绝，错误使用官方参数名。资源暂时不足的有效申请排队。节点策略及背景预留由 [管理员](administrator.md#通用-htcondor-节点容量) 维护。

可用 `environment` 传显式环境。入口按 cpus 提供常用框架线程变量，但 starter 仍可能注入其他线程限制；worker 继承其最终值并记录，应用并行参数由调用者自行设置。Windows 中文、空格、引号与空参数经 UTF-8 任务文件交给随包薄 worker，避免参数数组经过 submit 的有损转换。

长任务接续：

```powershell
python -m basepack --config '<project-config>' resources submit --spec '<project>/job.json'
python -m basepack --config '<project-config>' resources status '<cluster.proc>' --analyze
python -m basepack --config '<project-config>' resources wait '<cluster.proc>' --timeout 300
python -m basepack --config '<project-config>' resources cancel '<cluster.proc>'
```

`wait --timeout` 只是本次观察时限，到期返回 observation_expired，作业继续运行。任务的 queue_timeout/run_timeout 是作业时限；run 到期撤销并确认回收，原生 Condor 时限在客户端离开后仍生效，但有策略检查间隔。timeout 与 cleanup_confirmed 分别表示时限结果和资源回收确认；cleanup_error 保留撤销或确认失败的原始信息，不能把 timeout 当作已释放。

`status --analyze` 返回原生匹配诊断。partitionable slot 当前资源不足时，Condor会模拟排空后分析，因此“可匹配”不等于当前有空闲配额；任务仍可处于queued。[Condor分析说明](https://htcondor.readthedocs.io/en/25.0/man-pages/condor_q.html#analyze)

默认同机共享目录访问，不传输模型、环境或源码。需要 scratch 隔离时填写 transfer_inputs 和 transfer_outputs：输入路径相对 cwd，按原生 basename 语义进入 scratch；要保留层级可传整个目录，应用用其目录名访问。输出路径相对 scratch，显式列出嵌套输出目录可回传到 cwd；正常或应用失败退出时回传，取消时不保证。submit 字段须能用本机原生编码表示，文件清单拒绝逗号、控制字符和 `$(...)` 宏；应用参数通过 UTF-8 JSON 传递，不受 submit 编码限制。显式输出缺件可能导致 Condor hold。

从项目 `.basepack/jobs/<submission-id>/` 的提交材料、stdout、stderr、事件日志和 worker.json 定位失败。worker 回执直接写共享项目目录，记录 launcher/应用 PID、实际 CUDA/线程环境和退出结果，不依赖取消时回传；关键应用回执也可写项目共享绝对路径。保留 job ID，可用 status --analyze 查看无匹配原因。

Python 同样可一次调用：

```python
import sys
from basepack.config import load_config
from basepack.resources import JobSpec, ResourceClient

jobs = ResourceClient(load_config("<absolute-project-config>"))
capacity = jobs.capacity()
result = jobs.run(JobSpec(executable=sys.executable, arguments=["analysis.py"],
                          cpus=2, memory_mib=2048, disk_mib=256))
```
