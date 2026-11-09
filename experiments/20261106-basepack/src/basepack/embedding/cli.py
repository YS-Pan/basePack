"""CLI registration kept separate from model imports."""
import json
from pathlib import Path

from .client import EmbeddingClient


def register_commands(subparsers):
    embed = subparsers.add_parser("embed", help="use the machine-shared text/image model")
    source = embed.add_mutually_exclusive_group(required=True)
    source.add_argument("--text", action="append", help="text input; repeat for a batch")
    source.add_argument("--image", help="one local image, optionally with --caption")
    source.add_argument("--inputs", type=Path, help="UTF-8 JSON array of strings or {text, image}")
    embed.add_argument("--caption")
    embed.add_argument("--timeout", type=float, default=600)
    embed.add_argument("--output", type=Path)
    service = subparsers.add_parser("embedding", help="administer the independent machine service")
    service.add_argument("--machine-config", required=True, type=Path)
    actions = service.add_subparsers(dest="embedding_action", required=True)
    actions.add_parser("status")
    actions.add_parser("stop")
    actions.add_parser("serve", help="run LitServe in the foreground; production is hosted by Shawl")


def dispatch(args, config=None):
    if args.command == "embedding":
        from basepack.project.config import load_machine_config
        from .admin import status, stop
        machine = load_machine_config(args.machine_config)
        if args.embedding_action == "status":
            return status(machine), 0
        if args.embedding_action == "stop":
            return stop(machine), 0
        from .service import serve
        serve(machine)
        return {"stopped": True}, 0
    client = EmbeddingClient(config.machine)
    if args.inputs:
        inputs = json.loads(args.inputs.read_text(encoding="utf-8"))
    elif args.image:
        inputs = [{"image": str(Path(args.image).resolve())}]
        if args.caption:
            inputs[0]["text"] = args.caption
    else:
        inputs = args.text
    result = client.embed(inputs, timeout=args.timeout)
    if args.output:
        args.output.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        return {"pid": result["pid"], "embedding_identity": result["embedding_identity"],
                "count": len(result["vectors"]), "output": str(args.output.resolve())}, 0
    return result, 0
