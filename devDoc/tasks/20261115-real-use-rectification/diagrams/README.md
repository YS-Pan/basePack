# 记忆系统修改前后逻辑图

2026-11-18 更新当前组织图状态。两组图分别比较完整系统；它们是逻辑示意，不替代接口与数值合同。

## 维护组织变更：0.17.4 → 0.18 系列

| 版本 | 范围 | 可编辑源 | 预览 | 矢量采用件 |
| --- | --- | --- | --- | --- |
| 修改前 | 0.17.4 历史基线；Terra 按来源组接续 | [SVG](memory-system-wave-before.svg) | [PNG](memory-system-wave-before.png) | [PDF](memory-system-wave-before.pdf) |
| 修改后 | 0.18 系列；有限任务池与 Terra 两 turn，安装状态见部署合同 | [SVG](memory-system-wave-after.svg) | [PNG](memory-system-wave-after.png) | [PDF](memory-system-wave-after.pdf) |

本图按 0.18 系列描述维护组织，实际安装版本以[部署合同](../../../system/deployment.md)为唯一源，后续不因 patch 号单独改图。程序、纯文件宿主闭环与首个真实发布已验；source-level `unavailable_gaps` 语义持久化修复的真实小批验收、全项目实际接受范围与余项沿[任务进度](../progress.md)核实。该字段沿已有覆盖/缺口交付，不改变本图整体流程。

新图依据[有限任务池合同](../maintenance-waves.md)，保留下面的历史图。内容 embedding、KL-NMF、Gaussian H 投影、固定独立锚点、单次 LLM 综合评分与 rank、真实 delivery、原证/知识/assets、owner/stop/release 都在两张新图的共同部分；低权重不引入退出、删除或 GC。主 agent 用蓝色，Terra 和 Luna 等子 agent 用橙色，程序执行用绿色，来源与存储用灰色；颜色表示角色，不表示模型。

[新生成器](generate_maintenance_wave.py)复用历史图的图元与导出设施。22 个共同节点、29 条共同连线、4 个泳道、组织外框、检索 worker、图例和页脚逐项比较完整 XML，覆盖坐标、框、文字、颜色与路径；移除版本标题及组织变化组后，剩余整张 SVG 再作完整 XML 比较。10 个变化槽位保持相同位置、尺寸与角色颜色。变化集中在维护组织区：预登记与启动屏障、Luna 自领/提交循环、无活原子退队及唯一通知、同一 Terra 第二 turn 发布、原父观察两方终态后机械 close。旁注说明通知非事务、恢复名额和异常/stop/晚回调边界。

从项目根生成新图及同源报告：

```powershell
python devDoc/tasks/20261115-real-use-rectification/diagrams/generate_maintenance_wave.py `
  --render --inkscape '<本机 Inkscape 可执行文件>' `
  --qa-report artifacts/runs/20261118-wave-diagrams-series/same-layout-final.json
```

新 PNG 为 2040 × 2670；PDF 由同一 SVG 导出，单页 1530 × 2002.5 pt。初稿两轮逐张 `view_image` 检查 PNG，修正提交循环与无活退队分支、反馈线交叉和底注裁切，原证在 `artifacts/runs/20261117-wave-diagrams/`。本次更新系列状态后重新导出并逐张检查两张 PNG，以及 Poppler 栅格化的两张 PDF；同源报告、颜色核对与视觉原证保存在忽略目录 `artifacts/runs/20261118-wave-diagrams-series/`。图稿检查证明图形一致性和可读性，运行证据与完整维护验收分别报告。

## 历史架构：0.16 → 0.17

| 版本 | 范围 | 可编辑源 | 预览 | 矢量采用件 |
| --- | --- | --- | --- | --- |
| 修改前 | 实施前基线：客户端0.16、共享embedding0.15 | [SVG](memory-system-before.svg) | [PNG](memory-system-before.png) | [PDF](memory-system-before.pdf) |
| 修改后 | 制图时的0.17目标合同，其后已实现；接入状态见实施结果 | [SVG](memory-system-after.svg) | [PNG](memory-system-after.png) | [PDF](memory-system-after.pdf) |

修改前基线依据0.16的维护、freeze/apply、访问和rank源码。目标依据[目标架构](../target-architecture.md)：独立采集、有限语义工作组、程序编译及唯一发布；真实共交付训练标准KL-NMF，Gaussian连续降权，权重可低但材料保持可检索。数值投影使用H累计与未知证据区间；本图不包含退出、删除或GC。图形保持制图时的前后对照，当前接入进度见[实施结果](../implementation-result.md)，实际部署见[系统图入口](../../../system/diagrams.md)。本次只更新说明，没有改图形或重新生成视觉验收记录。

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
