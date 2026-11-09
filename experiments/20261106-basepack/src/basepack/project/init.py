"""Initialize a project from installed package resources."""

from importlib.resources import files
import json
import os
from pathlib import Path
from string import Template
import sys
from uuid import uuid4


def template(name: str) -> str:
    return files("basepack.project").joinpath("templates", name).read_text(encoding="utf-8")


def init_project(root: str | Path, machine_config: str | Path,
                 config_name: str = ".basepack/config.toml") -> Path:
    root = Path(root).resolve()
    machine_config = Path(machine_config).resolve(strict=True)
    config = (root / config_name).resolve()
    managed = root / ".basepack"
    if config == managed or not config.is_relative_to(managed):
        raise ValueError("Project config must be inside the project's .basepack directory")
    instructions = managed / "instructions.md"
    if config == instructions:
        raise ValueError("Project config must differ from .basepack/instructions.md")
    if config.exists():
        raise FileExistsError(config)
    if instructions.exists():
        raise FileExistsError(instructions)
    root.mkdir(parents=True, exist_ok=True)
    config.parent.mkdir(parents=True, exist_ok=True)
    text = Template(template("project.toml")).substitute(
        python=json.dumps(sys.executable, ensure_ascii=False),
        machine_config=json.dumps(str(machine_config), ensure_ascii=False),
        root=json.dumps(Path(os.path.relpath(root, config.parent)).as_posix(), ensure_ascii=False),
        memory_project_id=str(uuid4()),
    )
    _write_project_entry(root, config, Path(sys.executable))
    config.write_text(text, encoding="utf-8")
    return config


def _write_project_entry(root: Path, config: Path, python: Path) -> None:
    """Write the project's detailed instructions and host entry."""
    agents = root / "AGENTS.md"
    existing = agents.read_text(encoding="utf-8") if agents.exists() else ""
    snippet = template("agents-snippet.md")
    start, end = "<!-- basepack:start -->", "<!-- basepack:end -->"
    if start in existing or end in existing:
        before, _, tail = existing.partition(start)
        closing = tail.index(end)
        if existing.count(start) != 1 or existing.count(end) != 1:
            raise ValueError("Duplicate basepack entry markers in AGENTS.md")
        after = tail[closing + len(end):]
        existing = before + snippet.rstrip() + after
    else:
        existing = existing.rstrip() + "\n\n" + snippet
    instructions = root / ".basepack" / "instructions.md"
    instructions.write_text(Template(template("instructions.md")).substitute(
        python=str(python).replace("'", "''"),
        config=config.relative_to(root).as_posix().replace("'", "''"),
    ), encoding="utf-8")
    agents.write_text(existing.lstrip("\n"), encoding="utf-8")
    ignore = root / ".gitignore"
    lines = ignore.read_text(encoding="utf-8").splitlines() if ignore.exists() else []
    if "/.basepack/" not in lines:
        lines.append("/.basepack/")
    ignore.write_text("\n".join(lines) + "\n", encoding="utf-8")
