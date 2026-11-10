# 真实 PPT 项目修复与实测结果

2026 年 11 月 10 日。执行 [修改与维护计划](real-project-maintenance-plan.md)，M1–M4 已完成：特殊 ID 修复、接入与诊断、0.6.1 普通安装，以及原 PPT 项目的真实增量、关系更正、删证、恢复和九次独立上下文对照均通过验收。本小样本没有证明记忆组优于直接文件或取得全周期费用净收益。

## 修复与普通安装

| 项目 | 实际结果 |
| --- | --- |
| 根因与修复 | 从旧提交源码在真实隔离库重现 `Member changed while embedding`；共享 `_record` 恢复 canonical ID 的原 key、转义与整数类型，SQL 与 Python 的依赖身份统一，真实变化仍拒绝写入。 |
| 输入错误 | 文字成员缺起止行报成员、批次位置与字段；缺失 read ID 明确失败。失败批次未留部分记录，依赖链立即停止。 |
| 接入 | 端口/目录/UUID 在 memory init 前明确；配置同值启动、日志/cwd/凭据/Python 与跨调用存续可核。可执行三层批次与随包示例通过。 |
| 源码 | 提交 `488e298`；全套 157 passed、0 skipped，57.37 s，四项实际向量检查均执行。新增专项 37 passed。 |
| 普通 wheel | `experiments/20261106-basepack/dist/memory-0.6.1/basepack-0.6.1-py3-none-any.whl`，54,761 B；SHA256 `2a1bc7e014e2a89697ced0970352cf9f724f287ebf3baa728a4edb4b4403efd2`。 |
| 源码外验包 | 普通 venv 安装，全套 157 passed、0 skipped，56.49 s；33 个包文件与源码/wheel/安装逐字节相同，非 editable。 |
| 两项目与恢复 | 独立目录/端口/UUID、跨宿主调用 ready/init/brief、canonical 特殊 ID 编码/直接向量检索/复用、错项目拒绝、默认文字与向量示例通过。非空更正与退役历史原生恢复后六张领域表完全相等，read/图/向量通过；重建 5 项向量未改审计。 |
| 稳定安装 | `D:/AgentTools/envs/basepack-client/Scripts/python.exe` 已普通安装 0.6.1；33 个文件与 wheel 相同。源项目七表全记录与升级前逐字段相同，brief/search/read 通过。 |

共享 0.5.0 embedding 实现与 Qwen3-VL 语义身份继续复用。升级前保留 0.6.0 wheel 和对应项目原生恢复集合；源项目备份位于 `.basepack/backups/20261110-before-061/`。所有自建隔离数据库树及端口均已清理，正式项目库和共享模型服务留供后续使用。

### 环境与失败口径

源码首轮 8 项失败均为缺少锁定 sentence-transformers 发行元数据；在测试环境安装 760 KB 的 6.2.0 包（无依赖扩装）后完整通过。普通验包 venv 显式复用既有系统 pytest/psutil/torch/Pillow，basepack 和该测试包普通安装在 venv 内；稳定客户端保持轻量，不安装模型依赖。稳定环境没有 pip，首次安装在改动前停止，改用已有安装工具的 `pip --python` 指定目标成功。

受限宿主下，Hidden 启动和显式 breakaway 都在调用后被回收；普通用户执行同一原生启动脚本后，后续独立调用和知识操作通过。M4 续接时共享 SCM 服务已停止，普通中完整性令牌启动它被 Windows 拒绝（错误5）；用户以管理员启动原服务，健康与身份核对后仅续编码，没有重放 apply。两个正式库端口不可用时，沿各自既有 serve.ps1 重新打开原 store，未初始化空库。不将短期跨调用测试外推为宿主重连后的长期驻留保证，也未增加产品进程管理器。

取证脚本的 CRLF、恢复草稿缺 sources、PowerShell 退出码和 wheel 元数据换行假设均按实际错误修正，不计为产品缺陷。原协调者停在 pending_init 后，主 agent 接管剩余流程并复用已保存的九份答稿。

## 原 PPT 项目实测

原项目为 `D:/project/trifles/20261109 ppt memsys`，升级前 Git 为干净的 `main fd1ed3f`。冻结 7 份登记原件及其 hash、配置/mandatory/scope、原生 export 和只读记录清单：29 个当前成员、4 个退役成员、2 条条件关系、39 条审计；3 项覆盖缺口继续保留。

本轮使用原项目快照恢复出的独立物理目录和端口进行对照、修改、删证与恢复；正式 PPT Page、演讲备注和研究三报告保持原截点，反馈与进度在收尾维护。正式库升级后先只读核验，原生 export 与安装前逐字相同。每题使用独立新上下文 worker，未新建 UI chat；按同一11月9日冻结材料回答，评分依据与题目分离。

| 方法 | T1交接定位 | T2跨材料复盘 | T3未点名的备注约束 | 合计/6 | 顶层工具调用 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 直接文件 | 1 | 1 | 2 | 4 | 15 |
| mandatory短提示加文件 | 1 | 1 | 1 | 3 | 18 |
| 完整记忆 | 1 | 1 | 2 | 4 | 26 |

