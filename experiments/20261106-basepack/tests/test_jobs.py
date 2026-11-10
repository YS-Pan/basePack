import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from datetime import datetime
import socket
import subprocess
import sys

import pytest

from basepack.jobs.client import _terminal_time


@pytest.fixture
def resource_client(tmp_path):
    from basepack.project.config import load_project_config
    from basepack.jobs import CondorClient
    from basepack.project.init import init_project

    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n[shared]\nstate_dir='state'\n"
                       "[htcondor]\nbin_dir='bin'\nconfig_file='native.conf'\n", encoding="utf-8")
    client = CondorClient(load_project_config(init_project(tmp_path / "project", machine)))
    slot = {"Name": "slot1@local", "Machine": socket.gethostname().upper(),
            "MachineResources": "Cpus Memory Disk GPUs SiteGpuMiB",
            "TotalSlotCpus": 12, "TotalSlotMemory": 24576, "TotalSlotGPUs": 4,
            "TotalSlotDisk": 102400, "TotalSlotSiteGpuMiB": 7164,
            "Cpus": 0, "Memory": 0, "Disk": 51200, "GPUs": 0, "SiteGpuMiB": 0}
    client._ads = lambda *args: [slot]
    return client


def test_capacity_reports_total_and_currently_available_without_admission(resource_client):
    from basepack.jobs import JobSpec

    capacity = resource_client.capacity()
    assert capacity["slots"][0]["total"] == {
        "cpus": 12, "memory_mib": 24576, "gpus": 4, "Disk": 102400, "SiteGpuMiB": 7164}
    assert capacity["slots"][0]["available"] == {
        "cpus": 0, "memory_mib": 0, "gpus": 0, "Disk": 51200, "SiteGpuMiB": 0}
    spec = JobSpec(executable=sys.executable, cwd=str(resource_client.config.root),
                   cpus=2, memory_mib=2048, gpu_memory_mib=4000)
    resource_client._ads = lambda *args: pytest.fail("submission must leave capacity matching to Condor")
    resource_client._check_request(spec)
    for key, amount in (("cpus", 13), ("memory_mib", 24577)):
        resource_client._check_request(JobSpec(**{**spec.__dict__, key: amount}))
    resource_client._check_request(JobSpec(**{**spec.__dict__, "gpu_memory_mib": 7165}))


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


@pytest.mark.parametrize("field", ["cpus", "memory_mib", "disk_mib", "queue_timeout", "run_timeout"])
def test_request_requires_positive_resource_and_time_values(resource_client, field):
    from basepack.jobs import JobSpec

    with pytest.raises(ValueError, match=f"{field} must be positive"):
        resource_client._check_request(JobSpec(executable=sys.executable, **{field: 0}))


@pytest.mark.parametrize("field", ["TotalSlotCpus", "Cpus", "TotalSlotMemory", "Memory", "MachineResources", "TotalSlotGPUs", "GPUs"])
def test_capacity_preserves_missing_required_field_errors(resource_client, field):
    del resource_client._ads()[0][field]
    with pytest.raises(KeyError, match=field):
        resource_client.capacity()


def test_cpu_submit_needs_no_gpu_attributes_and_gpu_submit_uses_official_fields(resource_client):
    from basepack.jobs import JobSpec

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
    assert resource_client.capacity()["slots"][0]["available"]["gpus"] == 0


def test_submit_reuses_relative_spec_in_each_project_without_changing_it(resource_client, tmp_path):
    from basepack.jobs import JobSpec, CondorClient

    first_root = resource_client.config.root
    second_root = tmp_path / "second project 中文"
    for root in (first_root, second_root):
        (root / "work").mkdir(parents=True)
    second = CondorClient(replace(resource_client.config, root=second_root))
    second._ads = resource_client._ads
    for client in (resource_client, second):
        client._call = lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, stdout="123.0", stderr="")
    spec = JobSpec(executable=sys.executable, cwd="work", arguments=["", "中文"], environment={"VALUE": "text"})
    original = deepcopy(spec)
    for client in (resource_client, second):
        submitted = client.submit(spec)
        payload = json.loads(Path(submitted["payload"]).read_text(encoding="utf-8"))
        assert set(payload) == {"submission_id", "spec", "worker_receipt"}
        assert payload["spec"]["cwd"] == str((client.config.root / "work").resolve())
        assert "basepack.jobs.worker" in (Path(submitted["job_dir"]) / "job.sub").read_text(encoding=client.encoding)
        assert spec == original


@pytest.mark.parametrize("failure", ["admission", "submit"])
def test_failed_submit_keeps_callers_spec_unchanged(resource_client, failure):
    from basepack.jobs import JobSpec

    spec = JobSpec(executable=sys.executable, cwd=".", arguments=[""], environment={"VALUE": "text"})
    original = deepcopy(spec)

    def fail(*args, **kwargs):
        raise RuntimeError("original failure")

    if failure == "admission":
        resource_client._check_request = fail
    else:
        resource_client._call = fail
        resource_client._ads = lambda *args: []
        resource_client._check_request = lambda _: None
    with pytest.raises(RuntimeError, match="original failure"):
        resource_client.submit(spec)
    assert spec == original


