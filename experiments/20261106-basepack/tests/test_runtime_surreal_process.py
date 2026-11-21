import os
import sys
from time import monotonic, sleep

import pytest

from basepack.runtime.surreal_process import launch_surreal


@pytest.mark.skipif(os.name != "nt", reason="uses Windows console process groups")
def test_graceful_stop_signals_only_one_owned_child(tmp_path):
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
                children.append(launch_surreal([sys.executable, "-c", worker, str(state)], env=os.environ, log=log))
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
