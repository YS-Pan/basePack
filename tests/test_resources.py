import json
import os
from pathlib import Path
from datetime import datetime
import subprocess
import sys

import pytest

from basepack.resources.client import _descendants, _process_parents, _terminal_time


def test_native_empty_query_means_no_matches_but_invalid_json_is_an_error():
    from basepack.resources import ResourceClient

    client = ResourceClient.__new__(ResourceClient)
    client._call = lambda *args: subprocess.CompletedProcess(args, 0, stdout="", stderr="")
    assert client._ads("condor_q", "14294.0") == []
    client._call = lambda *args: subprocess.CompletedProcess(args, 0, stdout="invalid", stderr="")
    with pytest.raises(json.JSONDecodeError):
        client._ads("condor_q", "14294.0")


def test_uncertain_submit_keeps_original_error_without_submitting_twice(tmp_path):
    from basepack.config import load_config
    from basepack.resources import JobSpec, ResourceClient
    from basepack.setup import init_project

    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n[shared]\nstate_dir='state'\n"
                       "[htcondor]\nbin_dir='bin'\nconfig_file='native.conf'\n", encoding="utf-8")
    config = load_config(init_project(tmp_path / "project", machine))
    client = ResourceClient(config)
    client._admission = lambda _: {"budget_id": "test", "gpu_memory_mib": 0}
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
