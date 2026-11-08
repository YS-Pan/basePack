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
    migrate = sub.add_parser("migrate", help="Explicitly migrate a schema 1 project after draining its jobs")
    migrate.add_argument("--from-config", required=True)
    migrate.add_argument("--config-name", default=".basepack/config.toml")
    config = sub.add_parser("config")
    config.add_subparsers(dest="config_action", required=True).add_parser("show")
    check = sub.add_parser("doctor", help="Read-only facility checks")
    check.add_argument("--facility", choices=["core", "embedding", "condor", "all"], default="all")
    from .embedding.cli import register_commands as embedding_commands
    embedding_commands(sub)
    from .jobs.cli import register_commands as job_commands
    job_commands(sub)
    args = parser.parse_args()
    exit_code = 0
    if args.command == "init":
        from .project.init import init_project
        result = {"project_config": str(init_project(args.project_root, args.machine_config, args.config_name))}
    elif args.command == "migrate":
        from .project.migrate import migrate_project
        result = migrate_project(args.from_config, args.config_name)
    elif args.command == "embedding":
        from .embedding.cli import dispatch
        result, exit_code = dispatch(args)
    else:
        if not args.config:
            parser.error("--config is required for this action")
        from .project.config import load_project_config, describe
        config = load_project_config(args.config)
        if args.command == "config":
            result = describe(config)
        elif args.command == "doctor":
            from .project.doctor import doctor
            result = doctor(config, args.facility)
        elif args.command == "embed":
            from .embedding.cli import dispatch
            result, exit_code = dispatch(args, config)
        elif args.command == "jobs":
            from .jobs.cli import dispatch
            result, exit_code = dispatch(args, config)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
