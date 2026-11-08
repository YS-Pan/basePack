"""Explicit schema-1 project migration; callers first drain their old jobs."""

from datetime import date, datetime, time
import json
import os
from pathlib import Path
import re
import shutil
import tomllib
import uuid

from .config import ProjectConfig, _absolute, _read, load_machine_config
from .init import _write_project_entry


def _key(value):
    return value if re.fullmatch(r"[A-Za-z0-9_-]+", value) else json.dumps(value)


def _value(value):
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (date, datetime, time)):
        return value.isoformat()
    if isinstance(value, list):
        return "[" + ", ".join(_value(item) for item in value) + "]"
    return "{ " + ", ".join(f"{_key(key)} = {_value(item)}" for key, item in value.items()) + " }"


def _toml(raw):
    lines = [f"{_key(key)} = {_value(value)}" for key, value in raw.items() if not isinstance(value, dict)]
    for section, values in raw.items():
        if isinstance(values, dict):
            lines.extend(["", f"[{_key(section)}]",
                          *[f"{_key(key)} = {_value(value)}" for key, value in values.items()]])
    return "\n".join(lines) + "\n"


def _mapped_path(path: Path, moves):
    for source, target in moves:
        if path.is_relative_to(source):
            return target / path.relative_to(source)
    return path


def _rewrite_receipt(value, moves):
    """Rewrite generated path fields, leaving business argv and environment intact."""
    if isinstance(value, list):
        return [_rewrite_receipt(item, moves) for item in value]
    if not isinstance(value, dict):
        return value
    result = {}
    for key, item in value.items():
        if key in {"worker_receipt", "cwd", "job_dir", "payload", "stdout", "stderr", "event_log", "python"} and isinstance(item, str):
            path = Path(item)
            mapped = _mapped_path(path.resolve(), moves) if path.is_absolute() else path
            result[key] = str(mapped) if path.is_absolute() and mapped != path.resolve() else item
        elif key in {"arguments", "environment"}:
            result[key] = item
        else:
            result[key] = _rewrite_receipt(item, moves)
    return result


def migrate_project(source_config: str | Path, config_name: str = ".basepack/config.toml") -> dict:
    source_config = Path(source_config).resolve(strict=True)
    raw = _read(source_config, 1)
    python = _absolute(raw["runtime"]["python"], "runtime.python")
    machine = load_machine_config(_absolute(raw["runtime"]["machine_config"], "runtime.machine_config"))
    root = (source_config.parent / raw["project"]["root"]).resolve(strict=True)
    managed = root / ".basepack"
    config = (root / config_name).resolve()
    if not source_config.is_relative_to(root):
        raise ValueError("Old project config must be inside its project root")
    if config == managed or not config.is_relative_to(managed):
        raise ValueError("Project config must be inside the project's .basepack directory")
    if config.exists() and config != source_config:
        raise FileExistsError(config)
    if "jobs" in raw:
        raise ValueError("Schema-1 project must use [resources], not [jobs]")

    moves = []
    old_data = []
    for section, key, name in (("memory", "data_dir", "memory"), ("resources", "jobs_dir", "jobs")):
        if section not in raw:
            continue
        source = (root / raw[section][key]).resolve()
        if source in (root, managed) or not source.is_relative_to(root):
            raise ValueError(f"Old project data directory must be inside the project and below its root: {source}")
        target = source if source.is_relative_to(managed) else managed / name
        if source.exists() and not source.is_dir():
            raise NotADirectoryError(source)
        if target != source:
            if target.exists():
                raise FileExistsError(target)
            if source_config.is_relative_to(source):
                raise ValueError(f"Old config cannot be inside a data directory being moved: {source_config}")
            moves.append((source, target))
        old_data.append(source)
        raw[section][key] = target.relative_to(root).as_posix()
    for index, path in enumerate(old_data):
        if any(path.is_relative_to(other) or other.is_relative_to(path) for other in old_data[index + 1:]):
            raise ValueError("Project memory and jobs data directories must not overlap")
    for source, target in moves:
        if config.is_relative_to(target) and (source / config.relative_to(target)).exists():
            raise FileExistsError(config)
    raw["schema_version"] = 2
    raw["project"]["root"] = Path(os.path.relpath(root, config.parent)).as_posix()
    if "resources" in raw:
        raw["jobs"] = raw.pop("resources")
    text = _toml(raw)
    planned = ProjectConfig(config, python, root, tomllib.loads(text), machine)
    for section, attribute in (("memory", "memory_dir"), ("jobs", "jobs_dir")):
        if section in raw:
            getattr(planned, attribute)

    changed_receipts = []
    if moves:
        for directory in old_data:
            if directory.exists():
                for path in directory.rglob("*.json"):
                    if path.name in {"basepack-job.json", "submission.json", "worker.json"}:
                        if not path.resolve().is_relative_to(root):
                            raise ValueError(f"Generated receipt must be inside its project: {path}")
                        original = json.loads(path.read_text(encoding="utf-8"))
                        changed = _rewrite_receipt(original, moves)
                        if changed != original:
                            changed_receipts.append((path, changed))

    backup = managed / "migration" / uuid.uuid4().hex
    backup.mkdir(parents=True)
    originals = [source_config, root / "AGENTS.md", root / ".gitignore", managed / "instructions.md",
                 *[path for path, _ in changed_receipts]]
    saved = []
    for path in originals:
        if path.exists():
            destination = backup / "files" / path.relative_to(root)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
            saved.append(str(path))
    result = {"project_config": str(config), "project_root": str(root), "source_config": str(source_config),
              "backup_dir": str(backup), "backup_files": saved,
              "data_moves": [{"source": str(source), "target": str(target), "source_existed": source.exists()}
                             for source, target in moves],
              "rewritten_receipts": [str(_mapped_path(path, moves)) for path, _ in changed_receipts],
              "history_note": "Completed Condor history retains original BasePackPayload paths; use this mapping and backups when those paths moved."}
    (backup / "mapping.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    for source, target in moves:
        if source.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(target))
    for path, changed in changed_receipts:
        _mapped_path(path, moves).write_text(json.dumps(changed, ensure_ascii=False, indent=2), encoding="utf-8")
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(text, encoding="utf-8")
    _write_project_entry(root, config, python)
    if source_config != config:
        source_config.unlink()
    return result
