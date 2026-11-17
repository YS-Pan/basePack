"""Compare the deployed 0.17.4 organization with the 0.18 wave target.

Only the maintenance organization changes. The rest of both system diagrams is
rendered from shared objects and verified by exact XML comparison.
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

import generate_memory_system as base

HERE = Path(__file__).resolve().parent
W, H = 2040, 2670
node = base.node
text = base.xml_text
edge = base.render_edge

# These data and retrieval contracts are already deployed. They are the same in
# both figures; the earlier 0.16 -> 0.17 comparison remains a separate artifact.
COMMON_NODES = deepcopy(base.COMMON_NODES[:8])
COMMON_NODES = [n for n in COMMON_NODES if n["id"] != "source-material"]
for n in COMMON_NODES:
    if n["id"] == "delivery-events":
        n["lines"] = ["真实交付记录", "精确版本集合＋delivery_id", "J 记录首收；非空推进 C"]
    elif n["id"] == "project-store":
        n["lines"] = ["项目唯一 SurrealDB", "原证・知识版本・语义图・交付事实", "原件与 assets 沿项目保存"]

for id in ("base-search", "delivery-confirm", "behavior-model", "access-hint"):
    x, y, role = base.CHANGED_SLOTS[id]
    COMMON_NODES.append(node(id, x, y, base.VERSIONS["after"]["lines"][id], role))

COMMON_NODES += [
    node("source-material", 80, 1080,
         ["项目来源", "文件・private・绑定聊天", "附件与可定位原证"], "data"),
    node("source-collection", 450, 1080,
         ["独立采集", "原件保全＋采集回执", "维护消费已有快照"], "code"),
    node("prepare-workset", 820, 1080,
         ["实际工作集与 prepare", "增量差异・覆盖清单", "定位解析与固定读取包"], "code"),
    node("compile-proposal", 1190, 1080,
         ["程序编译固定稿", "依赖・符号・规则合同", "生成不可变 frozen"], "code"),
    node("unique-publisher", 1560, 1080,
         ["唯一发布者", "调用 apply 原子接受", "实际版本・覆盖与缺口回执"], "agent"),
    node("semantic-writing", 1560, 1610,
         ["原文智能创作", "分块・摘要・关系判断", "固定 prepare＋普通修稿"], "agent", h=150),
    node("owner-control", 80, 2240,
         ["唯一 owner ＋ control", "维护所有权与实际句柄", "原父保留 stop 与恢复权限"], "code"),
    node("stop-owned-work", 450, 2240,
         ["业务结束：stop 自有 control", "取消自有协调者及后代", "保留获准发布的明确终态"], "code", 700),
    node("release-owner", 1190, 2240,
         ["确认发布终态后 release", "未明状态保留 owner 与待处理项", "共享数据库继续运行"], "code", 700),
    node("host-guidance", 80, 2460,
         ["宿主 skills 与订阅 agent", "agent-team・工程判断・资料边界", "语义理解与创作由 agent 完成"], "data", 830),
    node("shared-condor", 1000, 2460,
         ["共享 embedding 与 HTCondor 设施", "内容向量 ≠ 纯行为 φ；按实际容量调用", "模型与重任务资源独立托管"], "data", 890),
]

SLOTS = {
    "terra-init": (80, 1340, "agent", 330, 150),
    "plan-registry": (450, 1340, "code", 330, 150),
    "root-start-gate": (820, 1340, "main", 330, 150),
    "luna-execution": (1190, 1340, "agent", 330, 150),
    "task-claim": (1560, 1340, "code", 330, 150),
    "draft-submit": (1190, 1610, "code", 330, 150),
    "retirement-receipt": (820, 1610, "code", 330, 150),
    "coordinator-notification": (450, 1610, "agent", 330, 150),
    "terra-publication": (80, 1610, "agent", 330, 150),
    "root-wave-close": (80, 1900, "main", 1810, 130),
}

VERSIONS = {
    "before": {
        "title": "修改前 · 当前记忆系统",
        "subtitle": "0.17.4 deployed · KL-NMF / Gaussian 已部署；维护按来源组接续",
        "state": "现用组织：Terra 在执行期间接收作者结果、正常修稿并逐组接续；阶段边界交接。",
        "lines": {
            "terra-init": ["Terra 阶段协调者", "按来源组规划与选择作者", "同一 turn 持续组织维护"],
            "plan-registry": ["组级派工程序", "固定 prepare＋descriptor", "生成当前作者的任务 prompt"],
            "root-start-gate": ["原父任务持有句柄", "按实际容量启动本组", "接收阶段交接并保留所有权"],
            "luna-execution": ["Luna 执行指定来源组", "按当前分配开展工作", "完成后回报协调者"],
            "task-claim": ["指定当前来源组", "作者绑定当前准备包", "后续来源由协调者再分配"],
            "draft-submit": ["作者交付固定稿", "path / hash＋覆盖与错误", "固定引用交给协调者"],
            "retirement-receipt": ["组级结果与回执", "协调者逐组接收结果", "依据实际句柄安排后续"],
            "coordinator-notification": ["Terra 继续组织", "等待作者与正常修稿", "汇总后续派下一来源组"],
            "terra-publication": ["Terra 汇总与发布", "固定完成稿交程序编译", "阶段边界才交 FINAL"],
            "root-wave-close": ["原父核阶段终态", "保留实际接受、未发稿与剩余范围", "转交下一干净阶段，或按维护收尾释放"],
        },
        "bounds": [
            "接续与修稿沿同一维护 receipt / owner / control；唯一发布与原子接受已经存在。",
            "0.17.4 的实际阶段与作者模型核验已有小批证据；全项目剩余维护仍未完成。",
        ],
    },
    "after": {
        "title": "修改后 · 有限任务池目标",
        "subtitle": "0.18 target · 实现中；本图不表示已安装、已验宿主闭环或完成维护",
        "state": "目标组织：Terra 两 turn；固定 Luna 池自领任务；普通完成只留邮箱，最后正常者 followup 同一 Terra。",
        "lines": {
            "terra-init": ["Terra 第一 turn", "一次规划有限独立任务", "启动固定池；init 回执即结束"],
            "plan-registry": ["预登记任务与固定 Luna", "目标・来源・写目标・输出", "脚本生成 prompt；保留恢复位"],
            "root-start-gate": ["原父核 Terra 已 idle", "登记成员已启动或明确失败", "seal 后向已启动者一次 go"],
            "luna-execution": ["Luna 自主循环", "首 turn 宿主事件等待 go", "逐项领取，不逐组续派"],
            "task-claim": ["原子 claim＋任务 prompt", "核 owner / control / wave", "有活领取；无活原子退队"],
            "draft-submit": ["按固定引用 submit", "稿 / 覆盖 / 错误 path＋hash", "提交后再领下一个任务"],
            "retirement-receipt": ["无活与活动数同原子更新", "最后正常者核全部任务", "保存波 receipt＋唯一通知权"],
            "coordinator-notification": ["最后正常 Luna 通知", "实际 followup 同一 Terra", "稳定 wave＋固定 receipt"],
            "terra-publication": ["Terra 第二 turn", "汇总固定引用；唯一 publisher", "固定发布结果即 FINAL"],
            "root-wave-close": ["原父观察两方终态后机械 close", "核 Terra FINAL 与最后 Luna 通知写回 / 宿主终态；保留未发稿与剩余范围", "正常期间 Terra 不 wait、不轮询；发布后不为通知 ack 追加 turn"],
        },
        "bounds": [
            "init ≠ 执行终态 ≠ 知识接受 ≠ 维护完成；seal 不证明 Terra idle，始终预留 Terra 恢复位。",
            "通知非事务：pending / accepted 分记；异常、残留 claimed、stop、晚回调不伪成功，原错交原父恢复。",
        ],
    },
}

COMMON_EDGES = deepcopy(base.COMMON_EDGES[:14]) + deepcopy(base.AFTER_EDGES)
COMMON_EDGES += [
    ("sources-to-collection", [(410, 1140), (450, 1140)], "flow", None),
    ("collection-to-prepare", [(780, 1140), (820, 1140)], "flow", None),
    ("prepare-to-organization", [(985, 1200), (985, 1240), (245, 1240), (245, 1340)],
     "flow", (430, 1229, "固定读取包进入维护组织", "middle")),
    ("compile-to-publisher", [(1520, 1140), (1560, 1140)], "flow", None),
    ("publisher-to-store", [(1890, 1140), (1970, 1140), (1970, 948), (1465, 948), (1465, 915)],
     "flow", (1735, 936, "唯一发布・原子接受", "middle")),
    ("publication-to-compile", [(245, 1760), (245, 1820), (1940, 1820), (1940, 1240), (1355, 1240), (1355, 1200)],
     "flow", (1720, 1229, "固定稿 → 编译 → 发布", "middle")),
    ("publisher-receipt-to-terra", [(1725, 1200), (1725, 1215), (1915, 1215), (1915, 1848), (210, 1848), (210, 1760)],
     "data", (1660, 1876, "固定 frozen / result 与接受回执返回同一发布者", "middle")),
    ("luna-to-source-writing", [(1725, 1490), (1725, 1610)], "flow",
     (1740, 1573, "本任务", "start")),
    ("writing-to-submit", [(1560, 1685), (1520, 1685)], "flow", None),
    ("owner-to-maintain", [(245, 2240), (245, 2170), (45, 2170), (45, 1280), (145, 1280), (145, 1340)],
     "control", None),
    ("owner-to-stop", [(410, 2300), (450, 2300)], "control", None),
    ("stop-to-release", [(1150, 2300), (1190, 2300)], "flow", None),
]

# All differing edges are inside the organization panel. Shared edges above are
# checked including paths, labels and colors; they are never laid out twice.
ORG_EDGES = [
    ("terra-to-registry", [(410, 1415), (450, 1415)], "flow", None),
    ("registry-to-gate", [(780, 1415), (820, 1415)], "control", None),
    ("gate-to-luna", [(1150, 1415), (1190, 1415)], "flow", None),
    ("luna-to-claim", [(1520, 1415), (1560, 1415)], "flow", None),
    ("receipt-to-notifier", [(820, 1685), (780, 1685)], "flow", None),
    ("notification-to-terra", [(450, 1685), (410, 1685)], "flow", None),
    ("terra-to-root-close", [(245, 1848), (245, 1900)], "control", None),
]


def render_node(n, changed=False):
    bg, stroke = base.PALETTE[n["role"]]
    x, y, w, h = (n[k] for k in ("x", "y", "w", "h"))
    p = [f'<g id="{n["id"]}" data-role="{n["role"]}">',
         f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" '
         f'fill="{bg}" stroke="{stroke}" stroke-width="2.3"/>']
    for i, line in enumerate(n["lines"]):
        p.append(text(x+w/2, y+h/2-27+32*i, line,
                      24 if i == 0 else 21, 650 if i == 0 else 400))
    if changed:
        p += [f'<circle cx="{x+w-4}" cy="{y+4}" r="13" fill="#FFF8E4" '
              'stroke="#C6973F" stroke-width="1.8"/>',
              text(x+w-4, y+10, "Δ", 17, 700, "#9B6C1E")]
    p.append('</g>')
    return "\n".join(p)


def lane(id, y, h, label):
    return (f'<g id="{id}"><rect x="20" y="{y}" width="1980" height="{h}" '
            'rx="16" fill="#FFFFFF" stroke="#E1E6ED" stroke-width="1.5"/>'
            + text(80, y+34, label, 22, 650, "#45536B", anchor="start") + '</g>')


def build(version):
    v = VERSIONS[version]
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc">',
         f'<title id="title">{escape(v["title"])}</title>',
         '<desc id="desc">完整记忆系统同源对照。蓝色为主agent，橙色为子agent，绿色为代码执行，'
         '灰色为来源与存储。Terra与Luna均为子agent，不以模型区分角色颜色。带Δ的节点为维护组织变化。</desc>',
         '<defs>']
    for kind, color in (("flow", "#596676"), ("data", "#99A5B4"), ("control", "#A0A7B3")):
        p.append(f'<marker id="{kind}-arrow" markerWidth="10" markerHeight="10" '
                 'refX="9" refY="5" orient="auto" markerUnits="userSpaceOnUse">'
                 f'<path d="M 0 0 L 10 5 L 0 10 Z" fill="{color}"/></marker>')
    p += ['</defs>', f'<g font-family="{base.FONT}">',
          f'<rect width="{W}" height="{H}" fill="#FCFDFE"/>',
          '<g id="version-heading">',
          text(80, 76, v["title"], 43, 700, anchor="start"),
          text(80, 117, v["subtitle"], 22, fill="#66758A", anchor="start"),
          '</g>', '<g id="unchanged-overview">',
          text(80, 163, "共同合同：Gaussian 连续降权；低 weight 的材料仍保留可检索，不退出、不删除、不 GC。",
               22, fill="#56667B", anchor="start"), '</g>', '<g id="legend">']
    lx = 1190
    for role, label, width in (("main", "主 agent", 166), ("agent", "子 agent", 167),
                               ("code", "代码执行", 170), ("data", "来源 / 存储", 210)):
        bg, stroke = base.PALETTE[role]
        p += [f'<rect x="{lx}" y="48" width="24" height="20" rx="4" '
              f'fill="{bg}" stroke="{stroke}" stroke-width="1.8"/>',
              text(lx+34, 66, label, 20, anchor="start")]
        lx += width
    p += [text(1890, 115, "Δ 维护组织调整　｜　其余图元完整 XML 一致", 19,
               fill="#7B725F", anchor="end"), '</g>']
    for spec in (("business-lane", 198, 535, "01  主业务、检索与真实交付反馈"),
                 ("store-lane", 770, 198, "02  项目知识与共享编码设施"),
                 ("maintenance-lane", 992, 1170, "03  后台维护：来源到接受版本"),
                 ("lifecycle-lane", 2190, 190, "04  维护控制与业务收尾")):
        p.append(lane(*spec))
    p += ['<g id="retrieval-worker">',
          '<rect x="800" y="307" width="740" height="163" rx="18" '
          'fill="#FFF9EE" stroke="#D7BD91" stroke-dasharray="6 5" stroke-width="1.5"/>',
          text(1170, 303, "检索 worker（子 agent）", 19, 600, "#9A723E"), '</g>',
          '<g id="organization-frame">',
          '<rect x="65" y="1270" width="1840" height="790" rx="18" '
          'fill="#FFFCF7" stroke="#D7BD91" stroke-dasharray="7 6" stroke-width="1.6"/>',
          text(95, 1306, "维护组织：角色颜色固定；Terra / Luna 均为主任务下属子 agent", 20, 600,
               "#8D6B3C", anchor="start"), '</g>',
          '<g id="shared-edges">']
    p += [edge(e) for e in COMMON_EDGES]
    p += ['</g>', '<g id="organization-edges">']
    p += [edge(e) for e in ORG_EDGES]
    if version == "before":
        p += [edge(("results-to-retirement", [(1190, 1685), (1150, 1685)], "flow", None)),
              edge(("coordinator-next-assignment", [(615, 1610), (615, 1545), (1355, 1545), (1355, 1490)],
                    "control", (950, 1530, "逐组接续与正常修稿", "middle")))]
    else:
        p += [edge(("submit-next-claim", [(1520, 1710), (1540, 1710), (1540, 1785),
                                          (1900, 1785), (1900, 1520), (1770, 1520), (1770, 1490)],
                    "control", (1770, 1806, "提交后再领", "middle"))),
              edge(("no-task-retirement", [(1560, 1450), (1540, 1450), (1540, 1570), (985, 1570), (985, 1610)],
                    "control", (1115, 1599, "无活：原子退队", "middle")))]
    p += ['</g>', '<g id="shared-nodes">']
    p += [render_node(n) for n in COMMON_NODES]
    p += ['</g>', '<g id="organization-nodes">']
    for id, (x, y, role, w, h) in SLOTS.items():
        p.append(render_node(node(id, x, y, v["lines"][id], role, w, h), changed=True))
    p += ['</g>', '<g id="version-boundaries">',
          text(95, 2085, v["state"], 21, 600, "#5C6676", anchor="start")]
    for i, line in enumerate(v["bounds"]):
        p.append(text(95, 2118+29*i, line, 20, fill="#6B7584", anchor="start"))
    p += ['</g>', '<g id="footer">',
          text(80, 2633, "实线：工作 / 交付　　虚线：数据 / 控制　　search・read・rank 本身不算交付", 20,
               fill="#697589", anchor="start"),
          text(1890, 2633, "2026-11-17 · 0.17.4 → 0.18 组织对照", 19,
               fill="#7E8997", anchor="end"), '</g>', '</g></svg>']
    return "\n".join(p) + "\n"


def verify_pair(before, after):
    roots = [ET.parse(path).getroot() for path in (before, after)]
    maps = [{el.get("id"): el for el in root.iter() if el.get("id")} for root in roots]
    common_ids = [n["id"] for n in COMMON_NODES] + [e[0] for e in COMMON_EDGES]
    common_ids += ["legend", "unchanged-overview", "retrieval-worker", "organization-frame",
                   "business-lane", "store-lane", "maintenance-lane", "lifecycle-lane", "footer"]
    for id in common_ids:
        assert ET.tostring(maps[0][id]) == ET.tostring(maps[1][id]), f"Shared object changed: {id}"
    for id in SLOTS:
        assert maps[0][id][0].attrib == maps[1][id][0].attrib, f"Slot geometry/role changed: {id}"
        assert maps[0][id].get("data-role") == maps[1][id].get("data-role")
    shared_canvases = []
    for root in roots:
        shared = deepcopy(root)
        parents = {child: parent for parent in shared.iter() for child in parent}
        for el in list(shared.iter()):
            if el.get("id") in {"title", "version-heading", "organization-nodes",
                                "organization-edges", "version-boundaries"}:
                parents[el].remove(el)
        shared_canvases.append(ET.tostring(shared))
    assert shared_canvases[0] == shared_canvases[1], "Shared canvas changed outside organization/title"
    return {
        "canvas": [W, H], "current": "0.17.4 deployed", "target": "0.18 implementation in progress",
        "unchanged_nodes": [n["id"] for n in COMMON_NODES],
        "unchanged_edges": [e[0] for e in COMMON_EDGES],
        "shared_objects_exact_xml": common_ids,
        "organization_slots_same_geometry_and_role": list(SLOTS),
        "whole_shared_canvas_exact_xml": True,
        "check": "exact XML equality: all shared node text, geometry, colors, edge paths and labels",
        "runtime_claim": "diagram QA only; target lifecycle not runtime acceptance",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--inkscape", default=shutil.which("inkscape"))
    parser.add_argument("--qa-report", type=Path)
    args = parser.parse_args()
    paths = []
    for version in ("before", "after"):
        path = HERE / f"memory-system-wave-{version}.svg"
        path.write_text(build(version), encoding="utf-8")
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
