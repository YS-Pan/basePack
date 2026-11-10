"""Project memory actions; SurrealDB's own tools handle server and backup work."""

import json
from pathlib import Path


def register_commands(subparsers):
    memory = subparsers.add_parser("memory", help="Project-local multilevel memory")
    commands = memory.add_subparsers(dest="memory_action", required=True)
    actions = {name: commands.add_parser(name) for name in
               ("init", "guide", "sources", "prepare", "apply", "embed", "search", "read", "neighbors", "brief", "changes", "rank")}
    actions["prepare"].add_argument("--paths", nargs="+", required=True)
    actions["apply"].add_argument("--batch", required=True, help="Agent-produced UTF-8 JSON batch")
    actions["search"].add_argument("--text", required=True)
    actions["search"].add_argument("--scope", default="")
    actions["search"].add_argument("--limit", type=int, default=12)
    actions["search"].add_argument("--literal", action="store_true", help="Case-insensitive substring search in stored titles/text")
    actions["search"].add_argument("--mode", choices=["hybrid", "text", "vector"], default="hybrid")
    actions["search"].add_argument("--timeout", type=float, default=600)
    actions["embed"].add_argument("--ids", nargs="+", help="Member IDs; otherwise index current representations")
    actions["embed"].add_argument("--timeout", type=float, default=600)
    actions["read"].add_argument("id", help="Member ID; follow a knowledge node's evidence via neighbors")
    actions["neighbors"].add_argument("id")
    actions["neighbors"].add_argument("--include-stale", action="store_true", help="Explicit historical inspection")
    actions["brief"].add_argument("--task", default="")
    actions["brief"].add_argument("--limit", type=int, default=6)
    actions["changes"].add_argument("--scope", nargs="+", required=True)
    actions["changes"].add_argument("--deep", action="store_true")
    actions["rank"].add_argument("--input", required=True, help="Read candidates with agent scores")
    actions["rank"].add_argument("--budget", type=int, default=6000, help="Returned text character budget")
    for command in actions.values():
        command.add_argument("--output", help="Write JSON here and return its location")


def dispatch(args, config):
    action = args.memory_action
    if action == "guide":
        result = {"skill": str(Path(__file__).with_name("SKILL.md"))}
    elif action == "rank":
        from .selection import select_scored
        result = select_scored(json.loads(Path(args.input).read_text(encoding="utf-8")), args.budget)
    else:
        from .store import Memory
        memory = Memory(config)
        if action == "init":
            result = memory.install_schema()
            _activate(config)
        elif action == "sources":
            result = memory.sources()
        elif action == "prepare":
            result = memory.prepare(args.paths)
        elif action == "apply":
            result = memory.apply(json.loads(Path(args.batch).read_text(encoding="utf-8")))
        elif action == "embed":
            result = memory.embed_members(args.ids, timeout=args.timeout)
        elif action == "search":
            if args.mode == "text":
                result = memory.search(args.text, scope=args.scope, limit=args.limit, literal=args.literal)
            elif args.mode == "vector":
                result = memory.vector_search(args.text, scope=args.scope, limit=args.limit, timeout=args.timeout)
            else:
                result = memory.hybrid_search(args.text, scope=args.scope, limit=args.limit,
                                              timeout=args.timeout, literal=args.literal)
        elif action == "read":
            result = memory.read(args.id)
        elif action == "neighbors":
            result = memory.neighbors(args.id, include_stale=args.include_stale)
        elif action == "brief":
            result = memory.brief(task=args.task, limit=args.limit)
        elif action == "changes":
            result = memory.changes(args.scope, deep=args.deep)
    if args.output:
        path = Path(args.output).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"output": str(path)}, 0
    return result, 0


def _activate(config):
    path = config.root / ".basepack/instructions.md"
    existing = path.read_text(encoding="utf-8")
    start, end = "<!-- basepack-memory:start -->", "<!-- basepack-memory:end -->"
    python = str(config.python).replace("'", "''")
    project_config = config.path.relative_to(config.root).as_posix().replace("'", "''")
    skill = Path(__file__).with_name("SKILL.md").resolve().as_posix()
    section = f"""{start}
记忆已在本项目启用。开始或接续任务时，读取启动信息：

```powershell
& '{python}' -m basepack --config '{project_config}' memory brief --task '<当前任务>'
```

直接保留当前 mandatory 信息；stale=true 的内容只作待核，不当作当前事实。brief 会快检已登记原件与配置的 source_scope；出现 changes/pending 时，在当前任务预算内共读并维护必要小批，余项明确交接。可将维护和检索合并为一次 worker 委托，交付实际证据与缺口；多轮检索、筛选与重排派工前，用同一命令前缀运行 `config ai --purpose retrieval` 解析项目档位。按 [记忆流程](<{skill}>) 执行。
{end}"""
    if start in existing:
        before, _, tail = existing.partition(start)
        closing = tail.index(end)
        after = tail[closing + len(end):]
        updated = before + section + after
    else:
        updated = existing.rstrip() + "\n\n" + section + "\n"
    path.write_text(updated, encoding="utf-8")
