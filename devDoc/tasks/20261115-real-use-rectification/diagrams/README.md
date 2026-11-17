# 记忆系统修改前后逻辑图

2026-11-17。两图比较完整系统；它们是逻辑示意，不替代接口与数值合同。

| 版本 | 范围 | 可编辑源 | 预览 | 矢量采用件 |
| --- | --- | --- | --- | --- |
| 修改前 | 已部署客户端 0.16；共享 embedding 服务 0.15 | [SVG](memory-system-before.svg) | [PNG](memory-system-before.png) | [PDF](memory-system-before.pdf) |
| 修改后 | 未来目标，尚未实现或部署 | [SVG](memory-system-after.svg) | [PNG](memory-system-after.png) | [PDF](memory-system-after.pdf) |

当前实现依据[系统图](../../../system/diagrams.md)及 0.16 的维护、freeze/apply、访问和 rank 源码。目标依据[目标架构](../target-architecture.md)与本轮最新决定：独立采集、有限语义工作组、程序编译及唯一发布；真实共交付训练标准 KL-NMF，Gaussian 连续降权，权重可低但材料保持可检索。数值投影使用 H 累计与未知证据区间；本图不包含退出、删除或 GC。

## 同源与修改范围

[生成器](generate_memory_system.py)维护唯一的公共节点和连线数据，再叠加两个版本的变化槽位。15 个不变节点、25 条不变连线、worker 分组和 4 个泳道逐个比较完整 XML，覆盖语义 ID、坐标、框尺寸、文字、角色颜色与连线路径。8 个变化节点使用同一坐标、尺寸和角色，角标 Δ 标出修改处；目标新增三条虚线，分别保留原始锚点、以当前独立锚点发现行为候选、逐事件更新 Gaussian 访问投影。标题与说明按当前／目标状态变化。

维护的唯一发布者、原子接受、实际阶段接续、stop 与 release 都在两图共同部分；freeze 的既有程序职责在目标编译器中继续保留。目标的批量 KL-NMF 与逐事件访问投影分开表达。内容 embedding 与纯行为 φ 分属两个空间；rank 保持排序、去重与预算，LLM 只做同次综合评分。

## 重建与检查

从项目根执行；SVG 生成和同源检查仅依赖 Python 标准库，PNG/PDF 导出另需 Inkscape：

```powershell
python devDoc/tasks/20261115-real-use-rectification/diagrams/generate_memory_system.py `
  --render --inkscape '<本机 Inkscape 可执行文件>' `
  --qa-report artifacts/runs/20261117-gaussian-diagrams/system/same-layout-final.json
```

交付 PNG 为 2040 × 1880，框内最多三行；SVG 保留真实文字和语义 ID。PDF 由同一 SVG 直接导出，单页 1530 × 1410 pt。

实际检查包括多轮独立图渲染与 `view_image` 视觉检查：调整 worker 标题与数据线避让；补齐共同阶段接续、拆开批量学习与逐事件投影；将维护控制接到准备阶段，使独立采集不依赖维护 owner，并把回源核验归到 LLM；最后补明当前锚点到行为候选的依赖。最终检查两张 PNG，以及 Poppler 从最终 PDF 重新渲染的两张预览，未见漏字、裁切、穿框或文字拥挤；本机 Microsoft YaHei 字宽检查无框内溢出。

首轮、第二轮预览、最终同源报告与 PDF 栅格预览保存在忽略目录 `artifacts/runs/20261117-gaussian-diagrams/system/`。这些检查仅证明图稿和导出的一致性、可读性，不表示未来系统已实现、业务效果已验收，也未检查论文或其他目标正文的插入版面。
