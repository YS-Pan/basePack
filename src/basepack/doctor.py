"""Read-only checks, selected by facility."""

import os
from pathlib import Path
import shutil
import subprocess

from .config import Config, describe


def doctor(config: Config, facility: str = "all") -> dict:
    result = describe(config)
    checks = {}
    for name, path in {"python": config.python, "project_root": config.root,
                       "package": Path(__file__).parent, "templates": Path(__file__).parent / "templates"}.items():
        if not path.exists():
            raise FileNotFoundError(path)
        checks[name] = str(path)
    actual = subprocess.check_output([str(config.python), "-c", "import basepack;print(basepack.__file__)"], text=True).strip()
    checks["configured_python_package"] = actual
    if facility in ("embedding", "all"):
        model = config.machine.path_value("embedding", "model_root")
        if not model.is_dir():
            raise FileNotFoundError(model)
        for name in ("model.lock.json", "model/config.json"):
            if not (model / name).is_file():
                raise FileNotFoundError(model / name)
        checks["model_root"] = str(model)
        smi = shutil.which("nvidia-smi")
        if smi:
            checks["gpu"] = subprocess.check_output([smi, "--query-gpu=name,memory.total,compute_mode", "--format=csv,noheader"], text=True, timeout=15).strip()
    if facility in ("condor", "all"):
        machine = config.machine
        native = machine.path_value("htcondor", "config_file")
        if not native.is_file():
            raise FileNotFoundError(native)
        env = os.environ | {"CONDOR_CONFIG": str(native)}
        for command, args in {"condor_version": [], "condor_status": ["-json"], "condor_q": ["-json"]}.items():
            exe = machine.path_value("htcondor", "bin_dir") / (command + (".exe" if os.name == "nt" else ""))
            checks[command] = subprocess.check_output([str(exe), *args], env=env, text=True, timeout=20).strip()
    result["checks"] = checks
    result["scope"] = "read-only; inference and real job execution are separate acceptance checks"
    return result
