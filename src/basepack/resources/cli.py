import json
from pathlib import Path

from .client import JobSpec, ResourceClient, budget_config


def register_commands(subparsers):
    resources = subparsers.add_parser("resources", help="Run local heavy jobs through HTCondor")
    commands = resources.add_subparsers(dest="resource_action", required=True)
    for action in ("run", "submit"):
        command = commands.add_parser(action)
        command.add_argument("--spec", required=True, help="UTF-8 JSON JobSpec")
    for action in ("status", "wait", "cancel"):
        command = commands.add_parser(action)
        command.add_argument("job_id")
        if action == "wait":
            command.add_argument("--timeout", type=float, default=300, help="Observation only; leaves the job running")
        if action == "status":
            command.add_argument("--analyze", action="store_true")
    commands.add_parser("budget-config", help="Generate the Condor config fragment from machine TOML")


def handle(args, config):
    action = args.resource_action
    if action == "budget-config":
        return budget_config(config.machine)
    client = ResourceClient(config)
    if action in ("run", "submit"):
        spec = JobSpec(**json.loads(Path(args.spec).read_text(encoding="utf-8")))
        return getattr(client, action)(spec)
    if action == "wait":
        return client.wait(args.job_id, timeout=args.timeout)
    if action == "status":
        return client.status(args.job_id, analyze=args.analyze)
    return client.cancel(args.job_id)