九份证据原文范围逐条一致；未见组别映射的订阅 agent 按预先0/1/2尺度评分。三组在T3都实际排除试用问题并区分源码/安装对象，短提示组另漏“隐藏备份”属性。T1/T2共同遗漏操作限制或因果反证，说明取回证据不等于最终短稿已交代条件。完整记忆本轮没有质量优势，不从一分差异外推普遍效果。

多数worker缺完整起止时钟，全组完整墙时不可比较。T2显式UTC工具窗口为直接129.637 s、短提示246.602 s、记忆600.530 s；记忆原回执误按本地时区多计八小时，统一UTC更正派生量并保留原件。工具调用包含记录与返工，不换算费用；精确模型、tokens、费用未知。分支总观察区间含协调等待、服务恢复和录入，不当作正常业务或模型总耗时。

- 正常增量同读更新文件摘要与对应原文块，编码2项；删去5个证据成员后复用22个当前向量，3个未变兄弟的内容/表示/向量一致。旧整句不再作为当前结果，原4个退役成员保持。
- 更正真实历史失败关系的条件并保留previous；该边确实引用reference-analysis日志。删除支持材料后，剩余Codex文字仍有效，但不能维持已失去起点的跨材料关系，故显式退役；另一版本印证关系逐字段保持，历史可查。
- 另一物理目录/18111原生恢复七表全记录相等：24当前、9退役、54审计；重编码24条后非向量知识与审计不变，read/图/向量通过，pending=0，保留2项覆盖缺口。
- 正式项目仅维护反馈/进度两源：接收9成员，编码8、复用22，30当前＋4退役；7来源scope、2项mandatory、2条原关系及3项研究缺口保持，changes/pending/vector_pending均为0。新报告由已登记材料指向。WinPS5.1包装器实际回读`m³`通过，缺失ID非零退出且带目标。

收尾曾将任务标签误放root_chat，核对真实chat后以原生更正保留previous并补正10条上下文，知识与向量不变；隔离历史快照的标签映射另存证。PPT项目维护文档提交为`2e82e93`，最终原生备份在该项目`.basepack/backups/20261110-075004/`；[项目结果](<D:/project/trifles/20261109 ppt memsys/devDoc/basepack-maintenance-20261110.md>)保留入口。

### 满分可达性补测

用户随后要求尝试生成满分答案。三位全新上下文的订阅agent各写一题，写作前可读原题、原评分表和同一批11月9日冻结材料；每题提交一份答稿，无外部评分后的改写。两位独立评分者只收到原题、匿名答稿、原评分表与冻结材料，未见作者自查、旧成绩或彼此结论，均给出2、2、2，即各6/6。

T1/T2/T3正文分别174/151/259个Unicode字符，包含空格、标点和正文引用标记，排除标题、另附依据及作者说明，满足原≤180/120–180/180–260限制。原题、评分表及7份材料共9份输入逐字一致。此前遗漏的authorBatch限制、独立事实/视觉核查、因果反证及隐藏备份属性均进入相应答稿。[完整答案与评分](../../../artifacts/runs/20261110-perfect-score/report.md)保留原文、引用、作者取证和独立评语。

这证明给出评分表和材料时，原要求在字数内可以完成；不检验未经提示的前提发现、三种检索方式的稳定成功率或费用收益。原盲测4/6、3/6、4/6及九份答稿保持，补测不并入原组别。对原试验仍只能确认保存的证据包包含漏项，未严格记录各信息进入写作上下文的时间。补测版本数字仍指冻结截点，精确模型/tokens/费用、主agent上下文用量和完整团队墙时未知。

## 原证与边界

- 修复复现与定向回归：`artifacts/runs/20261110-memory-061/code/`。
- 源码、普通安装、两项目及恢复：[验包总回执](../../../artifacts/runs/20261110-memory-061/validation/result.json)，[包绑定](../../../artifacts/runs/20261110-memory-061/validation/package-binding.json)，[wheel 清单](../../../artifacts/runs/20261110-memory-061/wheel-manifest.json)，[稳定安装](../../../artifacts/runs/20261110-memory-061/stable-install.json)。命令、完整日志、JUnit、输入与临时服务清理相邻保存。
- PPT 实测：[总回执](../../../artifacts/runs/20261110-real-project-trial/result.json)、[匿名评分](../../../artifacts/runs/20261110-real-project-trial/scoring/grades.json)、[正常增量](../../../artifacts/runs/20261110-real-project-trial/maintenance/normal-result.json)、[删证](../../../artifacts/runs/20261110-real-project-trial/maintenance/graph-result.json)、[恢复](../../../artifacts/runs/20261110-real-project-trial/restore-backup/restore-result.json)及[正式收尾](../../../artifacts/runs/20261110-real-project-trial/formal-maintenance/result.json)。输入、脚本、失败与清理相邻选留，不含明文凭据。

历史 P0–P5/R9 和本轮证据分开。以上功能通过不代表记忆系统已取得普遍质量或全周期费用收益；实际模型/用量/费用仅按宿主可取得值记录。未进行远端发布或无关 Condor 大矩阵复测。
