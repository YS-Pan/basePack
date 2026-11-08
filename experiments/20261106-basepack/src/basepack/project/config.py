"""The only resolver for project and machine configuration paths."""

from dataclasses import dataclass
from importlib import metadata
import json
from pathlib import Path
import sys
import tomllib


def _read(path: Path, schema_version: int) -> dict:
    with path.open("rb") as stream:
        raw = tomllib.load(stream)
    if raw["schema_version"] != schema_version:
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
class ProjectConfig:
    path: Path
    python: Path
    root: Path
    raw: dict
    machine: MachineConfig

    @property
    def machine_config(self) -> Path:
        return self.machine.path

    def data_path(self, section: str, key: str) -> Path:
        target = (self.root / self.raw[section][key]).resolve()
        if not target.is_relative_to(self.root / ".basepack"):
            raise ValueError(f"Project data directory must be inside {self.root / '.basepack'}: {target}")
        return target

    @property
    def memory_dir(self) -> Path:
        return self.data_path("memory", "data_dir")

    @property
    def jobs_dir(self) -> Path:
        return self.data_path("jobs", "jobs_dir")


def load_machine_config(path: str | Path) -> MachineConfig:
    path = Path(path).resolve()
    return MachineConfig(path, _read(path, 1))


def load_project_config(path: str | Path) -> ProjectConfig:
    path = Path(path).resolve()
    raw = _read(path, 2)
    python = _absolute(raw["runtime"]["python"], "runtime.python")
    machine_path = _absolute(raw["runtime"]["machine_config"], "runtime.machine_config")
    root = (path.parent / raw["project"]["root"]).resolve()
    return ProjectConfig(path, python, root, raw, load_machine_config(machine_path))


def installation() -> dict:
    dist = metadata.distribution("basepack")
    direct = dist.read_text("direct_url.json")
    editable = bool(direct and json.loads(direct).get("dir_info", {}).get("editable"))
    return {
        "version": dist.version,
        "mode": "editable" if editable else "wheel",
        "package_dir": str(Path(__file__).resolve().parents[1]),
        "python": sys.executable,
    }


def describe(config: ProjectConfig) -> dict:
    machine = config.machine
    paths = {}
    if "shared" in machine.raw:
        paths["state_dir"] = str(machine.state_dir)
    for section, keys in {"embedding": ["model_root"], "htcondor": ["bin_dir", "config_file"]}.items():
        if section in machine.raw:
            paths[section] = {key: str(machine.path_value(section, key)) for key in keys}
    result = {
        "installation": installation(),
        "project_config": str(config.path),
        "machine_config": str(config.machine_config),
        "runtime_python": str(config.python),
        "project_root": str(config.root),
        "machine_paths": paths,
    }
    if "memory" in config.raw:
        result["memory_dir"] = str(config.memory_dir)
    if "jobs" in config.raw:
        result["jobs_dir"] = str(config.jobs_dir)
    return result