@pytest.mark.parametrize("custom_resource", [None, "RenamedMemory"])
def test_standard_gpu_submission_does_not_depend_on_custom_resources(resource_client, custom_resource):
    from basepack.jobs import JobSpec

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
    from basepack.jobs import CondorClient

    client = CondorClient.__new__(CondorClient)
    client._call = lambda *args: subprocess.CompletedProcess(args, 0, stdout="", stderr="")
    assert client._ads("condor_q", "14294.0") == []
    client._call = lambda *args: subprocess.CompletedProcess(args, 0, stdout="invalid", stderr="")
    with pytest.raises(json.JSONDecodeError):
        client._ads("condor_q", "14294.0")


def test_uncertain_submit_keeps_original_error_without_submitting_twice(tmp_path):
    from basepack.project.config import load_project_config
    from basepack.jobs import JobSpec, CondorClient
    from basepack.project.init import init_project

    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n[shared]\nstate_dir='state'\n"
                       "[htcondor]\nbin_dir='bin'\nconfig_file='native.conf'\n", encoding="utf-8")
    config = load_project_config(init_project(tmp_path / "project", machine))
    client = CondorClient(config)
    client._check_request = lambda _: None
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


@pytest.mark.parametrize("lookup_failure", [None, RuntimeError("lookup failed")])
def test_uncertain_submit_preserves_submit_error_when_token_recovery_fails(resource_client, lookup_failure):
    from basepack.jobs import JobSpec

    original = subprocess.TimeoutExpired("condor_submit", 25, stderr="lost submit response")
    calls = []

    def command(name, *args, **kwargs):
        calls.append(name)
        raise original

    def ads(*args):
        if lookup_failure:
            raise lookup_failure
        return []

    resource_client._call = command
    resource_client._ads = ads
    with pytest.raises(subprocess.TimeoutExpired) as caught:
        resource_client.submit(JobSpec(executable=sys.executable))
    assert caught.value is original
    assert caught.value.__cause__ is lookup_failure
    assert calls == ["condor_submit"]


def test_uncertain_submit_recovers_from_history_by_same_token(resource_client):
    from basepack.jobs import JobSpec

    calls, queries = [], []

    def command(name, *args, **kwargs):
        calls.append(name)
        if name == "condor_submit":
            raise RuntimeError("submit response lost")

    def ads(name, *args):
        queries.append((name, args))
        return [] if name == "condor_q" else [{"ClusterId": 124, "ProcId": 0}]

    resource_client._call = command
    resource_client._ads = ads
    submitted = resource_client.submit(JobSpec(executable=sys.executable))
    assert submitted["job_id"] == "124.0"
    assert calls == ["condor_submit", "condor_reschedule"]
    assert [name for name, _ in queries] == ["condor_q", "condor_history"]
    assert all(f'BasePackSubmissionId == "{submitted["submission_id"]}"' in args for _, args in queries)


def test_worker_preserves_windows_argv_and_application_exit(tmp_path):
    """The Condor Windows argv conversion dropped empty arguments in the real probe."""
    values = ["two spaces 中文", "single'quote", 'double"quote', "", "trailing\\", "$(literal)"]
    output = tmp_path / "actual.json"
    receipt = tmp_path / "worker.json"
    code = "import json,sys; from pathlib import Path; Path(sys.argv[1]).write_text(json.dumps(sys.argv[2:]),encoding='utf-8'); sys.exit(7)"
    payload = tmp_path / "payload.json"
    payload.write_text(json.dumps({"spec": {"executable": sys.executable,
                                   "arguments": ["-c", code, str(output), *values]},
                                   "worker_receipt": str(receipt)}, ensure_ascii=False), encoding="utf-8")
    result = subprocess.run([sys.executable, "-m", "basepack.jobs.worker", str(payload)])
    assert result.returncode == 7
    assert json.loads(output.read_text(encoding="utf-8")) == values
    assert json.loads(receipt.read_text(encoding="utf-8"))["exit_code"] == 7


@pytest.mark.parametrize("exit_code,returned,success", [(0, True, True), (7, True, False), (0, False, False)])
def test_terminal_status_checks_application_exit_and_returned_outputs(resource_client, tmp_path, exit_code, returned, success):
    payload = tmp_path / "payload.json"
    payload.write_text(json.dumps({"spec": {"cwd": str(tmp_path), "transfer_outputs": ["result.txt"]}}), encoding="utf-8")
    if returned:
        (tmp_path / "result.txt").write_text("result", encoding="utf-8")
    ad = {"JobStatus": 4, "QDate": 10, "CompletionDate": 20, "ExitCode": exit_code,
          "BasePackPayload": str(payload)}
    resource_client._ad = lambda _: (ad, True)
    result = resource_client.status("123.0")
    assert result["terminal"]
    assert result["exit_code"] == exit_code
    assert result["success"] is success
    assert result["missing_outputs"] == ([] if returned else [str(tmp_path / "result.txt")])


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
