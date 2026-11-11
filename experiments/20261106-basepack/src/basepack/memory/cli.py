"""Project memory actions; SurrealDB's own tools handle server and backup work."""

import json
from pathlib import Path


def register_commands(subparsers):
    memory = subparsers.add_parser("memory", help="Project-local multilevel memory")
    commands = memory.add_subparsers(dest="memory_action", required=True)
    actions = {name: commands.add_parser(name) for name in
               ("init", "guide", "sources", "prepare", "apply", "stop", "embed", "search", "read", "neighbors", "brief", "changes", "maintain", "prompt", "rank")}
    actions["prepare"].add_argument("--paths", nargs="+", required=True,
                                    help="Project-relative files; enumerate directories first")
    actions["apply"].add_argument("--batch", required=True, help="Agent-produced UTF-8 JSON batch")
    actions["apply"].add_argument("--control", help="Unique task control file for host cancellation")
    actions["apply"].add_argument("--timeout", type=float, default=600, help="Candidate embedding timeout")
    actions["stop"].add_argument("--control", required=True, help="The task's unique control file")
    actions["search"].add_argument("--text", required=True)
    actions["search"].add_argument("--scope", default="")
    actions["search"].add_argument("--limit", type=int, default=12)
    actions["search"].add_argument("--literal", action="store_true", help="With hybrid: prioritize case-insensitive path/title/text substring matches")
    actions["search"].add_argument("--mode", choices=["hybrid", "vector"],
                                 help="Override memory.search_mode from the project config")
    actions["search"].add_argument("--timeout", type=float, default=600)
    actions["embed"].add_argument("--ids", nargs="+", help="Member IDs; otherwise index current representations")
    actions["embed"].add_argument("--timeout", type=float, default=600)
    actions["read"].add_argument("id", help="Member ID; follow a knowledge node's evidence via neighbors")
    actions["read"].add_argument("--source-version", help="Read an evidence source_version")
    actions["read"].add_argument("--start-line", type=int, help="Evidence start line (inclusive)")
    actions["read"].add_argument("--end-line", type=int, help="Evidence end line (inclusive)")
    actions["read"].add_argument("--locator", help="Image evidence locator as a JSON object")
    actions["neighbors"].add_argument("id")
    actions["neighbors"].add_argument("--include-stale", action="store_true", help="Explicit historical inspection")
    actions["brief"].add_argument("--task", default="")
    actions["brief"].add_argument("--limit", type=int, default=6)
    actions["changes"].add_argument("--scope", nargs="+", required=True)
    actions["changes"].add_argument("--deep", action="store_true")
    actions["maintain"].add_argument("--scope", nargs="+", help="Override new-file discovery; registered sources and pending relations remain included")
    actions["maintain"].add_argument("--codex-registry", help="Host project binding and complete registered roots as UTF-8 JSON")
    actions["maintain"].add_argument("--control", help="Unique task control file for host cancellation")
    actions["maintain"].add_argument("--timeout", type=float, default=600, help="Candidate embedding timeout")
    actions["prompt"].add_argument("--receipt", required=True, help="Maintenance receipt to render as worker context")
    actions["prompt"].add_argument("--control", required=True, help="The same task control file used by maintain and apply")
    actions["prompt"].add_argument("--role", choices=["coordinator", "reader"], default="coordinator")
    actions["prompt"].add_argument("--tier", choices=["tier1", "tier2", "tier3", "tier4"],
                               help="Override the role's default AI tier")
    actions["prompt"].add_argument("--paths", nargs="+", help="Reader's bounded project-relative source files")
    actions["rank"].add_argument("--input", required=True, help="Read candidates with agent scores")
    actions["rank"].add_argument("--budget", type=int, default=6000, help="Returned text character budget")
    for name, command in actions.items():
        if name == "prompt":
            command.set_defaults(output=None)
        else:
            command.add_argument("--output", help="Write JSON here and return its location")


