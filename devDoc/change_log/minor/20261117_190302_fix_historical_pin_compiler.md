# 修复真实维护发现的历史版本闭包误判

0.17.0首100来源试用中，两个固定prepare里的fresh记录保留合法历史basis/parent版本，compiler却要求pin等于当前版本，导致freeze误拒，并曾迫使作者额外重写10个section。主任务在46/95个语义候选已接受时暂停，确认全部团队结束和发布终态后释放owner，保留49个未完候选与固定工件。

0.17.1的prepare按精确(ID,knowledge_revision)物化已有依赖版本，compiler沿实际历史pin编译，保留当前版本的事务冲突保护和精确版本private传播。缺失版本明确报错，不以current替代历史，不要求作者为通过编译重绑语义。schema、交付事实及行为模型合同不变。

独立内存库最终publish/proposals 22项通过；此前维护组合70项通过。独立实样复测用原始失败稿及未变的4个原件，旧0.17.0复现原错误；只更换prepare路径/hash后新源码freeze成功，原46成员、10section、1节点与3边的语义不改。该组prepare物化330个历史版本，约2.3MB、15.498秒，freeze约0.015秒；不作为性能收益承诺。普通0.17.1安装后65文件与wheel逐字节一致、依赖检查及同稿freeze通过，尚待新小批实用；实际部署、接受截点与余项见[执行记录](../../tasks/20261115-real-use-rectification/execution.md#首批真实维护与修复循环)。
