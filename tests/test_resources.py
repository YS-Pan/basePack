import json
from copy import deepcopy
from dataclasses import replace
import os
from pathlib import Path
from datetime import datetime
import socket
import subprocess
import sys

import pytest

from basepack.resources.client import _descendants, _process_parents, _terminal_time


@pytest.fixture
def resource_client(tmp_path):
    from basepack.project.config import load_project_config
    from basepack.resources import ResourceClient
    from basepack.project.init import init_project

    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n[shared]\nstate_dir='state'\n"
                       "[htcondor]\nbin_dir='bin'\nconfig_file='native.conf'\n", encoding="utf-8")
    client = ResourceClient(load_project_config(init_project(tmp_path / "project", machine)))
    slot = {"Name": "slot1@local", "Machine": socket.gethostname().upper(),
            "MachineResources": "Cpus Memory Disk GPUs SiteGpuMiB",
            "TotalSlotCpus": 12, "TotalSlotMemory": 24576, "TotalSlotGPUs": 4,
            "TotalSlotDisk": 102400, "TotalSlotSiteGpuMiB": 7164,
            "Cpus": 0, "Memory": 0, "Disk": 51200, "GPUs": 0, "SiteGpuMiB": 0}
    client._ads = lambda *args: [slot]
    return client


def test_native_capacity_and_admission_distinguish_total_from_currently_available(resource_client):
    from basepack.resources import JobSpec

    capacity = resource_client.capacity()
    assert capacity["slots"][0]["total"] == {
        "cpus": 12, "memory_mib": 24576, "gpus": 4, "Disk": 102400, "SiteGpuMiB": 7164}
    assert capacity["slots"][0]["available"] == {
        "cpus": 0, "memory_mib": 0, "gpus": 0, "Disk": 51200, "SiteGpuMiB": 0}
    spec = JobSpec(executable=sys.executable, cwd=str(resource_client.config.root),
                   cpus=2, memory_mib=2048, gpu_memory_mib=4000)
    resource_client._admission(spec)
    for key, amount in (("cpus", 13), ("memory_mib", 24577)):
        with pytest.raises(ValueError, match="exceeds local Condor slot capacity"):
            resource_client._admission(JobSpec(**{**spec.__dict__, key: amount}))
    # The schedd owns GPU resource admission, including over-pool requests.
    resource_client._admission(JobSpec(**{**spec.__dict__, "gpu_memory_mib": 7165}))


def test_capacity_discovers_renamed_resources_without_client_changes(resource_client):
    slot = resource_client._ads()[0]
    slot["MachineResources"] = "Cpus, Memory, Disk, GPUs, RenamedMemory, Licenses"
    slot["TotalSlotRenamedMemory"], slot["RenamedMemory"] = 7164, 2164
    slot["TotalSlotLicenses"], slot["Licenses"] = 2, 1
    capacity = resource_client.capacity()["slots"][0]
    assert capacity["total"]["RenamedMemory"] == 7164
    assert capacity["available"]["RenamedMemory"] == 2164
    assert capacity["total"]["Licenses"] == 2
    assert capacity["available"]["Licenses"] == 1
    assert "SiteGpuMiB" not in capacity["total"]


@pytest.mark.parametrize("published", [{}, {"Swap": 512}, {"TotalSlotSwap": 1024}])
def test_capacity_omits_resources_without_published_total_and_available(resource_client, published):
    # Windows advertises Swap in MachineResources without publishing its amounts.
    slot = resource_client._ads()[0]
    slot["MachineResources"] += " Swap"
    slot.update(published)
    capacity = resource_client.capacity()["slots"][0]
    assert "Swap" not in capacity["total"]
    assert "Swap" not in capacity["available"]
    assert capacity["total"]["Disk"] == 102400
    assert capacity["total"]["SiteGpuMiB"] == 7164


def test_admission_requires_one_local_slot_to_fit_all_requested_resources(resource_client):
    from basepack.resources import JobSpec

    slot = resource_client._ads()[0]
    resource_client._ads = lambda *args: [
        slot | {"TotalSlotMemory": 1024},
        slot | {"Name": "slot2@local", "TotalSlotCpus": 1},
        slot | {"Machine": "another-computer"}]
    with pytest.raises(ValueError, match="exceeds local Condor slot capacity"):
        resource_client._admission(JobSpec(executable=sys.executable,
            cwd=str(resource_client.config.root), cpus=2, memory_mib=2048))


