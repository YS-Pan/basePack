# 新行为架构迁移与推广

2026-11-17。正式停写备份、数据迁移、首批真实维护和18080入口推广已完成；全项目授权维护及其最终恢复点仍待完成。预备演练导出发生在生产库仍可写期间，正式迁移另用停写后的新鲜导出。

## 数据合同

物理迁移保留全部记录、UUID、内容向量和精确版本；不猜历史拆合、不重读全部内容。旧delivery保留原`event`与`items`，原`context`另存`legacy_context`，标`legacy=true`、`j=null`、`context=null`；旧非空event仅表达其已知先后，旧空事件无可证明的严格次序。旧`access_state`和`meta:access`原样保留作历史，不供新模型解释为新权重；新`meta:delivery.j=0`。旧知识版本`j_enter=null`，`observed_j=0`和`age_origin=legacy_cutover`只表示新规则的观察起点，不能表示真实接受时间或命中。旧实交付可训练共用，缺失锚点的质量为unknown；旧从未命中者真实hits仍为0，从此观察起点随新事件变冷。真实旧年龄无法恢复。

## 实际预备演练

生产库只读的预备导出为459,907,312字节，隔离源库原生重导出SHA-256相同。分别恢复到本机独立端口18171、18172及不同物理store。数据桥转换后全部旧表逐记录逐字段相等，除合同中的明确新增字段和新增新游标外无差异：meta 1419、source 1585、source_version 2165、member 8192、node 166、semantic 262、change 16690、knowledge_version 9264、access_state 134、delivery 23、feedback 8。七条旧delivery含非空旧context，已按合同保留。在独立配置与目录上安装当时源码schema并训练，23次旧非空交付重放为C=23、22个共用篮进入训练；brief含3条mandatory，literal search、文本/图片read、history与neighbors均可读取，新空交付J=1、重试不增、非空交付J=2。旧未命中版本hits保持0，一次新非空交付后其权重区间上界由0.999875降至0.999750，观察起点标为legacy_cutover。首次图片回读因隔离目录缺assets失败，复制原assets后成功；恢复集合必须带上这些文件。以上是预备快照与当时源码的隔离检查，不代替最终集成版本的验收。演练和报告在忽略的`tmp/20261117-implementation/migration/`；原生备份与上下文可能含私有资料，不公开。

## 正式恢复和切换门

1. 等待新版本集成门通过。停止自有维护和所有写入、确认无在途发布；保存旧客户端wheel及执行环境、项目配置和凭据、launcher、托管入口、原生新鲜导出、必要原件/图片/assets及回执；切换后恢复集合还须包含`memory_dir/behavior/`模型工件及对应数据库投影。保留整个旧物理库。恢复集合和哈希清单放项目既有`.basepack/memory/backups/`，按私有资料管理。
2. 源库停写并保持只读，保存新鲜原生export；将其导入不同的隔离物理目标，再原生重导出目标并对SHA-256与输入逐字节比较。端点必须与配置中的生产端点不同，源、目标端点也不同。
3. 使用保存的旧0.16客户端运行一次性数据桥（下例为演练端口；配置及数据路径按实际替换）：

```powershell
$oldPython = '<保留的0.16客户端Python绝对路径>'
$bridge = 'experiments/20261106-basepack/src/basepack/memory/migration.py'
& $oldPython -X utf8 $bridge migrate '.basepack/config.toml' 'http://127.0.0.1:18171' 'http://127.0.0.1:18172'
if ($LASTEXITCODE -ne 0) { throw 'migration failed; leave target closed' }
& $oldPython -X utf8 $bridge finalize '.basepack/config.toml' 'http://127.0.0.1:18171' 'http://127.0.0.1:18172' --report '<new-private-report.json>'
if ($LASTEXITCODE -ne 0) { throw 'handoff failed; inspect target and leave it closed' }
```

finalize先比较数据库定义、各表索引及事件、所有旧记录和明示转换，再于事务内核J=0及旧身份标记并写`memory_schema_version=3`；结果报告记录handoff marker。只读的`verify`动作可供演练单独使用。未知表、旧字段已有新迁移标记、目标游标已存在或端点不隔离时停止。数据桥只适用于本次已核的member identity 2及十一表schema，不是长期兼容接口。
4. 数据对照通过后，在已设置marker的目标安装集成通过的新schema，再用独立配置与独立`memory_dir`显式训练模型并重放投影；不能让隔离演练向生产模型目录写入工件或锁。检查旧缺锚点和旧入场未知提示、真实旧命中、从切换起降权及低权重仍可检索。分别验证brief、search、原文及图片read、history、neighbors、空和非空delivery、重复请求及重训切换。实际结果与截点记录后，才同步切换客户端与本项目服务入口并恢复写入。
5. 失败或检查未完成时保持新目标关闭，不改旧库；按保留的旧wheel、旧配置/凭据、launcher和原库恢复旧入口。新库开始接收写入后回退须先导出其新事实并妥善保留，再决定如何处置，不能把旧备份当成包含新事实的恢复点。

