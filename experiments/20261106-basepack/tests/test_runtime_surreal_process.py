import os
import sys
from time import monotonic, sleep
from types import SimpleNamespace
import venv

import pytest

from basepack.runtime import surreal_process


@pytest.mark.skipif(os.name != "nt", reason="uses Windows console process groups")
def test_graceful_stop_signals_only_one_owned_child(tmp_path, monkeypatch):
    sender_env = tmp_path / "sender-env"
    venv.create(sender_env, with_pip=False)
    native_python = sys._base_executable
    monkeypatch.setattr(surreal_process, "sys", SimpleNamespace(
        executable=str(sender_env / "Scripts" / "python.exe"), _base_executable=native_python,
    ))
    worker = """
from pathlib import Path
import signal
import sys
from time import sleep

state = Path(sys.argv[1])

def stop(*_):
    state.with_suffix(".stopped").touch()
    raise SystemExit(0)

signal.signal(signal.SIGBREAK, stop)
state.touch()
while True:
    sleep(0.05)
"""
    states = [tmp_path / "first", tmp_path / "second"]
    children = []
    with (tmp_path / "children.log").open("w", encoding="utf-8") as log:
        try:
            for state in states:
                children.append(surreal_process.launch_surreal(
                    [native_python, "-c", worker, str(state)], env=os.environ, log=log,
                ))
            deadline = monotonic() + 10
            while not all(state.exists() for state in states):
                assert all(child.poll() is None for child in children)
                assert monotonic() < deadline, "Workers did not install their Ctrl-Break handlers"
                sleep(0.05)

            first, second = children
            first.stop()
            assert states[0].with_suffix(".stopped").exists()
            assert second.poll() is None
            second.stop()
            assert states[1].with_suffix(".stopped").exists()
        finally:
            for child in children:
                if child.poll() is None:
                    child.kill()
                    child.wait(timeout=5)
