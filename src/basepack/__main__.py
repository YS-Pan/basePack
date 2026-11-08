import argparse
import json


def main():
    parser = argparse.ArgumentParser(prog="basepack")
    parser.add_argument("--config", help="Explicit project config path; no parent-directory search")
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="Connect a project using installed templates")
    init.add_argument("--project-root", required=True)
    init.add_argument("--machine-config", required=True)
    init.add_argument("--config-name", default="basepack.toml")
    config = sub.add_parser("config")
    config.add_subparsers(dest="config_action", required=True).add_parser("show")
    check = sub.add_parser("doctor", help="Read-only facility checks")
    check.add_argument("--facility", choices=["core", "embedding", "condor", "all"], default="all")
    args = parser.parse_args()
    if args.command == "init":
        from .setup import init_project
        result = {"project_config": str(init_project(args.project_root, args.machine_config, args.config_name))}
    else:
        if not args.config:
            parser.error("--config is required for this action")
        from .config import load_config, describe
        config = load_config(args.config)
        if args.command == "config":
            result = describe(config)
        elif args.command == "doctor":
            from .doctor import doctor
            result = doctor(config, args.facility)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
