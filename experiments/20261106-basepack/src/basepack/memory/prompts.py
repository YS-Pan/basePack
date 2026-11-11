"""Render host-executed maintenance briefs without opening the memory store."""

import json
import os
from pathlib import Path, PurePath
import shlex
from string import Template
from uuid import uuid4


def memory_command(config, *args):
    """Build a command for the current platform's standard shell."""
    parts = [str(config.python), "-X", "utf8", "-m", "basepack", "--config",
             str(config.path), "memory", *(str(arg) for arg in args)]
    if os.name == "nt":
        return "& " + " ".join("'" + part.replace("'", "''") + "'" for part in parts)
    return shlex.join(parts)


def prompt_dispatch(config, receipt, control, *, role="coordinator", tier=None, paths=None):
    """Describe a future render without reading the receipt or loading a template."""
    defaults = {"coordinator": "tier2", "reader": "tier1"}
    default_tier = defaults[role]
    if role == "reader" and not paths:
        raise ValueError("reader requires at least one project-relative path")
    if role == "coordinator" and paths is not None:
        raise ValueError("coordinator does not accept paths")
    for path in paths or ():
        relative = PurePath(path)
        if not str(path) or relative.anchor or ".." in relative.parts:
            raise ValueError(f"Source path must be project-relative: {path}")
    resolved = config.resolve_ai(tier=tier or default_tier)
    args = ["prompt", "--receipt", str(Path(receipt).resolve()), "--control",
            str(Path(control).resolve()), "--role", role, "--tier", resolved["tier"]]
    if paths:
        args.extend(["--paths", *paths])
    return {"role": role, **resolved, "render_command": memory_command(config, *args)}


def _reader_hints(material, paths):
    """Select compact receipt hints without copying original text into a prompt."""
    selected = {PurePath(path).as_posix() for path in paths}
    semantic = material["semantic"]
    member_paths = {member["id"]: item["path"] for item in semantic for member in item["members"]}
    sources = []
    for item in semantic:
        if item["path"] not in selected:
            continue
        sources.append({key: item[key] for key in ("path", "reason", "category") if key in item})
        sources[-1]["members"] = [{key: member[key] for key in
                                   ("id", "kind", "reasons", "source_version", "start_line", "end_line")
                                   if key in member} for member in item["members"]]
        if item.get("uncovered_ranges"):
            sources[-1]["uncovered_ranges"] = [{key: row[key] for key in ("start_line", "end_line")}
                                                  for row in item["uncovered_ranges"]]
    relevant, unknown = [], 0
    for relation in material["pending_relations"]:
        basis = relation["basis"]
        known_paths = [item.get("path") or member_paths.get(item["member"]) for item in basis]
        hint = {"id": relation["id"], "basis_members": [item["member"] for item in basis]}
        if any(path in selected for path in known_paths):
            relevant.append(hint)
        elif not basis or any(path is None for path in known_paths):
            unknown += 1
    hints = {"sources": sources, "related_pending_relations": relevant, "unresolved_pending_relations_count": unknown}
    if "codex" in material:
        hints["codex"] = material["codex"]
    return hints


def render_prompt(config, receipt, control, *, role="coordinator", tier=None, paths=None):
    """Render one brief from a saved receipt; no store, locks, or writes are used."""
    dispatch = prompt_dispatch(config, receipt, control, role=role, tier=tier, paths=paths)
    receipt_path = Path(receipt).resolve()
    material = json.loads(receipt_path.read_text(encoding="utf-8"))
    template = Template((Path(__file__).with_name("prompts") / f"{role}.md").read_text(encoding="utf-8"))
    reader = config.resolve_ai(tier="tier1") if role == "coordinator" else None
    work = config.root / "tmp" / "basepack-maintenance" / receipt_path.stem / uuid4().hex
    reading, batch = work / "reading.json", work / "batch.json"
    values = {
        "skill": str(Path(__file__).with_name("SKILL.md").resolve()),
        "root": str(config.root),
        "python": str(config.python),
        "config": str(config.path),
        "receipt": str(receipt_path),
        "control": str(Path(control).resolve()),
        "semantic_count": str(len(material["semantic"])),
        "relations_count": str(len(material["pending_relations"])),
        "feedback_count": str(len(material.get("feedback", []))),
        "paths": json.dumps(paths or [], ensure_ascii=False),
        "hints": json.dumps(_reader_hints(material, paths) if role == "reader" else {}, ensure_ascii=False),
        "codex": json.dumps(material.get("codex", {}), ensure_ascii=False),
        "work": str(work),
        "batch": str(batch),
        "reader_command": memory_command(config, "prompt", "--receipt", receipt_path,
                                         "--control", Path(control).resolve(), "--role", "reader", "--tier", "tier1"),
        "reader_model": reader["model"] if reader else "",
        "reader_effort": reader["reasoning_effort"] if reader else "",
        "prepare_command": memory_command(config, "prepare", "--paths", *(paths or []),
                                          "--output", reading),
        "apply_command": memory_command(config, "apply", "--batch", batch,
                                        "--control", Path(control).resolve()),
        "read_command": memory_command(config, "read", "<member-id>"),
        "neighbors_command": memory_command(config, "neighbors", "<record-id>", "--include-stale"),
        "model": dispatch["model"],
        "effort": dispatch["reasoning_effort"],
        "tier": dispatch["tier"],
    }
    return {"prompt": template.substitute(values), **dispatch}
