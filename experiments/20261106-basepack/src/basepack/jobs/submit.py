"""Job specification, Condor field encoding and submission materials."""

from dataclasses import asdict, dataclass, field, replace
import json
from pathlib import Path
import re
import socket
import uuid


def _line(value: str) -> str:
    if any(character in value for character in ("\r", "\n", "\x00")) or "$(" in value:
        raise ValueError(f"Unsupported submit-field characters: {value!r}")
    return value


def arguments(values: list[str]) -> str:
    """Condor V2 syntax; only used for the small launcher argument list."""
    return '"' + " ".join("'" + _line(value).replace("'", "''").replace('"', '""') + "'"
                           for value in values) + '"'


def environment(values: dict[str, str]) -> str:
    """Condor environment V2 syntax, independent of Windows shell syntax."""
    for key in values:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            raise ValueError(f"Invalid environment variable name: {key!r}")
    return arguments([f"{key}={value}" for key, value in values.items()])


def path_field(value: str | Path) -> str:
    return _line(str(value).replace("\\", "/"))


def transfer_list(values: list[str]) -> str:
    if any("," in value for value in values):
        raise ValueError("Condor transfer paths cannot contain commas")
    return ",".join(path_field(value) for value in values)


@dataclass
class JobSpec:
    executable: str
    arguments: list[str] = field(default_factory=list)
    cwd: str = "."
    environment: dict[str, str] = field(default_factory=dict)
    cpus: int = 1
    memory_mib: int = 512
    disk_mib: int = 64
    gpu_memory_mib: int = 0
    queue_timeout: int = 300
    run_timeout: int = 600
    transfer_inputs: list[str] = field(default_factory=list)
    transfer_outputs: list[str] = field(default_factory=list)


def normalize_spec(config, spec: JobSpec) -> JobSpec:
    normalized = replace(spec, cwd=str((config.root / spec.cwd).resolve()))
    if not Path(normalized.executable).is_absolute():
        raise ValueError("Job executable must be an explicit absolute path")
    return normalized


def prepare_submission(config, spec: JobSpec, encoding: str):
    """Write one normalized spec and its standard Condor submission description."""
    cwd = Path(spec.cwd)
    token = uuid.uuid4().hex
    folder = config.jobs_dir / token
    folder.mkdir(parents=True)
    transfer = bool(spec.transfer_inputs or spec.transfer_outputs)
    payload = folder / "basepack-job.json"
    metadata = {"submission_id": token, "spec": asdict(spec)}
    payload.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    env = {"OMP_NUM_THREADS": str(spec.cpus), "MKL_NUM_THREADS": str(spec.cpus),
           "OPENBLAS_NUM_THREADS": str(spec.cpus), "NUMEXPR_NUM_THREADS": str(spec.cpus),
           **spec.environment}
    if any(key.upper() == "CUDA_VISIBLE_DEVICES" for key in env):
        raise ValueError("CUDA_VISIBLE_DEVICES belongs to Condor's device allocation")
    requirement = f'TARGET.Machine == {json.dumps(socket.gethostname())}'
    lines = [
        "universe = vanilla", f"executable = {path_field(config.python)}",
        "transfer_executable = False", "getenv = False",
        "arguments = " + arguments(["-I", "-m", "basepack.jobs.worker", payload.name if transfer else str(payload)]),
        f"environment = {environment(env)}", f"initialdir = {path_field(cwd)}",
        f"output = {path_field(folder/'stdout.txt')}", f"error = {path_field(folder/'stderr.txt')}",
        f"log = {path_field(folder/'events.log')}", f"request_cpus = {spec.cpus}",
        f"request_memory = {spec.memory_mib} MB", f"request_disk = {spec.disk_mib} MB",
        f"request_gpus = {int(bool(spec.gpu_memory_mib))}", f"requirements = {requirement}",
        f'+BasePackSubmissionId = "{token}"', f'+BasePackPayload = {json.dumps(payload.as_posix(), ensure_ascii=False)}',
        f"allowed_execute_duration = {spec.run_timeout}",
        "periodic_remove = "
        f"(JobStatus == 1 && time() - QDate >= {spec.queue_timeout}) || "
        f"(JobStatus == 2 && JobCurrentStartExecutingDate > 0 && time() - JobCurrentStartExecutingDate >= {spec.run_timeout}) || "
        "(JobStatus == 5 && member(HoldReasonCode, {46,47}))",
        "notification = Never", "on_exit_remove = True",
        f"should_transfer_files = {'YES' if transfer else 'NO'}",
    ]
    if spec.gpu_memory_mib:
        lines.append(f"gpus_minimum_memory = {spec.gpu_memory_mib} MB")
    if transfer:
        inputs = [str(payload), *[str((cwd / path).resolve()) for path in spec.transfer_inputs]]
        for output in spec.transfer_outputs:
            if Path(output).is_absolute() or ".." in Path(output).parts:
                raise ValueError(f"Transfer output must be relative to scratch: {output}")
        lines.extend(["when_to_transfer_output = ON_EXIT", "transfer_input_files = " + transfer_list(inputs),
                      "transfer_output_files = " + transfer_list(spec.transfer_outputs)])
    submit = folder / "job.sub"
    submit.write_text("\n".join([*lines, "queue 1", ""]), encoding=encoding)
    return token, folder, payload, submit
