"""Generate the current/target memory diagrams from one shared semantic layout.

The optional --render uses a local Inkscape installation. SVG text stays editable.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from html import escape
import json
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
W, H = 2040, 1880
FONT = "Microsoft YaHei, Noto Sans CJK SC, sans-serif"
PALETTE = {
    "main": ("#E4EEFC", "#5179AE"),
    "agent": ("#FFF0D7", "#B67E31"),
    "code": ("#E7F2E7", "#688C6D"),
    "data": ("#F0F2F5", "#8994A4"),
}


def node(id, x, y, lines, role, w=330, h=120):
    return dict(id=id, x=x, y=y, w=w, h=h, lines=lines, role=role)


# Shared objects are never re-created separately for BEFORE and AFTER.
COMMON_NODES = [
    node("memory-brief", 80, 330,
         ["memory brief", "mandatory・概况与缺口", "不按当前问题搜索"], "code"),
    node("business-main", 450, 330,
         ["业务主 agent", "理解任务并开展工作", "按需委托检索 worker"], "main"),
    node("candidate-score", 1190, 330,
         ["一次综合评分", "LLM 回源核验＋访问提示", "形成候选综合分"], "agent"),
    node("rank-budget", 1560, 330,
         ["rank 程序", "排序・去重・字符预算", "按综合分返回实际结果"], "code"),
    node("delivery-events", 820, 570,
         ["真实交付记录", "精确版本集合＋delivery_id", "同库保存；空 / 重复不增钟"], "data"),
    node("project-store", 450, 800,
         ["项目唯一 SurrealDB", "原证・知识版本・语义图・交付事实", "项目知识与状态留在所属项目"], "data", 1060, 115),
    node("shared-embedding", 1560, 800,
         ["共享图文 embedding", "内容向量编码与检索", "机器服务独立托管"], "data", h=115),
    node("source-material", 80, 1060,
         ["项目来源", "文件・private・绑定聊天", "附件与可定位原证"], "data"),
    node("unique-publisher", 1560, 1260,
         ["唯一发布者", "调用 apply 原子接受", "回执：实际版本与缺口"], "agent", h=110),
    node("stage-continuation", 820, 1260,
         ["本组完成后真实接续", "新上下文继续后续来源组", "沿同轮 receipt・owner・control"], "agent", 700, 110),
    node("owner-control", 80, 1490,
         ["唯一 owner ＋ control", "维护所有权与自有句柄", "控制维护团队的生命周期"], "code"),
    node("stop-owned-work", 450, 1490,
         ["业务结束：stop 自有 control", "取消自有协调者及后代", "保留已获准发布的明确终态"], "code", 700),
    node("release-owner", 1190, 1490,
         ["确认发布终态后 release", "未明状态保留 owner 与待处理项", "共享数据库继续运行"], "code", 700),
    node("host-guidance", 80, 1690,
         ["宿主 skills 与订阅 agent", "agent-team・工程判断・资料边界", "语义理解与创作由 agent 完成"], "data", 830),
    node("shared-condor", 1000, 1690,
         ["HTCondor 重任务资源", "容量・准入・作业进程树", "调用者声明实际并行与资源"], "data", 890),
]

CHANGED_SLOTS = {
    "base-search": (820, 330, "code"),
    "delivery-confirm": (450, 570, "code"),
    "behavior-model": (1190, 570, "code"),
    "access-hint": (1560, 570, "code"),
    "source-collection": (450, 1060, "code"),
    "prepare-workset": (820, 1060, "code"),
    "semantic-authors": (1190, 1060, "agent"),
    "compile-proposal": (1560, 1060, "code"),
}

VERSIONS = {
    "before": {
        "title": "修改前 · 当前记忆系统",
        "subtitle": "0.16 actual · 已部署客户端；共享 embedding 服务 0.15",
        "note": "访问偏好由全项目真实交付驱动；没有行为向量、独立锚点或 Gaussian 投影。",
        "lines": {
            "base-search": ["baseSearch 基础检索", "词法・内容向量・语义图", "多轮补检索与原证定位"],
            "delivery-confirm": ["宿主确认实际交付", "精确知识版本", "非空交付：命中版本 hits +1"],
            "behavior-model": ["全局事件与访问投影", "非空 delivery 推进 G", "真实 hits 决定访问强度"],
            "access-hint": ["全局访问提示", "同一 G 影响全项目", "无日历衰减；交综合评分"],
            "source-collection": ["maintain 内采集", "collector 先采新聊天", "明确 skip 可跳过本轮采集"],
            "prepare-workset": ["maintain 准备", "变化发现・固定候选", "prepare 提供读取包"],
            "semantic-authors": ["阶段协调者与作者", "来源组阅读・摘要・识图", "建关系并完成正常修稿"],
            "compile-proposal": ["freeze 固定稿", "UUID・局部引用・private", "合并 expected 后交发布"],
        },
    },
    "after": {
        "title": "修改后 · 未来目标架构",
        "subtitle": "target future · 计划设计，尚未实现或部署",
        "note": "Gaussian 连续降权；权重可以很低，材料仍保留可检索；本目标不引入退出或删除。",
        "lines": {
            "base-search": ["baseSearch 基础检索", "词法・内容向量・语义图", "行为筛选前固定独立锚点"],
            "delivery-confirm": ["宿主确认实际交付", "精确版本＋原始锚点", "非空交付：命中版本 hits +1"],
            "behavior-model": ["批量共交付学习", "标准 KL-NMF → 行为 φ", "模型快照・同空间重放"],
            "access-hint": ["Gaussian 候选与访问", "H_j 质量累计＋版本基准", "unknown 区间交综合评分"],
            "source-collection": ["独立采集", "原件保全＋采集回执", "维护显式消费已有快照"],
            "prepare-workset": ["实际工作集与 prepare", "增量差异・覆盖清单", "定位解析与固定读取包"],
            "semantic-authors": ["有限语义工作组", "按共读量启用作者", "提案・关系与正常修稿"],
            "compile-proposal": ["程序编译固定稿", "依赖・符号・规则合同", "生成不可变 frozen"],
        },
    },
}

# Every unchanged edge, its geometry and its label are shared verbatim.
# Points are explicit so the final SVG is editable without the generator.
COMMON_EDGES = [
    ("brief-to-main", [(410, 390), (450, 390)], "flow", None),
    ("main-to-search", [(780, 390), (820, 390)], "flow", None),
    ("base-to-score", [(1150, 390), (1190, 390)], "flow", None),
    ("score-to-rank", [(1520, 390), (1560, 390)], "flow", None),
    ("rank-to-main", [(1725, 330), (1725, 255), (615, 255), (615, 330)], "flow",
     (1170, 241, "预算内检索结果", "middle")),
    ("main-to-delivery", [(615, 450), (615, 570)], "flow",
     (628, 518, "实际接收后", "start")),
    ("confirm-to-events", [(780, 630), (820, 630)], "flow", None),
    ("events-to-model", [(1150, 630), (1190, 630)], "flow", None),
    ("model-to-hint", [(1520, 630), (1560, 630)], "flow", None),
    ("hint-to-score", [(1725, 570), (1725, 520), (1355, 520), (1355, 450)], "flow",
     (1540, 508, "候选与访问提示", "middle")),
    ("store-to-brief", [(450, 858), (45, 858), (45, 390), (80, 390)], "data", None),
    ("store-to-base-search", [(45, 390), (45, 294), (985, 294), (985, 330)], "data",
     (245, 281, "只读：已接受知识", "middle")),
    ("events-in-project-store", [(985, 690), (985, 800)], "data",
     (1000, 756, "同库", "start")),
    ("embedding-to-store", [(1560, 858), (1510, 858)], "data", None),
    ("sources-to-collection", [(410, 1120), (450, 1120)], "flow", None),
    ("collection-to-prepare", [(780, 1120), (820, 1120)], "flow", None),
    ("prepare-to-authors", [(1150, 1120), (1190, 1120)], "flow", None),
    ("authors-to-compile", [(1520, 1120), (1560, 1120)], "flow", None),
    ("compile-to-publisher", [(1725, 1180), (1725, 1260)], "flow", None),
    ("publisher-to-stage", [(1560, 1315), (1520, 1315)], "control", None),
    ("stage-to-prepare", [(820, 1315), (800, 1315), (800, 1220), (985, 1220), (985, 1180)],
     "control", (1010, 1233, "适用长任务", "start")),
    ("publisher-to-store", [(1890, 1315), (1960, 1315), (1960, 948), (1465, 948), (1465, 915)], "flow",
     (1725, 936, "唯一发布・原子接受", "middle")),
    ("owner-to-maintain", [(245, 1490), (245, 1430), (760, 1430), (760, 1200), (900, 1200), (900, 1180)], "control",
     (430, 1417, "维护控制", "middle")),
    ("owner-to-stop", [(410, 1550), (450, 1550)], "control", None),
    ("stop-to-release", [(1150, 1550), (1190, 1550)], "flow", None),
]

AFTER_EDGES = [
    ("base-anchors-to-delivery", [(985, 450), (985, 546), (795, 546), (795, 598), (780, 598)],
     "data", (997, 493, "保留原始锚点", "start")),
    ("current-anchors-to-behavior-candidates", [(985, 546), (1640, 546), (1640, 570)],
     "data", (1415, 541, "当前锚点 / 行为候选", "middle")),
    ("facts-to-gaussian-projection", [(1070, 690), (1070, 720), (1725, 720), (1725, 690)],
     "data", (1395, 709, "逐事件更新 H/R 与基准", "middle")),
]


def xml_text(x, y, text, size=22, weight=400, fill="#283342", anchor="middle"):
    return (f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}">{escape(text)}</text>')


def render_node(n, changed=False):
    bg, stroke = PALETTE[n["role"]]
    x, y, w, h = (n[k] for k in ("x", "y", "w", "h"))
    parts = [f'<g id="{n["id"]}" data-role="{n["role"]}">',
             f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" '
             f'fill="{bg}" stroke="{stroke}" stroke-width="2.3"/>']
    baselines = [y + h/2 - 27, y + h/2 + 5, y + h/2 + 36]
    for i, line in enumerate(n["lines"]):
        parts.append(xml_text(x+w/2, baselines[i], line,
                              size=24 if i == 0 else 21, weight=650 if i == 0 else 400))
    if changed:
        parts.append(f'<circle cx="{x+w-4}" cy="{y+4}" r="13" '
                     'fill="#FFF8E4" stroke="#C6973F" stroke-width="1.8"/>')
        parts.append(xml_text(x+w-4, y+10, "Δ", 17, 700, "#9B6C1E"))
    parts.append('</g>')
    return "\n".join(parts)


def render_edge(edge):
    id, pts, kind, label = edge
    color = {"flow": "#596676", "data": "#99A5B4", "control": "#A0A7B3"}[kind]
    dash = ' stroke-dasharray="7 6"' if kind != "flow" else ""
    points = " ".join(f"{x},{y}" for x, y in pts)
    parts = [f'<g id="{id}" data-edge-type="{kind}">',
             f'<polyline points="{points}" fill="none" stroke="{color}" '
             f'stroke-width="2.2"{dash} marker-end="url(#{kind}-arrow)" '
             'stroke-linejoin="round"/>']
    if label:
        x, y, text, anchor = label
        parts.append(xml_text(x, y, text, 19, fill="#637083", anchor=anchor))
    parts.append('</g>')
    return "\n".join(parts)


def build(version):
    v = VERSIONS[version]
    changed = [node(id, x, y, v["lines"][id], role)
               for id, (x, y, role) in CHANGED_SLOTS.items()]
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc">',
         f'<title id="title">{escape(v["title"])}</title>',
         '<desc id="desc">同源比较图。颜色区分主agent、子agent、代码、来源和存储。'
         '实线为工作或交付流，虚线为数据和控制。带Δ的节点是前后修改部分。</desc>',
         '<defs>']
    for kind, color in (("flow", "#596676"), ("data", "#99A5B4"), ("control", "#A0A7B3")):
        p.append(f'<marker id="{kind}-arrow" markerWidth="10" markerHeight="10" '
                 'refX="9" refY="5" orient="auto" markerUnits="userSpaceOnUse">'
                 f'<path d="M 0 0 L 10 5 L 0 10 Z" fill="{color}"/></marker>')
    p += ['</defs>', f'<g font-family="{FONT}">',
          f'<rect width="{W}" height="{H}" fill="#FCFDFE"/>',
          xml_text(80, 76, v["title"], 43, 700, anchor="start"),
          xml_text(80, 117, v["subtitle"], 23, fill="#66758A", anchor="start"),
          xml_text(80, 163, v["note"], 22, fill="#56667B", anchor="start")]

    lx = 1190
    for role, label, width in (("main", "主 agent", 166), ("agent", "子 agent", 167),
                               ("code", "代码执行", 170), ("data", "来源 / 存储", 210)):
        bg, stroke = PALETTE[role]
        p.append(f'<rect x="{lx}" y="48" width="24" height="20" rx="4" '
                 f'fill="{bg}" stroke="{stroke}" stroke-width="1.8"/>')
        p.append(xml_text(lx+34, 66, label, 20, anchor="start"))
        lx += width
    p.append(xml_text(1890, 115, "Δ 本轮调整　｜　其余节点与连线完全同源", 19,
                      fill="#7B725F", anchor="end"))

    # Swimlanes share exactly the same geometry in both images.
    for id, y, h, label in (("business-lane", 198, 535, "01  主业务、检索与真实交付反馈"),
                            ("store-lane", 770, 198, "02  项目知识与共享编码设施"),
                            ("maintenance-lane", 992, 403, "03  后台维护：来源到接受版本"),
                            ("lifecycle-lane", 1450, 190, "04  维护控制与业务收尾")):
        p.append(f'<g id="{id}"><rect x="20" y="{y}" width="1980" height="{h}" '
                 'rx="16" fill="#FFFFFF" stroke="#E1E6ED" stroke-width="1.5"/>')
        p.append(xml_text(80, y+34, label, 22, 650, "#45536B", anchor="start"))
        p.append('</g>')

    p += ['<g id="retrieval-worker">',
          '<rect x="800" y="307" width="740" height="163" rx="18" '
          'fill="#FFF9EE" stroke="#D7BD91" stroke-dasharray="6 5" stroke-width="1.5"/>',
          xml_text(1170, 303, "检索 worker（子 agent）", 19, 600, "#9A723E"),
          '</g>', '<g id="edges">']
    p += [render_edge(e) for e in COMMON_EDGES]
    if version == "after":
        p += [render_edge(e) for e in AFTER_EDGES]
    p += ['</g>', '<g id="nodes">']
    p += [render_node(n) for n in COMMON_NODES]
    p += [render_node(n, changed=True) for n in changed]
    p += ['</g>',
          xml_text(80, 1846, "实线：工作 / 交付流　　虚线：数据 / 控制依赖　　search・read・rank 本身不算交付", 20,
                   fill="#697589", anchor="start"),
          xml_text(1890, 1846, "2026-11-17 · 同网格比较", 19, fill="#7E8997", anchor="end"),
          '</g></svg>']
    return "\n".join(p) + "\n", deepcopy(COMMON_NODES) + changed


def verify_pair(before_path, after_path):
    a = ET.parse(before_path).getroot()
    b = ET.parse(after_path).getroot()
    am = {el.get("id"): el for el in a.iter() if el.get("id")}
    bm = {el.get("id"): el for el in b.iter() if el.get("id")}
    common_ids = [n["id"] for n in COMMON_NODES] + [e[0] for e in COMMON_EDGES]
    common_ids += ["retrieval-worker", "business-lane", "store-lane", "maintenance-lane", "lifecycle-lane"]
    for id in common_ids:
        assert ET.tostring(am[id]) == ET.tostring(bm[id]), f"Shared object changed: {id}"
    for id in CHANGED_SLOTS:
        ar, br = am[id][0], bm[id][0]
        assert ar.attrib == br.attrib, f"Changed slot geometry or role changed: {id}"
    return {
        "canvas": [W, H],
        "unchanged_nodes": [n["id"] for n in COMMON_NODES],
        "unchanged_edges": [e[0] for e in COMMON_EDGES],
        "changed_slots_same_geometry": list(CHANGED_SLOTS),
        "added_edges_after": [e[0] for e in AFTER_EDGES],
        "check": "exact XML equality for every shared node, edge and lane",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--inkscape", default=shutil.which("inkscape"))
    parser.add_argument("--qa-report", type=Path)
    args = parser.parse_args()
    paths = []
    for version in ("before", "after"):
        path = HERE / f"memory-system-{version}.svg"
        svg, _ = build(version)
        path.write_text(svg, encoding="utf-8")
        paths.append(path)
    report = verify_pair(*paths)
    if args.render:
        if not args.inkscape:
            raise RuntimeError("--render requires Inkscape; pass --inkscape explicitly")
        for path in paths:
            for kind in ("png", "pdf"):
                subprocess.run([args.inkscape, str(path), f"--export-type={kind}",
                                f"--export-filename={path.with_suffix('.'+kind)}"], check=True)
    if args.qa_report:
        args.qa_report.parent.mkdir(parents=True, exist_ok=True)
        args.qa_report.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
