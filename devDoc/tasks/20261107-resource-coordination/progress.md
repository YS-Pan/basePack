# 资源协调进度

更新：2026 年 11 月 8 日（北京时间）。

## 当前阶段

**R0–R7 已完成本机部署及真实验收。** 当前普通 wheel 为0.3.0，用户与basePack只提交官方GPU字段，由schedd原生JOB_TRANSFORM统一生成站点内部显存申请；普通容量仍由通用Condor节点维护。独立embedding按请求加载。现行结果见 [标准提交交付](standard-submit-result.md)，R6与R0–R5条件分别保留在 [通用节点改造](native-condor.md) 和 [历史交付](result.md)，使用者从 [项目接入](../../../docs/setup-project.md) 开始。

[R7计划](standard-submit-plan.md) 的R7.0–R7.4均已完成。背景9GiB、7164MiB普通池与4个同卡作业上限保持；未申报显存预订整池、非法值/超池/多GPU提交拒绝、原筛选保留及CPU独立运行均已验收。

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
| R6 | 普通容量迁至通用Condor配置；4个同卡GPU名额与7164MiB申报额度原生记账，容量查询、排队、GPU声明要求与CPU独立运行实测通过；0.2.0普通wheel及最大embedding联合验收 |
| R7 | 标准GPU提交与schedd站点映射解耦；通用capacity、原生转换/拒绝、4+1同卡排队、显存不足、默认整池、CPU、取消及embedding联合实测通过；0.3.0普通wheel与成对升级/回滚说明已交付 |

## 当前部署与检查

- 普通容量唯一来源：`C:/condor/config/60_resources.conf`。实际父slot为12 CPU/24576 MiB RAM、4个同卡GPU名额、7164MiB显存；背景总预留9216MiB，不再额外扣原2048MiB。`70_job_transforms.conf`在同一主配置加载，按官方属性转换新提交作业并追加原匹配条件；CPU不转换。
- 系统Python仍为 `C:/Program Files/Python313/python.exe`；0.3.0普通包在其 `Lib/site-packages/basepack`。机器TOML只维护路径与embedding自身设置，额度为 `[embedding].gpu_memory_mib=9216`。
- 独立交互用户broker43200在作业树外运行，无模型驻留；测试worker21732、broker18524与升级前broker8060已退出。不是登录自启服务，机器重启后按管理员说明启动。
- 当前wheel为 `dist/basepack-0.3.0-py3-none-any.whl`，35193 B，SHA256 `ee19d7ec94be4abc933f58854b62c5129ebf2763db6d42cd95033f40df4ee26a`；22份代码/模板/许可与源码和系统安装一致，源码与源码外普通wheel回归均22项通过。旧wheel与成对回滚备份保留。
- 原生14319/14320用官方字段完成正确CUDA计算；14322–14325四项同卡进展共同重叠16.163秒，14326因令牌用完排队后执行。5000+3000在尚有令牌时因显存不足排队；缺显存14329自动预订全池，CPU14331正常，取消后排队GPU恢复。原筛选及非法申报拒绝通过。
- 普通客户端14332–14334从源码外调用安装包；4×2048 token向量正确，推理期间6个GPU正确进展点，取消后同一共享worker继续。所有测试作业已清理，队列为空、资源全部归还，临时提交闸门已移除。
- R7证据在 `artifacts/standard-submit/`，完整结论见 [R7回执](standard-submit-result.md)。离线工具退出1的源代码原因已查清并留回归，真实服务器规则另行验收；SSPI原错保留且未改认证政策。R6证据仍在 `artifacts/native-condor/`，历史时限与R0–R5测量范围见 [原始结果](result.md)。

## 后续边界

R0–R7无未完成交付项。声明额度是合作约束，小矩阵验证调度记账，不提供显存硬隔离或吞吐结论；Python原生提交经subprocess调用官方CLI，现有cp39绑定不适配系统3.13，未宣称bindings API验收。当前仅核本机Windows、单NVIDIA GPU和固定VL2B配置，没有实施记忆数据库、自动重试、多机调度或远端发布。模型、输入上限或背景峰值变更先排空、重标定，再调整通用Condor节点容量。
