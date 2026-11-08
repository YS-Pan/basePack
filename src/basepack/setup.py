"""Initialize a project from installed package resources."""

from importlib.resources import files
import json
import os
from pathlib import Path
from string import Template
import sys


def template(name: str) -> str:
    return files("basepack").joinpath("templates", name).read_text(encoding="utf-8")


def init_project(root: str | Path, machine_config: str | Path, config_name: str = "basepack.toml") -> Path:
    root = Path(root).resolve()
    machine_config = Path(machine_config).resolve(strict=True)
    config = (root / config_name).resolve()
    if not config.is_relative_to(root):
        raise ValueError("Project config must be inside the project root")
    if config.exists():
        raise FileExistsError(config)
    root.mkdir(parents=True, exist_ok=True)
    config.parent.mkdir(parents=True, exist_ok=True)
    text = Template(template("project.toml")).substitute(
        python=json.dumps(sys.executable),
        machine_config=json.dumps(str(machine_config)),
        root=json.dumps(Path(os.path.relpath(root, config.parent)).as_posix()),
    )
    config.write_text(text, encoding="utf-8")
    agents = root / "AGENTS.md"
    existing = agents.read_text(encoding="utf-8") if agents.exists() else ""
    snippet = Template(template("agents-snippet.md")).substitute(config=config.relative_to(root).as_posix())
    start, end = "<!-- basepack:start -->", "<!-- basepack:end -->"
    if start in existing:
        before, _, tail = existing.partition(start)
        _, _, after = tail.partition(end)
        existing = before + snippet.rstrip() + after
    else:
        existing = existing.rstrip() + "\n\n" + snippet
    agents.write_text(existing.lstrip("\n"), encoding="utf-8")
    ignore = root / ".gitignore"
    lines = ignore.read_text(encoding="utf-8").splitlines() if ignore.exists() else []
    for entry in ("/" + config.relative_to(root).as_posix(), "/.basepack/"):
        if entry not in lines:
            lines.append(entry)
    ignore.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return config
