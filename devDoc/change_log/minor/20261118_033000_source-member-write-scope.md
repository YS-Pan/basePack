# 明确来源成员与共享图的写范围

真实e459维护任务把空write_targets误解为成员只读。wave-task先按paths授权，后又要求只修改stated write targets，存在措辞矛盾。

0.18.4明确paths授权来源及其成员的必要修改，write_targets协调共享节点/关系；read_paths仍只读，新增写来源留后波。程序已有的路径边界及发布顺序保持。136项prompt检查通过，后端与schema不变，不为指引修订重复整轮native测试；等当前0.18.3波收口后安装，再以实际修复任务验收。
