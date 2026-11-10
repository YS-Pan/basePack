"""One-time memory walkthrough in an initialized, disposable project."""

import argparse
import json
import os
import subprocess
from uuid import uuid4

from basepack.project.config import load_project_config


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--config", required=True)
args = parser.parse_args()
project = load_project_config(args.config)
cli = [str(project.python), "-X", "utf8", "-m", "basepack", "--config", str(project.path), "memory"]
env = {**os.environ, "PYTHONUTF8": "1"}


def run(*arguments):
    subprocess.run([*cli, *arguments], check=True, env=env)


# Exclusive creation protects any existing business file with this name.
source_path = "memory-example.md"
with (project.root / source_path).open("x", encoding="utf-8", newline="\n") as stream:
    stream.write("# 试用说明\n## 约定\n试用问题 A-17 留在开发记录。\n项目数据库按项目隔离。\n")

work = project.memory_dir / ("example-" + uuid4().hex)
work.mkdir(parents=True)
reading_path, batch_path = work / "reading.json", work / "batch.json"
run("prepare", "--paths", source_path, "--output", str(reading_path))
reading = json.loads(reading_path.read_text(encoding="utf-8"))
source = reading["sources"][0]
print(source["numbered_text"], flush=True)
batch = {
    "expected": reading["expected"],
    "sources": [{"path": source["path"], "revision": source["revision"]}],
    "members": [
        {"id": "example-file", "kind": "file", "path": source_path, "parent": None,
         "start_line": 1, "end_line": 4, "title": "试用说明",
         "text": "试用问题 A-17 留在开发记录；项目数据库按项目隔离。", "evidence": ["member:`example-chunk`"]},
        {"id": "example-section", "kind": "section", "path": source_path, "parent": "member:`example-file`",
         "start_line": 2, "end_line": 4, "title": "约定",
         "text": "保留试用记录，并使用独立项目数据库。", "evidence": ["member:`example-chunk`"]},
        {"id": "example-chunk", "kind": "chunk", "path": source_path, "parent": "member:`example-section`",
         "start_line": 3, "end_line": 4, "title": "试用与隔离约定", "evidence": []},
    ],
}
batch_path.write_text(json.dumps(batch, ensure_ascii=False, indent=2), encoding="utf-8")
run("apply", "--batch", str(batch_path))
run("search", "--text", "A-17", "--mode", "hybrid", "--literal")
run("search", "--text", source_path, "--mode", "hybrid", "--literal")
run("read", "member:`example-chunk`")
run("neighbors", "member:`example-section`")
print(f"UTF-8 reading and batch: {work}", flush=True)
