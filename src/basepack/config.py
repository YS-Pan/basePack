"""The only resolver for project and machine configuration paths."""

from dataclasses import dataclass
from importlib import metadata
import json
from pathlib import Path
import sys
import tomllib


def _read(path: Path) -> dict:
    with path.open("rb") as stream:
        raw = tomllib.load(stream)
    if raw["schema_version"] != 1:
        raise ValueError(f"Unsupported schema_version in {path}")
    return raw


def _absolute(value: str, field: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        raise ValueError(f"{field} must be absolute: {value}")
    return path.resolve()


@dataclass(frozen=True)
class MachineConfig:
    path: Path
    raw: dict

    def path_value(self, section: str, key: str) -> Path:
        return (self.path.parent / self.raw[section][key]).resolve()

    @property
    def state_dir(self) -> Path:
        return self.path_value("shared", "state_dir")


@dataclass(frozen=True)
class Config:
    path: Path
    python: Path
    machine_config: Path
    root: Path
    memory_dir: Path
    jobs_dir: Path
    machine: MachineConfig


def load_machine(path: str | Path) -> MachineConfig:
    path = Path(path).resolve()
    return MachineConfig(path, _read(path))


def load_config(path: str | Path) -> Config:
    path = Path(path).resolve()
    raw = _read(path)
    python = _absolute(raw["runtime"]["python"], "runtime.python")
    machine_path = _absolute(raw["runtime"]["machine_config"], "runtime.machine_config")
    root = (path.parent / raw["project"]["root"]).resolve()
    memory = (root / raw["memory"]["data_dir"]).resolve()
    jobs = (root / raw["resources"]["jobs_dir"]).resolve()
    for target in (memory, jobs):
        if not target.is_relative_to(root):
            raise ValueError(f"Project data directory must be inside {root}: {target}")
    return Config(path, python, machine_path, root, memory, jobs, load_machine(machine_path))


def installation() -> dict:
    dist = metadata.distribution("basepack")
    direct = dist.read_text("direct_url.json")
    editable = bool(direct and json.loads(direct).get("dir_info", {}).get("editable"))
    return {
        "version": dist.version,
        "mode": "editable" if editable else "wheel",
        "package_dir": str(Path(__file__).resolve().parent),
        "python": sys.executable,
    }


def describe(config: Config) -> dict:
    machine = config.machine
    paths = {"state_dir": str(machine.state_dir)}
    for section, keys in {"embedding": ["model_root"], "htcondor": ["bin_dir", "config_file"]}.items():
        if section in machine.raw:
            paths[section] = {key: str(machine.path_value(section, key)) for key in keys}
    return {
        "installation": installation(),
        "project_config": str(config.path),
        "machine_config": str(config.machine_config),
        "runtime_python": str(config.python),
        "project_root": str(config.root),
        "memory_dir": str(config.memory_dir),
        "jobs_dir": str(config.jobs_dir),
        "machine_paths": paths,
        "budget": machine.raw.get("budget"),
    }
