# 资源使用

先读项目 `.basepack/instructions.md` 和实际配置，用其中 runtime.python 启动工具，每次显式传配置绝对路径。以下 `python` 均指该解释器。向量检索和图文编码需要共享模型服务，普通重任务需要 HTCondor；显式 `search_mode='text'` 的记忆无需这两项设施。新项目先按 [项目接入](setup-project.md) 初始化，设施由管理员按 [首次部署](administrator.md) 准备。

## 共享 embedding

共享服务支持 CPU 与 CUDA；机器默认 `device='auto'` 使用可用 CUDA，否则使用 CPU，也可显式选择 `cpu` 或 `cuda:0`。CPU 路径无需 NVIDIA 工具或 GPU 预算；CUDA 预算由管理员配置。两端使用相同模型、前处理与 FP16，设备不改变 embedding_identity，同身份索引可跨设备复用。

```powershell
python -m basepack --config '<project-config>' embed --text '待编码文本' --output '<project>/.basepack/vectors.json'
python -m basepack --config '<project-config>' embed --image '<absolute-image>' --caption '图片说明' --output '<project>/.basepack/image-vector.json'
python -m basepack embedding --machine-config '<machine-config>' status
```

成功时 `--output` 命令返回 count、embedding_identity、worker pid 和输出位置，文件保存 vectors；单条文字冒烟应得到 count 为 1、2048 维向量。未指定 `--output` 时直接返回向量。连接失败请管理员检查服务日志与状态，模型或 CUDA 错误保留原始信息后修正对应配置。

多条输入可重复 `--text`，或用 `--inputs inputs.json` 传 UTF-8 JSON 数组，元素为字符串或 `{"text":"...","image":"<absolute-local-image>"}`。建库批量输入与单条查询共用一份模型。

每请求 1–8 项，文本每项至多 64 KiB。实际含模板 token 上限由机器 max_length 固定，超限在模型 forward 前报错，原文和图片均不静默截断。每项最多一张静态图，原文件至多 32 MiB、4000 万源像素；预处理按 max_pixels 缩放。机器模板为 2048 token、max_pixels 1048576、纯文本 batch 4，含图请求 batch 固定为 1；管理员须按目标硬件验证这些负载。模型为 Qwen3-VL-Embedding-2B、FP16，输出 2048 维 L2 归一化向量；浮点范数有舍入误差。

`--timeout` 是客户端连接和读取的等待期限；到期报错，服务端排队或已开始的推理仍可继续。机器配置 `queue_timeout` 是 LitServe 的排队期限，出队时检查；超过期限的请求可能要等前一项推理结束才收到 504。它不限制已经开始的推理。超时或断开不自动重投，也不停止另一项目共用的模型。

模型随 Windows 服务启动而加载并常驻。客户端只连接机器配置的 endpoint；服务未运行时请管理员启动。Python 使用同一入口：

```python
from basepack.project.config import load_project_config
from basepack.embedding import EmbeddingClient

client = EmbeddingClient(load_project_config("<absolute-project-config>").machine)
result = client.embed(["text"], timeout=120)
```

