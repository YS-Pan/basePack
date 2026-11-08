import json
import os
from pathlib import Path
import subprocess
import sys

from basepack.resources.client import _descendants, _process_parents


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
