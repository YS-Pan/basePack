# 资源协调进度

更新：2026 年 11 月 8 日（北京时间）。

## 当前阶段

**R0–R5 已完整交付并通过本机真实验收。** 稳定普通 wheel 已安装到系统 Python，机器级轻量 broker 独立运行，模型按请求加载；测试作业及模型进程已释放。最终结论、适用范围及原始证据入口见 [交付结果](result.md)，使用者从 [项目接入](../../../docs/setup-project.md) 开始。

本目录按用户指定保留为资源工具的维护入口；记忆检索、建图和数据库由 [独立任务](../20261106-memory-system/plan.md) 接续。

## 已交付

| 批次 | 实际完成 |
| --- | --- |
| R0 | Python 包、统一配置、随包模板、init/config show/按设施 doctor；系统 editable 新进程与最小普通 wheel；现有模型/Condor、slot 账户、中文路径、CPU/GPU 真结果及预算标定 |
| R1 | 作业外 broker 拥有单模型 worker，跨项目冷请求共实例，图文与批次有效；请求取消/截止隔离，空闲、worker/broker 崩溃与重启真实通过 |
| R2 | run/submit/status/wait/cancel，分字段编码、UTF-8 参数数组、明确单位/回传；实际预算核对、原生/客户端时限、held/失败诊断及回收确认 |
| R3 | 两种 GPU 启动顺序均有真实重叠进展；第二普通 GPU 排队，CPU/RAM 声明准入、并行/队列及超额拒绝通过 |
| R4 | 作业内冷请求后取消作业，共享模型及另一项目继续；父子孙进程和异常退出回收、请求局部取消/截止、空闲/崩溃回归通过 |
| R5 | 普通 wheel 安装到系统 site-packages；源码外两项目、移动项目、新检出、图文/Condor 调用及最终 GPU 并行通过；使用/管理员文档、示例及 resources skill 已交付 |

## 当前部署与检查

- 机器配置：`D:/AgentTools/basepack.toml`；Condor 派生片段：`C:/condor/config/60_basepack.conf`。实际父 slot 为12 CPU/24576 MiB，显存 T16380/E9216/S2048/B5116 MiB，预算版本 `5dd7fc9014b383e0`。CPU/RAM 变更经空队列 peaceful 重启 startd 后核实际值。
- 系统 Python：`C:/Program Files/Python313/python.exe`；普通包：其 `Lib/site-packages/basepack`。独立 broker PID26696，由交互用户在作业树外启动，当前无模型 worker；不是登录自启服务，机器重启后按管理员说明启动。
- 最终 wheel：`dist/basepack-0.1.0-py3-none-any.whl`，35350 B；运行源码版本 `9fc1d4d`。22份运行代码/模板/许可与源码、wheel、实际安装逐字节一致。
- 普通 wheel 模式11项回归通过；resources skill静态校验通过。最终验收job14295退出0、回收确认，最大文本4×2048 token推理期间有50个普通GPU正确进展点，两个源码外项目共worker16464。
- 无匹配诊断补验14298：实际queued，原生报告明确Disk条件0slot，取消后清理确认。CPU满配时better-analyze可模拟排空后称可匹配，其诊断范围已写入使用文档；补验结束队列为空，broker26696保持。
- 原生执行3秒上限实测11秒移除，排队3秒上限实测52秒，存在策略周期；run另有客户端有界等待。WDDM CUDA free是device-view，全卡证据使用外部nvidia采样，均不参与动态抢占准入。
- R5捕获的空查询解析回归已修复并重新构建、重装、完整重验；非空无效JSON仍报原错。详细证据集中在 `artifacts/r0/`、`artifacts/condor/`、`artifacts/resource-acceptance/`、`artifacts/r5/`。

## 后续边界

本轮无未完成交付项。资源预算是合作约束；RAM验证声明和排队，没有实际分配全部额度。首版仅本机Windows、单NVIDIA GPU及固定VL2B配置；没有实施记忆数据库、自动重试、多机调度或远端发布。后续按实际需求另开实施批次，模型/输入上限变更先排空、重标定并发布预算。
