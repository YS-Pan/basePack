"""Project memory actions; SurrealDB's own tools handle server and backup work."""

import json
from pathlib import Path


def register_commands(subparsers):
    memory = subparsers.add_parser("memory", help="Project-local multilevel memory")
    commands = memory.add_subparsers(dest="memory_action", required=True)
    actions = {name: commands.add_parser(name) for name in
               ("init", "guide", "sources", "prepare", "apply", "stop", "embed", "search", "read", "neighbors", "brief", "changes", "rank")}
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
    actions["rank"].add_argument("--input", required=True, help="Read candidates with agent scores")
    actions["rank"].add_argument("--budget", type=int, default=6000, help="Returned text character budget")
    for command in actions.values():
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
                result = memory.vector_search(args.text, scope=args.scope, limit=args.limit, timeout=args.timeout,
                                              include_coverage=True)
            else:
                result = memory.hybrid_search(args.text, scope=args.scope, limit=args.limit,
                                              timeout=args.timeout, literal=args.literal, include_coverage=True)
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
    project_config = str(config.path).replace("'", "''")
    skill = Path(__file__).with_name("SKILL.md").resolve().as_posix()
    section = f"""{start}
记忆已在本项目启用。每个新的 PowerShell 进程先执行下面整段：从当前配置读取实际目录、凭据文件和 password_env，加载到当前进程后读取启动信息；无需部署 shell 的变量、函数或工作目录。密码原文只从本地文件读取，不输出。

```powershell
$ErrorActionPreference = 'Stop'
$OutputEncoding = [Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = $OutputEncoding
$basepackPython = '{python}'
$basepackConfig = '{project_config}'
$basepackJson = & $basepackPython -X utf8 -m basepack --config $basepackConfig config show
if ($LASTEXITCODE -ne 0) {{ throw "Cannot load project config ($LASTEXITCODE)" }}
$basepackInfo = $basepackJson | ConvertFrom-Json
$basepackPython = $basepackInfo.runtime_python
[Environment]::SetEnvironmentVariable($basepackInfo.memory.password_env, [IO.File]::ReadAllText($basepackInfo.memory_password_file), 'Process')
& $basepackPython -X utf8 -m basepack --config $basepackConfig memory brief --task '<当前任务>'
if ($LASTEXITCODE -ne 0) {{ throw "memory brief failed ($LASTEXITCODE)" }}
```

后续命令复用本进程的 `$basepackPython` 和 `$basepackConfig`；新进程重新执行整段。密码文件由可选 `memory.password_file` 指定（相对项目根或绝对路径），省略时为当前 `memory_dir/password.txt`。项目搬迁后更新本段配置绝对路径，或用新配置重新执行 `memory init` 刷新本段。

本项目数据库的 launcher 为 `$basepackInfo.memory_dir/serve.ps1`，cwd 为该 `memory_dir`，日志为其中 `logs/surreal.stdout.log` 与 `logs/surreal.stderr.log`。先检查配置 endpoint 的 `/ready`；不可用时查日志，并由项目维护者显式启动该 launcher，以该目录为 cwd。保持同项目多聊天共用的进程，避免并行启动同一 store。首次准备、独立调用验证和故障处理见 [数据库部署](https://github.com/YS-Pan/basePack/blob/main/experiments/20261106-basepack/docs/administrator.md#项目-surrealdb)，原生导出、原件与 assets 的恢复集合见 [备份恢复](https://github.com/YS-Pan/basePack/blob/main/experiments/20261106-basepack/docs/memory.md#备份与恢复)。

`memory search` 未传 `--mode` 时采用当前配置 `memory.search_mode`；仅支持 `vector`（新项目默认）或 `hybrid`。`hybrid --literal` 优先返回路径、标题或正文的精确子串命中，`lexical_rank` 标明词法命中；无此字段的是语义补充。`vector --literal` 明确拒绝。显式 `--mode` 优先；旧 `text` 配置须改为 `vector` 或 `hybrid`，设施或兼容向量缺失保留原错。

直接保留 mandatory 信息；stale=true 的内容只作待核，不当作当前事实。brief、search 和 read 读取已发布知识及其依据快照，不扫描或维护来源。宿主支持可取消子任务与任务开始/完成事件时，并行启动低优先级维护 worker，业务完成时停止该任务的维护；缺少这些能力时说明自动维护不可用。多轮检索、筛选与重排前用同一命令前缀运行 `config ai --purpose retrieval` 解析项目档位。按 [记忆流程](<{skill}>) 执行。
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
