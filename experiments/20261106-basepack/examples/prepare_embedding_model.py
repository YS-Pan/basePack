"""Prepare the pinned model with the official hf CLI, then record local bytes."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


MODEL = "Qwen/Qwen3-VL-Embedding-2B"
REVISION = "9f2f7e710d6d81056aa5c0a4f04764fec6bb7bda"


def prepare(model_root: Path, hf: str = "hf") -> Path:
    model_dir = model_root / "model"
    common = [MODEL, "--revision", REVISION, "--local-dir", str(model_dir)]
    subprocess.run([hf, "download", *common], check=True)
    subprocess.run([hf, "cache", "verify", *common,
                    "--fail-on-missing-files", "--fail-on-extra-files"], check=True)
    files = []
    for path in sorted(model_dir.rglob("*")):
        relative = path.relative_to(model_dir)
        if not path.is_file() or ".cache" in relative.parts or relative.as_posix() == ".gitattributes":
            continue
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        files.append({"path": path.relative_to(model_root).as_posix(),
                      "bytes": path.stat().st_size, "sha256": digest})
    if not files:
        raise ValueError(f"No model files in {model_dir}")
    manifest = {"model": MODEL, "hf_revision": REVISION, "files": files}
    lock = model_root / "model.lock.json"
    lock.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return lock


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model_root", type=Path, help="A new stable directory outside the repository")
    parser.add_argument("--hf", default="hf", help="Path to the official hf executable")
    args = parser.parse_args()
    print(prepare(args.model_root.resolve(), args.hf))
