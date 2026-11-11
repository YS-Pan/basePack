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
                 config_name: str = ".basepack/config.toml", *, codex_project_id: str = "",
                 codex_other_project_roots: list[str] | None = None,
                 codex_registry_complete: bool = False) -> Path:
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
        codex_project_id=json.dumps(codex_project_id, ensure_ascii=False),
        codex_other_project_roots=json.dumps([str(Path(path).resolve())
                                            for path in codex_other_project_roots or []], ensure_ascii=False),
        codex_registry_complete=str(codex_registry_complete).lower(),
    )
    _write_project_entry(root, config, Path(sys.executable))
    config.write_text(text, encoding="utf-8")
    return config


def _write_project_entry(root: Path, config: Path, python: Path) -> None:
    """Write the project's detailed instructions and host entry."""
    refresh_project_entry(root, config, python)
    ignore = root / ".gitignore"
    lines = ignore.read_text(encoding="utf-8").splitlines() if ignore.exists() else []
    if "/.basepack/" not in lines:
        lines.append("/.basepack/")
    ignore.write_text("\n".join(lines) + "\n", encoding="utf-8")


def replace_managed_block(existing: bytes, section: str, *, name: str, path: str) -> bytes:
    """Replace one ordered marker pair while retaining every outside byte."""
    start = f"<!-- {name}:start -->".encode()
    end = f"<!-- {name}:end -->".encode()
    replacement = section.strip().encode("utf-8")
    if start in existing or end in existing:
        if (existing.count(start) != 1 or existing.count(end) != 1
                or existing.index(start) >= existing.index(end)):
            raise ValueError(f"Invalid {name} entry markers in {path}")
        opening, closing = existing.index(start), existing.index(end) + len(end)
        return existing[:opening] + replacement + existing[closing:]
    separator = b"" if not existing else (b"\n" if existing.endswith(b"\n") else b"\n\n")
    return existing + separator + replacement + b"\n"


def refresh_project_entry(root: Path, config: Path, python: Path, *,
                          memory_enabled: bool = False, memory_dir: Path | None = None) -> None:
    """Refresh the same managed entries during project init and memory init."""
    root, config, python = Path(root).resolve(), Path(config).resolve(), Path(python)
    agents = root / "AGENTS.md"
    instructions = root / ".basepack" / "instructions.md"
    state = "enabled" if memory_enabled else "disabled"
    snippet = template("agents-snippet.md").replace("$memory_instructions", template(f"agents-{state}.md").strip())
    host_entry = replace_managed_block(agents.read_bytes() if agents.exists() else b"", snippet,
                                       name="basepack", path="AGENTS.md")
    existing = instructions.read_bytes() if instructions.exists() else Template(template("instructions.md")).substitute(
        python=str(python).replace("'", "''"),
        config=config.relative_to(root).as_posix().replace("'", "''"),
    ).encode("utf-8")
    from basepack.memory import __file__ as memory_module
    skill = Path(memory_module).with_name("SKILL.md").resolve().as_posix()
    section = template(f"memory-{state}.md").replace(
        "<!-- basepack-memory:end -->", template("tools.md") + "\n<!-- basepack-memory:end -->")
    section = Template(section).substitute(
        python=str(python).replace("'", "''"),
        config=str(config).replace("'", "''"),
        skill=skill,
        memory_dir=(memory_dir or root / ".basepack/memory").as_posix(),
    )
    details = replace_managed_block(existing, section, name="basepack-memory", path="instructions.md")
    # Validate both boundaries before either file changes.
    instructions.parent.mkdir(parents=True, exist_ok=True)
    instructions.write_bytes(details)
    agents.write_bytes(host_entry)