服务使用原生 `POST /predict`（JSON `{"inputs":[...]}`）、`GET /health` 和 `GET /info`。`status` 返回健康与模型信息，新服务的 model 字段还报告实际 device 和 dtype；兼容旧服务仍可使用。模型身份变化时补建兼容向量，步骤见 [记忆使用](memory.md)。服务停止、升级和日志入口见 [管理员说明](administrator.md#共享服务与身份)。

## 普通重任务

把任务写为 UTF-8 JSON，再一次提交并等待。`executable` 使用明确绝对路径，`arguments` 是参数数组；`cwd` 相对项目根，省略时为项目根。例如：

```json
{
  "executable": "<absolute-job-python.exe>",
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
python -m basepack --config '<project-config>' jobs capacity
python -m basepack --config '<project-config>' jobs run --spec '<project>/job.json'
```

`capacity` 只读查询父 slot 的总容量与当前剩余量，来源是 HTCondor 实际发布的资源。`cpus`、`memory_mib`、`gpus` 为标准键；纯 CPU 节点未发布 GPU 数量时显示 0。`MachineResources` 中其余资源在总量和剩余数量均有发布时，按原名和原生单位展示。采用随包单卡策略时，`gpus` 表示同卡共享名额。资源匹配与准入由 Condor 及其站点策略负责；当前资源不足的有效申请排队，无法匹配时用 `status --analyze` 查看原因。`run` 返回 job ID、终态、应用退出码及 stdout/stderr/event log 定位；应用失败、超时或未确认回收时 CLI 退出 1，原始应用退出码保留在 JSON。示例应写出内容为 499500 的 result.txt；检查实际内容，应用退出 0 只说明正常退出。轻任务可直接运行，无需全部接入。

`memory_mib`、`disk_mib`、`gpu_memory_mib` 均用 MiB；disk 是执行 scratch 需求，提交前也查项目输出盘容量。GPU 任务增加正的 `gpu_memory_mib`，声明整个应用进程树的峰值，含 CUDA context、框架缓存和 workspace，并自行限制预分配。适配器只将它转换为官方 `request_gpus = 1` 与 `gpus_minimum_memory = <峰值> MB`。Condor 按本站点策略预订显存，并在名额和显存均足够时安排同卡共享。声明额度不等于驱动硬隔离，也不保证多作业加速。保留 Condor 分配的 CUDA_VISIBLE_DEVICES。

原生 Condor 用户无需安装 basePack，也使用相同官方字段，例如向自己的 submit 文件添加：

```ini
request_gpus = 1
gpus_minimum_memory = 3000 MB
```

`gpus_minimum_memory` 的官方含义仍是设备显存容量下限，原有 `requirements` 和 `require_gpus` 筛选继续生效。本站点额外把它作为作业的显存预订量，由提交节点统一转换；其他 Condor 站点是否采用此约定由当地管理员决定。原生申报须在提交时解析为正数，官方单位 `MB` 表示 MiB、`GB` 表示 GiB，预订量向上取整到整 MiB。依赖执行节点 `TARGET` 的动态表达式不支持。

采用随包单卡策略时，申请 GPU 而省略显存会预订整个普通池，与其他 GPU 作业串行；显式 `undefined`、零、负值、不支持的表达式、超过全池或 `request_gpus > 1` 在提交时拒绝，错误使用官方参数名。资源暂时不足的有效申请排队。节点策略及背景预留由 [管理员](administrator.md#condor-容量与策略) 维护。

可用 `environment` 传显式环境。入口按 cpus 提供常用框架线程变量，但 starter 仍可能注入其他线程限制；worker 继承其最终值并记录，应用并行参数由调用者自行设置。Windows 中文、空格、引号与空参数经 UTF-8 任务文件交给随包薄 worker，避免参数数组经过 submit 的有损转换。

长任务接续：

```powershell
python -m basepack --config '<project-config>' jobs submit --spec '<project>/job.json'
python -m basepack --config '<project-config>' jobs status '<cluster.proc>' --analyze
python -m basepack --config '<project-config>' jobs wait '<cluster.proc>' --timeout 300
python -m basepack --config '<project-config>' jobs cancel '<cluster.proc>'
```

`wait --timeout` 只是本次观察时限，到期返回 observation_expired，作业继续运行。任务的 queue_timeout/run_timeout 是作业时限；run 到期撤销并确认回收，原生 Condor 时限在客户端离开后仍生效，但有策略检查间隔。timeout 与 cleanup_confirmed 分别表示时限结果和资源回收确认；cleanup_error 保留撤销或确认失败的原始信息，不能把 timeout 当作已释放。

`cleanup_scope` 说明回收确认的依据：`known_processes_and_condor_history` 表示已有原生历史且 `checked_pids` 中进程均已消失；`condor_history_never_started` 表示原生历史明确记录执行次数为 0。曾执行或执行记录不完整、又缺少 worker PID 时，返回 `cleanup_confirmed=false` 和 `condor_history_only`，从任务目录的 worker 回执及 Condor 日志继续定位。

时间差直接保留原生时间的计算结果，负值可用于定位时钟或记录异常，未发布的时间为 `null`。超时分类依据实际观察到的作业时限或原生 hold code；终态原因无法分类时 `timeout=null`，保留 `reason`、`hold_reason_code` 和 `hold_reason_subcode`，供调用方诊断。

`status --analyze` 返回原生匹配诊断。partitionable slot 当前资源不足时，Condor会模拟排空后分析，因此“可匹配”不等于当前有空闲配额；任务仍可处于queued。[Condor分析说明](https://htcondor.readthedocs.io/en/25.0/man-pages/condor_q.html#analyze)

默认同机共享目录访问，不传输模型、环境或源码。需要 scratch 隔离时填写 transfer_inputs 和 transfer_outputs：输入路径相对 cwd，按原生 basename 语义进入 scratch；要保留层级可传整个目录，应用用其目录名访问。输出路径相对 scratch，显式列出嵌套输出目录可回传到 cwd；正常或应用失败退出时回传，取消时不保证。submit 字段须能用本机原生编码表示，文件清单拒绝逗号、控制字符和 `$(...)` 宏；应用参数通过 UTF-8 JSON 传递，不受 submit 编码限制。显式输出缺件可能导致 Condor hold。

从项目 `.basepack/jobs/<submission-id>/` 的提交材料、stdout、stderr、事件日志和 worker.json 定位失败。worker 回执直接写共享项目目录，记录 launcher/应用 PID、实际 CUDA/线程环境和退出结果，不依赖取消时回传；关键应用回执也可写项目共享绝对路径。保留 job ID，可用 status --analyze 查看无匹配原因。

Python 同样可一次调用：

```python
import sys
from basepack.project.config import load_project_config
from basepack.jobs import JobSpec, CondorClient

jobs = CondorClient(load_project_config("<absolute-project-config>"))
capacity = jobs.capacity()
result = jobs.run(JobSpec(executable=sys.executable, arguments=["analysis.py"],
                          cpus=2, memory_mib=2048, disk_mib=256))
```