def test_cpu_submit_needs_no_gpu_attributes_and_gpu_submit_uses_official_fields(resource_client):
    from basepack.resources import JobSpec

    def command(name, *args, **kwargs):
        return subprocess.CompletedProcess(args, 0, stdout="123.0" if name == "condor_submit" else "", stderr="")

    resource_client._call = command
    gpu = resource_client.submit(JobSpec(executable=sys.executable, gpu_memory_mib=4000))
    gpu_submit = (Path(gpu["job_dir"]) / "job.sub").read_text(encoding=resource_client.encoding)
    assert "request_gpus = 1\n" in gpu_submit
    assert "gpus_minimum_memory = 4000 MB\n" in gpu_submit
    assert "request_GPUMemoryMiB" not in gpu_submit
    assert "BasePackBudget" not in gpu_submit
    assert "BasePackGpuBudget" not in gpu_submit

    slot = {key: value for key, value in resource_client._ads()[0].items()
            if "gpu" not in key.lower()}
    slot["MachineResources"] = "Cpus Memory Disk"
    resource_client._ads = lambda *args: [slot]
    cpu = resource_client.submit(JobSpec(executable=sys.executable))
    cpu_submit = (Path(cpu["job_dir"]) / "job.sub").read_text(encoding=resource_client.encoding)
    assert "request_gpus = 0\n" in cpu_submit
    assert "gpus_minimum_memory" not in cpu_submit
    assert resource_client.capacity()["slots"][0]["total"]["gpus"] == 0


def test_submit_reuses_relative_spec_in_each_project_without_changing_it(resource_client, tmp_path):
    from basepack.resources import JobSpec, ResourceClient

    first_root = resource_client.config.root
    second_root = tmp_path / "second project 中文"
    for root in (first_root, second_root):
        (root / "work").mkdir(parents=True)
    second = ResourceClient(replace(resource_client.config, root=second_root))
    second._ads = resource_client._ads
    for client in (resource_client, second):
        client._call = lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, stdout="123.0", stderr="")
    spec = JobSpec(executable=sys.executable, cwd="work", arguments=["", "中文"], environment={"VALUE": "text"})
    original = deepcopy(spec)
    for client in (resource_client, second):
        submitted = client.submit(spec)
        payload = json.loads(Path(submitted["payload"]).read_text(encoding="utf-8"))
        assert payload["spec"]["cwd"] == str((client.config.root / "work").resolve())
        assert spec == original


@pytest.mark.parametrize("failure", ["admission", "submit"])
def test_failed_submit_keeps_callers_spec_unchanged(resource_client, failure):
    from basepack.resources import JobSpec

    spec = JobSpec(executable=sys.executable, cwd=".", arguments=[""], environment={"VALUE": "text"})
    original = deepcopy(spec)

    def fail(*args, **kwargs):
        raise RuntimeError("original failure")

    if failure == "admission":
        resource_client._admission = fail
    else:
        resource_client._call = fail
        resource_client._ads = lambda *args: []
        resource_client._admission = lambda _: None
    with pytest.raises(RuntimeError, match="original failure"):
        resource_client.submit(spec)
    assert spec == original


@pytest.mark.parametrize("custom_resource", [None, "RenamedMemory"])
def test_standard_gpu_submission_does_not_depend_on_custom_resources(resource_client, custom_resource):
    from basepack.resources import JobSpec

    slot = resource_client._ads()[0]
    slot["MachineResources"] = "Cpus Memory Disk GPUs"
    del slot["TotalSlotSiteGpuMiB"], slot["SiteGpuMiB"]
    if custom_resource:
        slot["MachineResources"] += " " + custom_resource
        slot["TotalSlot" + custom_resource], slot[custom_resource] = 7164, 0
    resource_client._call = lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, stdout="124.0", stderr="")
    submitted = resource_client.submit(JobSpec(executable=sys.executable, gpu_memory_mib=4000))
    description = (Path(submitted["job_dir"]) / "job.sub").read_text(encoding=resource_client.encoding)
    assert "request_gpus = 1\n" in description
    assert "gpus_minimum_memory = 4000 MB\n" in description
    assert "request_GPUMemoryMiB" not in description
    assert {line.split(" = ")[0] for line in description.splitlines() if line.startswith("request_")} == {
        "request_cpus", "request_memory", "request_disk", "request_gpus"}
    assert resource_client.capacity()["slots"][0]["total"] == {
        "cpus": 12, "memory_mib": 24576, "gpus": 4, "Disk": 102400,
        **({custom_resource: 7164} if custom_resource else {})}


