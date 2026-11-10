import argparse
import json
import sys


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="basepack")
    parser.add_argument("--config", help="Explicit project config path; no parent-directory search")
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="Connect a project using installed templates")
    init.add_argument("--project-root", required=True)
    init.add_argument("--machine-config", required=True)
    init.add_argument("--config-name", default=".basepack/config.toml")
    init.add_argument("--codex-project-id", default="", help="Host-provided Codex project ID")
    init.add_argument("--codex-other-project-root", action="append", default=[],
                      help="A different Codex project's registered root; repeat as needed")
    init.add_argument("--codex-registry-complete", action="store_true",
                      help="The host supplied its complete other-project root list")
    config = sub.add_parser("config")
    config_commands = config.add_subparsers(dest="config_action", required=True)
    config_commands.add_parser("show")
    ai = config_commands.add_parser("ai", help="Resolve project AI settings for host dispatch")
    selection = ai.add_mutually_exclusive_group()
    selection.add_argument("--purpose", choices=["task", "retrieval"], default="task")
    selection.add_argument("--tier", choices=["tier1", "tier2", "tier3", "tier4"])
    check = sub.add_parser("doctor", help="Read-only facility checks")
    check.add_argument("--facility", choices=["core", "embedding", "condor", "all"], default="core")
    from .embedding.cli import register_commands as embedding_commands
    embedding_commands(sub)
    from .jobs.cli import register_commands as job_commands
    job_commands(sub)
    from .memory.cli import register_commands as memory_commands
    memory_commands(sub)
    args = parser.parse_args()
    exit_code = 0
    if args.command == "init":
        from .project.init import init_project
        result = {"project_config": str(init_project(
            args.project_root, args.machine_config, args.config_name,
            codex_project_id=args.codex_project_id, codex_other_project_roots=args.codex_other_project_root,
            codex_registry_complete=args.codex_registry_complete))}
    elif args.command == "embedding":
        from .embedding.cli import dispatch
        result, exit_code = dispatch(args)
    elif args.command == "memory" and args.memory_action in ("guide", "rank", "stop"):
        from .memory.cli import dispatch
        result, exit_code = dispatch(args, None)
    else:
        if not args.config:
            parser.error("--config is required for this action")
        from .project.config import load_project_config, describe
        config = load_project_config(args.config)
        if args.command == "config":
            result = (describe(config) if args.config_action == "show"
                      else config.resolve_ai(purpose=args.purpose, tier=args.tier))
        elif args.command == "doctor":
            from .project.doctor import doctor
            result = doctor(config, args.facility)
        elif args.command == "embed":
            from .embedding.cli import dispatch
            result, exit_code = dispatch(args, config)
        elif args.command == "jobs":
            from .jobs.cli import dispatch
            result, exit_code = dispatch(args, config)
        elif args.command == "memory":
            from .memory.cli import dispatch
            result, exit_code = dispatch(args, config)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
