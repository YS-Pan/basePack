import json
from pathlib import Path

from .client import CondorClient
from .submit import JobSpec


def register_commands(subparsers):
    jobs = subparsers.add_parser("jobs", help="Run local heavy jobs through HTCondor")
    commands = jobs.add_subparsers(dest="jobs_action", required=True)
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
    commands.add_parser("capacity", help="Show local Condor slot capacity and available resources")


def dispatch(args, config):
    action = args.jobs_action
    client = CondorClient(config)
    if action == "capacity":
        result = client.capacity()
    elif action in ("run", "submit"):
        spec = JobSpec(**json.loads(Path(args.spec).read_text(encoding="utf-8")))
        result = getattr(client, action)(spec)
    elif action == "wait":
        result = client.wait(args.job_id, timeout=args.timeout)
    elif action == "status":
        result = client.status(args.job_id, analyze=args.analyze)
    else:
        result = client.cancel(args.job_id)
    if action == "run":
        return result, 0 if result.get("success") and result.get("cleanup_confirmed") else 1
    if action == "cancel":
        return result, 0 if result["cleanup_confirmed"] else 1
    return result, 0
