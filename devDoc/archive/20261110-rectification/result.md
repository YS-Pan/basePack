# 整改结果：0.7.0 与 0.7.1 接续

2026-11-10。按[整改计划](plan.md)先完成故障、查询/维护和 CPU/CUDA 三批实现并安装 0.7.0。随后按用户经另一聊天明确转达的要求接续 0.7.1，删除独立纯 text 运行模式；最终检查与普通安装已完成，接续见[进度](progress.md)。工程取舍 skill 独立保留，按用户要求不安排测试，长期使用反馈沿其[结果](../20261110-engineering-judgment/result.md)维护。

## 交付行为

- 查询只读取已发布知识与对应依据快照；原件变化不撤下旧知识。独立维护准备候选内容和匹配向量后短事务发布，保留 expected 并发核查、明确退役及已知错误的排除。
- 宿主使用任务独有 control 与可取消 worker 管理自动维护，业务结束即停止接新批；未发布工作留下，积压较多只建议用户另开手动维护。订阅 agent 继续负责阅读、分块和建图。
- CPU/CUDA 自动选择使用相同模型、前处理和 FP16，向量语义身份保持，跨设备复用；新项目默认 vector，可选 hybrid；0.7.1 取消纯 text 配置与 CLI 路径。旧 text 项目先复用或补齐兼容向量再切换，编号和文件名精确查找保留为 hybrid --literal。brief/search 报告已发布范围的兼容向量覆盖。
- 修正 prepare 目录输入、HTTP 413 信息、空 PID 回收误确认、负时间归零和英文猜超时；Condor 维护匹配与准入，客户端保留请求合同和单次 token 提交恢复。
- 轻客户端 Python 声明改为 >=3.13；模型依赖分别提供 CPU/CUDA extra。用户操作围绕能力条件、步骤、成功输出和失败动作，管理员预算与研发验证各归其位。

详细合同、实际条件与余项由[记忆](memory-result.md)、[作业](jobs-result.md)、[embedding/Python](embedding-result.md)、[文档](docs-result.md)和[普通安装](installation-result.md)结果各自维护。

## 实际检查

源码整合回归 246 项通过、4 项因未指定共享设施跳过；随后相关真实共享向量与恢复分别 3 项、1 项通过。0.7.0 普通 wheel 在源码目录外、完整 CPU extra 的 Python 3.14.10 环境中全套 **255 passed，无跳过**，包含共享模型及原生恢复。新增作业异常回归也由所属分支完成源码检查。

实际宿主探针在候选编码阻塞时执行 stop，约 226 ms 返回；取消运行中的 worker 后再释放编码，旧发布内容仍在，worker 进程已退出。真实 Condor 作业完成 CPU 输出、排队/执行期限和取消并回收。实际 CPU-only 图文服务完成默认语义找回、图片回源、CPU/CUDA 双向索引复用、搬迁与原件更新发布。上述结论分别限于原证所列设备、模型和输入。

最初整合脚本的临时目录父级缺失，以及薄测试环境缺少可选模型依赖，分别修正运行入口和采用完整依赖环境后重验；这两项属于验收准备问题，没有为其修改产品。没有运行新 skill 的行为、触发或收益测试。

0.7.0 基线 wheel：`experiments/20261106-basepack/dist/rectification-0.7.0/basepack-0.7.0-py3-none-any.whl`，SHA256 `742dad25435ffa061f2a4bff30a7abb9353ac6be227d7078fd804475c6dc8176`。源码/普通安装 JUnit、构建日志和宿主停止探针选留于 `artifacts/runs/20261110-rectification/integration/`，设备与作业原证见各分支结果。uv 锁离线检查通过。

## 0.7.1 最终核验

普通wheel在源码外Python3.14.10完整CPU依赖环境中全套**266 passed，无跳过**，含真实共享模型及原生恢复。三个项目先确认1191、272、30条有效发布成员的兼容向量全部复用，再切vector；最终共用客户端普通升级0.7.1、入口刷新、默认查询、hybrid精确命中、旧text及vector/literal错误、旧快照回源和新shell凭据接续均通过。七表逐记录逐字段不变，既有stale/retired未恢复。

最终wheel：`experiments/20261106-basepack/dist/rectification-0.7.1/basepack-0.7.1-py3-none-any.whl`，SHA256 `ec8d8a4cacf0c60eb518a960c601fa2b0c80e85d707e85ecab901013553f3b08`。Python3.13.17/3.14.10轻客户端的真实向量闭环也已通过，客户端仅安装basepack与psutil、连接既有服务。JUnit与构建原证在`artifacts/runs/20261110-rectification/integration-071/`；安装与新shell原证见[安装结果](installation-result.md)。

## 完成范围

本轮不以正式记忆追新或积压清零为结束条件。项目新增源码、测试和技能已登记本机 source_scope；普通安装后的项目状态、备份与入口刷新见安装结果。临时测试库19141已关闭；正式共享模型与 Condor 策略继续使用原实例。远端推送和 GitHub Release 尚未执行，按独立授权处理。

团队总 token、费用及主上下文分项不可核，记为未知；不从测试数或本轮耗时推算长期收益。
