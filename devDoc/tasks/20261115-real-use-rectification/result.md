# 0.16真实使用整改结果

2026-11-16（北京时间）。用户授权执行整改，并明确本轮仅接入basePack本项目；后续追加GitHub push及Release。P0—P4实现与本项目普通安装已完成，P5完成有界R1验证，P6外部项目不在本轮范围。发布状态沿[进度](progress.md)更新。

## 实际交付

| 批次 | 已完成行为与验收边界 |
| --- | --- |
| P0 | 管理员示例从同一endpoint生成含端口的Origin；隔离服务两次真实WebSocket发布成功。整源snapshot在同一事务中按实际JSON wire字节数分消息追加，每条不超过2112 KiB；保留原表、完整正文、hash、来源版本及回滚。freeze缺字段返回稿件／数组位置，无默认填值 |
| P1／M2 | `memory maintain --skip-codex-collection`只跳新聊天采集，回执标记not_requested；既有聊天来源、历史快照及依赖保留。自有语义派工前失败确认无发布后stop/release，默认collector仍抛原错，未明发布保留owner。候选身份集合固定，current_revision为发现观察，每批prepare当前版本并报告实际接受版本；优先组由宿主判断 |
| P2／C1 | agent-team及三个维护角色改为作者负责有限相关来源组、固定稿引用、同稿MESSAGE／自动FINAL一次完成、自有分支观察和有界事件等待。实际两组各处理两源，原作者修稿后发布；程序继续复用E，未增加逐稿语义审计、抢任务队列或去重数据库 |
| P3／C2 | `memory stage`固定handoff、精确completed／remaining和引用hash，owner.json.stage以旧指针作CAS。沿同receipt／owner／control返回带run前缀的新身份及SHA派工入口；宿主真实结束旧组、fresh spawn新协调者／reader，最终父stop和取消生效 |
| P4／S2 | `[memory].private_scope`默认为空，可按原位文件／目录或`.`声明额外私有；根private始终私有，分类不扩大发现或控制Git发行。freeze固定规则，分类／规则进入新source_version，编码前及提交前核规则；历史依据不重标，未变输入向量复用 |
| P5／R1 | 真实Condor作业14469.0退出0；2 CPU、128 MiB、16 MiB，核实际slot账户、父进程链、两个原生hash线程、slot创建到宿主ysPan读回的owner变化，以及digest／job／submission／seed绑定。worker与宿主owner预算分开；既有jobs代码无需修改 |
| 本项目接入 | 最终0.16.0 wheel普通安装至原稳定客户端，刷新memory托管入口；五个独立skill经原有联接使用，当前宿主目录显示对应项目作用域。外部项目客户端、数据库、权限和业务文件未修改 |

## 实际检查与发现的问题

源码全套首轮为 **694 passed、3 failed、1 skipped**（557.23s）。失败分别为受限沙箱内的凭据ACL断言、一次回环连接超时及链接验证器只识别二级标题；已将验证器修为识别全部Markdown标题层级。前三项与原跳过的Condor policy在正常用户上下文定点复核 **5 passed**（3.22s），未修改产品权限／连接逻辑来迁就环境。最终新增缺字段定位后，对record IDs、大源、身份及publish的受影响集运行 **62 passed**（117.03s），含三条新回归。以上是实际分次结果，不宣称一次全套全绿；分支检查与原错留原证，不相加成另一个总数。

大源使用3,901,650／8,441,182／8,943,755字节的合成原文，覆盖CRLF、中文、非BMP、引号、反斜线与制表符；完整回读与hash相同。同版本再接受不累加，追加失败原子回滚；最大样例原生export/import后正文、版本和receipt一致。没有读取或重新发布外部三个业务大源。私有范围覆盖分类不扩发现、混合／端点依据、仅分类变更的新版本、历史回读、freeze后规则变化及向量复用。

实际宿主两阶段使用普通安装的0.16.0、两个Terra/ultra协调者和两个Luna/max reader，均`fork_turns=none`；固定manual5布局每阶段只实际启协调者＋一个reader。run为`1389b6c4a0b142b08ba3fd970887f028`；原receipt字节／hash不变，两组发布共4来源、8成员和1关系。四个接受chunk的精确版本回读与原件正文（含CRLF）一致，第二阶段hybrid literal查询返回相应两源。阶段间旧组实际结束后，按新身份`bp_mem_1389b6c4_s1_coord_0`接续；末段父stop后中断等待中的协调者，发布为空才release，最终owner=null。此样例证明实际派工／发布／接续／收尾，不是以计数代替功能验收。

