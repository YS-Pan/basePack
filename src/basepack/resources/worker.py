"""Keep application argv intact across HTCondor's Windows argument conversion."""

import json
import os
from pathlib import Path
import subprocess
import sys
import time


def main():
    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    child = subprocess.Popen([payload["executable"], *payload["arguments"]])
    receipt = {
        "pid": os.getpid(), "child_pid": child.pid, "started": time.time(),
        "python": sys.executable, "cwd": os.getcwd(),
        "environment": {key: value for key, value in os.environ.items()
                        if key in ("CUDA_VISIBLE_DEVICES", "_CONDOR_SLOT") or "THREAD" in key},
    }
    path = Path(payload["worker_receipt"])
    def save():
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(receipt, ensure_ascii=False), encoding="utf-8")
        temporary.replace(path)
    save()
    receipt.update(exit_code=child.wait(), finished=time.time())
    save()
    raise SystemExit(receipt["exit_code"])


if __name__ == "__main__":
    main()
