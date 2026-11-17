# 有限任务池与两段Terra维护

0.18.0源码以单一有限任务池替换逐组Terra续派：协调者规划并实际启动固定Luna池后结束turn；原父确认初始化结束再seal/go，Luna自主领取、提交固定引用并退队，最后正常者实际followup同一协调者收尾发布。保留原owner、stop、固定版本和唯一publisher；未知通知/提交不重试抢回。旧合同执行入口明确拒绝，旧轮须正确关闭后新建。数据库schema3及Gaussian行为规则不变。

状态机、CLI、提示词、阶段交接和使用文档同步；新修改前后图保留共同节点/连线一致，已查看PNG及PDF栅格。定向核心、提示词及跨模块回归已通过；独立测试库上的全memory回归649通过、6跳过，1483.62秒。普通安装、全新宿主句柄闭环和真实剩余来源小批仍待验收，实际结果沿[执行记录](../../tasks/20261115-real-use-rectification/execution.md)更新，不以静态描述代替宿主验收，也不承诺净token节省比例。

完整授权与生命周期合同见[维护计划](../../tasks/20261115-real-use-rectification/maintenance-waves.md)，原Terra用量原因和各次修正证据见[调查](../../tasks/20261115-real-use-rectification/research/terra-usage-20261117.md)。