宿主验收保留并修复了原稿缺edge.id、未创建自有work目录、接续prompt路径笔误和宿主read_text换行归一比较错误。缺字段未进入apply，原作者另存稿／hash后成功；root随后在既有freeze边界增加定位。宿主用wheel SHA为`9b607e4293e5ecc9daec6e0b2894e8d803c47b49dcb77e3fdc11c2a517149bc2`；最终wheel仅draft.py多此错误定位分支，stage／CLI／owner／模板字节相同。最终普通安装的三个非法稿用例均返回准确位置，60个包内文件与最终源码／wheel一致。

Condor首次宿主Get-Acl模块自动加载失败且命令返回0、owner为空，原记录明确未验收；对同一回传工件改用Windows原生只读安全API核owner并重算hash通过，未重投或修改权限。五个已知作业进程及scratch均已清理。此探针不代验AEDT／GUI、许可证、AppContainer、其它账户隔离或科研真值边界。

## 安装、数据与恢复

最终wheel为`experiments/20261106-basepack/dist/basepack-0.16.0-py3-none-any.whl`，SHA256为`ee3bd3a30cdbb26992cb813206b3d0fc424f2de69822522fa10eadbd2cf68eb8`。客户端从`D:/AgentTools/envs/basepack-client-0.10/Lib/site-packages/`导入；原目录名沿用。依赖未变，锁文件仅本包版本变化；共享embedding服务保持0.15.0，不重启或改模型／identity。

升级前确认owner为空并保留一次原生export（430,996,586 bytes）、旧0.15 wheel、原配置／入口及凭据，位置为`.basepack/memory/backups/rectification-0.16.0-20261116/`。这只是客户端升级恢复覆盖集，完整项目恢复仍依赖原件、assets和既有恢复链，不重复复制大导出到artifacts或Git。

升级及memory init后，UUID `464948e9-d41e-420f-966b-ebaa602fd9bc`、配置hash、三条mandatory精确read结果hash及11表计数完全一致：meta 1211、source 1514、source_version 2034、member 7781、node 144、semantic 249、change 15444、knowledge_version 7996、feedback 8、access_state 104、delivery 18。AGENTS及instructions托管块外字节先核完全相同；随后仅显式更新instructions块外已知客户端／服务版本句子。

本轮未将新文档自动重新总结进正式知识库，也未做全库语义审计。开始时默认自动维护在语义派工前遇已知Codex SQLite14访问错误，自有run `a533dfd8048e400bb16ad9fa8c07e00a`已stop、核发布为空并release。M2实际文件维护由隔离宿主样例验证，不能称聊天已刷新或SQLite权限根因已修复。全部自有隔离服务退出、临时凭据删除，正式数据库保持运行，最终owner=null。

## 有限兼容、余项与原证

0.15固定稿仅在两个隐私规则字段同时缺失且当前额外私有范围为空时，沿已知根private合同保留原batch ID／UUID接续；只缺一个字段为错误，新增范围明确冲突。已提交数据库receipt恢复先于规则检查。S2只提供分类能力，不自动迁移既有镜像／历史路径。

外部镜像迁移、R2项目薄入口、AEDT／GUI／许可证实际执行条件及科研项目权限问题均在本轮外，后续按具体项目选择。Terra减少60–80%、Luna持平至增加10%仍为规划情景；此次短样例没有同材料基线，未实测用量节省，长期质量、遗漏和全队用量沿真实使用反馈维护。

选留原证在`artifacts/runs/20261116-real-use-rectification/`：manifest固定96份文件、约0.55MB，含宿主handoff／原稿／发布回执／精确回读、Condor原证、测试原错与定点复核、两个wheel及安装前后不变量。原JSON绝对执行路径按目录README的前缀映射复核；分支报告的待root验收是当时状态，最终口径以本文为准。临时venv、缓存、大源副本和密码不选留，均不进入公开发行包。