def dispatch(args, config):
    action = args.memory_action
    if action == "guide":
        result = {"skill": str(Path(__file__).with_name("SKILL.md"))}
    elif action == "stop":
        from .maintenance import stop
        stop(args.control)
        result = {"stopped": True}
    elif action == "rank":
        from .selection import select_scored
        result = select_scored(json.loads(Path(args.input).read_text(encoding="utf-8")), args.budget)
    elif action == "prompt":
        from .prompts import render_prompt
        result = render_prompt(config, args.receipt, args.control,
                               role=args.role, tier=args.tier, paths=args.paths)
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
            result = memory.apply(json.loads(Path(args.batch).read_text(encoding="utf-8")),
                                  control=args.control, timeout=args.timeout)
        elif action == "embed":
            result = memory.embed_members(args.ids, timeout=args.timeout)
        elif action == "search":
            mode = args.mode if args.mode is not None else config.memory_search_mode
            if mode == "vector":
                if args.literal:
                    raise ValueError("--literal requires --mode hybrid; vector mode does not support literal matching.")
                result = memory.vector_search(args.text, scope=args.scope, limit=args.limit, timeout=args.timeout)
            else:
                result = memory.hybrid_search(args.text, scope=args.scope, limit=args.limit,
                                              timeout=args.timeout, literal=args.literal)
        elif action == "read":
            result = memory.read(args.id, source_version=args.source_version,
                                 start_line=args.start_line, end_line=args.end_line,
                                 locator=json.loads(args.locator) if args.locator else None)
        elif action == "neighbors":
            result = memory.neighbors(args.id, include_stale=args.include_stale)
        elif action == "brief":
            result = memory.brief(task=args.task, limit=args.limit)
        elif action == "changes":
            result = memory.changes(args.scope, deep=args.deep)
        elif action == "maintain":
            from uuid import uuid4
            from .discovery import discover_sources, retained_codex_paths
            from .maintenance import check
            from .prompts import prompt_dispatch
            control = str(Path(args.control).resolve() if args.control else
                          config.memory_dir / "maintenance" / f"task-{uuid4().hex}.control")
            check(control)
            discovery = discover_sources(config, args.scope)
            codex = _collect_codex(config, args.codex_registry, control=control)
            retained = retained_codex_paths(config, codex["project_id"])
            scope = list(dict.fromkeys([*discovery["paths"], *codex.pop("paths", []), *retained["paths"]]))
            codex["retained_sources"] = len(retained["paths"])
            codex["retained_gaps"] = retained["gaps"]
            result = memory.maintain(scope, control=control, timeout=args.timeout)
            result["codex"] = codex
            result["control"] = control
            result["discovery"] = {"mode": discovery["mode"], "sources": len(scope),
                                   "gaps": discovery["gaps"]}
            if result["needs_semantic"]:
                result["worker"] = prompt_dispatch(config, result["receipt"], control)
    if args.output:
        path = Path(args.output).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"output": str(path)}, 0
    return result, 0