def test_native_empty_query_means_no_matches_but_invalid_json_is_an_error():
    from basepack.resources import ResourceClient

    client = ResourceClient.__new__(ResourceClient)
    client._call = lambda *args: subprocess.CompletedProcess(args, 0, stdout="", stderr="")
    assert client._ads("condor_q", "14294.0") == []
    client._call = lambda *args: subprocess.CompletedProcess(args, 0, stdout="invalid", stderr="")
    with pytest.raises(json.JSONDecodeError):
        client._ads("condor_q", "14294.0")


def test_uncertain_submit_keeps_original_error_without_submitting_twice(tmp_path):
    from basepack.project.config import load_project_config
    from basepack.resources import JobSpec, ResourceClient
    from basepack.project.init import init_project

    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n[shared]\nstate_dir='state'\n"
                       "[htcondor]\nbin_dir='bin'\nconfig_file='native.conf'\n", encoding="utf-8")
    config = load_project_config(init_project(tmp_path / "project", machine))
    client = ResourceClient(config)
    client._admission = lambda _: None
    calls = []

    def command(name, *args, **kwargs):
        calls.append(name)
        if name == "condor_submit":
            raise subprocess.TimeoutExpired("condor_submit", 25, stderr="original submit response lost")

    client._call = command
    client._ads = lambda *args: [{"ClusterId": 123, "ProcId": 0}]
    submitted = client.submit(JobSpec(executable=sys.executable))
    assert calls.count("condor_submit") == 1
    assert submitted["job_id"] == "123.0"
    assert "timed out" in submitted["submit_response_error"]
    assert "original submit response lost" in submitted["submit_response_error"]
    saved = json.loads((Path(submitted["job_dir"]) / "submission.json").read_text(encoding="utf-8"))
    assert saved["submit_response_error"] == submitted["submit_response_error"]


def test_worker_preserves_windows_argv_and_application_exit(tmp_path):
    """The Condor Windows argv conversion dropped empty arguments in the real probe."""
    values = ["two spaces 中文", "single'quote", 'double"quote', "", "trailing\\", "$(literal)"]
    output = tmp_path / "actual.json"
    receipt = tmp_path / "worker.json"
    code = "import json,sys; from pathlib import Path; Path(sys.argv[1]).write_text(json.dumps(sys.argv[2:]),encoding='utf-8'); sys.exit(7)"
    payload = tmp_path / "payload.json"
    payload.write_text(json.dumps({"executable": sys.executable,
                                   "arguments": ["-c", code, str(output), *values],
                                   "worker_receipt": str(receipt)}, ensure_ascii=False), encoding="utf-8")
    result = subprocess.run([sys.executable, "-m", "basepack.resources.worker", str(payload)])
    assert result.returncode == 7
    assert json.loads(output.read_text(encoding="utf-8")) == values
    assert json.loads(receipt.read_text(encoding="utf-8"))["exit_code"] == 7


def test_process_snapshot_sees_real_child():
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        snapshot = _process_parents()
        assert snapshot[child.pid] == os.getpid()
        assert child.pid in _descendants({os.getpid()}, snapshot)
    finally:
        child.terminate()
        child.wait(timeout=5)
    assert child.pid not in _process_parents()


def test_removed_job_uses_native_abort_time_instead_of_stale_status(tmp_path):
    log = tmp_path / "events.log"
    log.write_text("000 (14277.000.000) 2026-11-08 10:23:48 Job submitted\n...\n"
                   "009 (14277.000.000) 2026-11-08 10:24:40 Job was aborted\n...\n"
                   "009 (14278.000.000) 2026-11-08 10:25:40 Another job\n", encoding="utf-8")
    submitted = int(datetime.fromisoformat("2026-11-08 10:23:48").timestamp())
    ad = {"ClusterId": 14277, "ProcId": 0, "QDate": submitted,
          "EnteredCurrentStatus": submitted, "UserLog": str(log)}
    assert _terminal_time(ad, "utf-8") - submitted == 52
    log.unlink()
    assert _terminal_time(ad, "utf-8") is None
