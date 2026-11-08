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
    embed.add_argument("--request-id")
    embed.add_argument("--tokens-only", action="store_true")
    embed.add_argument("--output", type=Path)
    service = subparsers.add_parser("embedding", help="administer the independent machine service")
    actions = service.add_subparsers(dest="embedding_action", required=True)
    actions.add_parser("status")
    actions.add_parser("stop")
    actions.add_parser("broker", help="run the machine launcher in the foreground outside Condor")


def dispatch(args, config):
    client = EmbeddingClient(config)
    if args.command == "embedding":
        if args.embedding_action == "status":
            return client.status()
        if args.embedding_action == "stop":
            return client.stop_service()
        from .broker import serve
        serve(config.machine)
        return {"stopped": True}
    if args.inputs:
        inputs = json.loads(args.inputs.read_text(encoding="utf-8"))
    elif args.image:
        inputs = [{"image": str(Path(args.image).resolve())}]
        if args.caption:
            inputs[0]["text"] = args.caption
    else:
        inputs = args.text
    result = client.embed(inputs, timeout=args.timeout, request_id=args.request_id, tokens_only=args.tokens_only)
    if args.output:
        args.output.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        return {"pid": result["pid"], "model_identity": result["model_identity"],
                "count": len(result["inputs"]), "output": str(args.output.resolve())}
    return result