def _collect_codex(config, registry_path, *, control=None):
    """Capture provably assigned threads; leave unavailable binding explicit."""
    import os
    from uuid import uuid4
    from .codex import AppServer, collect_codex, list_threads
    from .codex_binding import classify_threads, discover_binding

    binding = (json.loads(Path(registry_path).read_text(encoding="utf-8")) if registry_path
               else config.raw["memory"].get("codex", {}))
    if not binding.get("project_id") or not binding.get("registry_complete"):
        return {"status": "binding_unavailable", "project_id": binding.get("project_id"), "paths": [],
                "gap": "Host project ID and complete registered project roots are required."}
    resolved = discover_binding(config.root, binding["project_id"], binding["other_project_roots"])
    client = AppServer(os.environ.get("CODEX_APP_RUNTIME_CLI_PATH", "codex"))
    try:
        discovered = classify_threads(resolved, list_threads(client, control=control))
        captured = collect_codex(binding["project_id"], [row["id"] for row in discovered["matched"]],
                                 config.memory_dir / "codex", control=control, client=client,
                                 project_binding=resolved)
    finally:
        client.close()
    root = config.root.resolve()
    paths = [Path(path).relative_to(root).as_posix() for path in captured["paths"]]
    def identifiers(rows):
        return [{"thread_id": row["thread"]["id"], "reason": row["reason"]} for row in rows]
    details = {"binding": resolved, "unresolved": identifiers(discovered["unresolved"]),
               "excluded": identifiers(discovered["excluded"]), "capture": captured}
    directory = config.memory_dir / "maintenance"
    directory.mkdir(parents=True, exist_ok=True)
    receipt = directory / f"codex-{uuid4().hex}.json"
    receipt.write_text(json.dumps(details, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "captured", "project_id": binding["project_id"], "discovered": len(discovered["matched"]),
            "unresolved": len(discovered["unresolved"]), "gaps": len(discovered["gaps"]) + len(captured["gaps"]),
            "receipt": str(receipt), "paths": paths}


def _activate(config):
    path = config.root / ".basepack/instructions.md"
    existing = path.read_text(encoding="utf-8")
    start, end = "<!-- basepack-memory:start -->", "<!-- basepack-memory:end -->"
    python = str(config.python).replace("'", "''")
    project_config = str(config.path).replace("'", "''")
    skill = Path(__file__).with_name("SKILL.md").resolve().as_posix()
    memory_dir = config.memory_dir.as_posix()
    section = f"""{start}
记忆已在本项目启用。每个新的 PowerShell 进程执行下面整段读取启动信息；客户端自动读取本项目配置指定的密码文件，无需手工加载凭据。

```powershell
$ErrorActionPreference = 'Stop'
$OutputEncoding = [Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = $OutputEncoding
$basepackPython = '{python}'
$basepackConfig = '{project_config}'
& $basepackPython -X utf8 -m basepack --config $basepackConfig memory brief --task '<当前任务>'
if ($LASTEXITCODE -ne 0) {{ throw "memory brief failed ($LASTEXITCODE)" }}
```

后续命令复用本进程的 `$basepackPython` 和 `$basepackConfig`；新进程重新执行整段。项目搬迁后更新本段配置绝对路径，或用新配置重新执行 `memory init` 刷新本段。

本项目数据库的 launcher 为 `{memory_dir}/serve.ps1`，cwd 为 `{memory_dir}`，日志为其中 `logs/surreal.stdout.log` 与 `logs/surreal.stderr.log`。先检查配置 endpoint 的 `/ready`；不可用时查日志，并由项目维护者显式启动该 launcher，以该目录为 cwd。保持同项目多聊天共用的进程，避免并行启动同一 store。首次准备、独立调用验证和故障处理见 [数据库部署](https://github.com/YS-Pan/basePack/blob/main/experiments/20261106-basepack/docs/administrator.md#项目-surrealdb)，原生导出、原件与 assets 的恢复集合见 [备份恢复](https://github.com/YS-Pan/basePack/blob/main/experiments/20261106-basepack/docs/memory.md#备份与恢复)。

`memory search` 未传 `--mode` 时采用当前配置 `memory.search_mode`；仅支持 `vector`（新项目默认）或 `hybrid`。`hybrid --literal` 优先返回路径、标题或正文的精确子串命中，`lexical_rank` 标明词法命中；无此字段的是语义补充。`vector --literal` 明确拒绝。显式 `--mode` 优先；旧 `text` 配置须改为 `vector` 或 `hybrid`，设施或兼容向量缺失保留原错。

直接保留 mandatory 信息；stale=true 的内容只作待核，不当作当前事实。brief、search 和 read 只读已发布知识及其依据快照。宿主支持可取消子任务与任务开始/完成事件时，预先分配任务唯一控制文件，默认异步运行 `memory maintain --control <任务唯一控制文件>`，不按当前任务文件缩小范围；它先维护全项目受管来源并完成机械变化。仅 `needs_semantic=true` 时，按返回 `worker` 的 `model`/`reasoning_effort` 设置宿主派工，给协调者一条英文启动句及 `worker.render_command`，由其执行并遵循 JSON 的 `prompt`。协调者持续接续收据中的待维护批次；业务完成时运行 `memory stop --control <同一文件>`，再取消协调者及其后代，不等待已获准提交的事务。Codex 宿主按随包 skill 刷新项目注册清单，缺失时报告采集缺口；缺少生命周期能力时说明自动维护不可用。多轮检索、筛选与重排前用同一命令前缀运行 `config ai --purpose retrieval` 解析项目档位。按 [记忆流程](<{skill}>) 执行。
{end}"""
    if start in existing or end in existing:
        if existing.count(start) != 1 or existing.count(end) != 1:
            raise ValueError("Invalid basepack memory entry markers in instructions.md")
        before, _, tail = existing.partition(start)
        closing = tail.index(end)
        after = tail[closing + len(end):]
        updated = before + section + after
    else:
        updated = existing.rstrip() + "\n\n" + section + "\n"
    path.write_text(updated, encoding="utf-8")