## 正式停写与隔离接入

正式停写前核唯一18080进程的工作目录、参数与`store-0.13`绝对路径，owner为null。停止进程后，首个端口检查仍瞬间显示监听而按保护中止；后续独立核实原PID退出、18080无监听、旧库锁已释放，再把原库以18174启动。保留首次错误与回执；未重复停止。该阶段18080保持关闭，旧store不删除。

冻结源实际event=24、delivery=24、feedback=9。恢复集合位于本机`.basepack/memory/backups/architecture-0.17.0-20261117/`：原生导出、旧0.16 wheel、配置和凭据、入口、assets、受管聊天、维护材料及回执共2702文件、951,738,769字节，有逐文件SHA-256清单。源导出SHA-256为`67d138a62c3897d044fb3bff34156ff5f477acda594ee6a6771e39c668ef45aa`。新`store-0.17`在18176原生导入并重导出，字节哈希与源完全一致；旧客户端执行数据桥与finalize，十一表、全部记录及原有schema/索引/事件逐项等价，保留139条旧访问状态、24交付及9反馈，并显式写schema marker 3。原生数据、回执和清单均按私有边界保管。

当时稳定客户端普通安装0.17.0及behavior依赖，模型训练使用NumPy 2.5.5、SciPy 1.18.1、scikit-learn 1.9.1。当时隔离staging配置为本机`.basepack/staging-0.17.toml`，绑定18176并沿用本项目memory目录及assets；该阶段未刷新根托管入口。新模型编译J=0、C=24、23个共用篮，139个旧精确版本实际命中数与重放投影一致。真实共享embedding查询返回5项，8005/8005旧向量兼容；brief保留3条mandatory，文本和图片read、history和neighbors只读通过。没有向正式staging写合成交付。详见私有`handoff-verified.json`及`staging-read-verification.json`。

用户要求先以约100候选真实维护测试，再按发现的问题修复与小批复验。该阶段在18176执行，记录实际处置、发布回执、J及模型/投影游标，不逐批全库导出。旧库和旧wheel继续保留；全部维护完成后保留最终恢复点。

## 真实维护后推广

首轮测试发现历史pin编译误判，修复后在0.17.1复验；第二轮54个来源范围均已接受，29个publication均达终态，未处理范围外来源。主任务停止并释放owner后，最终0.17.2 wheel经普通安装，SHA-256为`60af6c2504d85132c4c90b66f651841a532087c015482bdb6a7529362f964c47`。此范围通过不代表全项目维护已完成；业务处置细节和后续范围以任务进度为准。

推广前按PID、工作目录和参数确认新`store-0.17`在18176、旧`store-0.13`在18174，owner=null且端口无已建立连接；停止两个已核进程，等端口关闭并核两个锁释放。保留旧物理库，更新launcher并以隐藏进程在18080启动同一新库。启动和ready检查分开：launcher PID 48740，数据库 PID 115116；独立检查证实后者绑定18080并打开`store-0.17`。

切换前、启动后、普通`memory init`后及原staging配置重指18080后，精确delivery集合摘要、知识版本数10607、来源数1626、J=compiled J=2、C=26、模型`3c69a1307fa077bfb0860ff26277bb78daec95c92afa2aa699fc673d3e64791f`均一致。26次delivery包括24次旧事实及两次推广前实际新交付；未补造测试交付或重训。保留中的`.basepack/staging-0.17.toml`只改唯一endpoint字节，其余字节不变；原文件备份于任务临时目录。根AGENTS托管块外字节未变，普通init刷新受管入口，项目instructions块外仅修正客户端版本、当前store和迁移前恢复集合位置；runtime记录实际launcher PID。

独立只读验收：owner=null，brief含3条mandatory，共享embedding查询返回5项，8250/8250内容向量兼容；文本和图片read、历史回读及实际图边neighbors通过。旧18174和临时18176端口关闭；旧库保留但不运行，共享embedding设施未变。临时检查记录位于`tmp/20261117-implementation/migration/`。

最终完整恢复点待全部授权维护完成后制作一次，须包括届时原生数据库、匹配wheel及配置/凭据、launcher、原件/图片/assets、受管快照和回执、对应behavior模型工件，以及独立private Git和需保留的忽略原件。`private/README.md`所列同盘bundle在推广准备时包含private HEAD；另有13个忽略文件共3,706,415字节，均在private/tmp，可在最终恢复点一并保全。同盘副本不提供设备故障保护。
