import ctypes
import os
import subprocess
import sys
from unittest.mock import Mock

import pytest

from basepack.runtime import job


@pytest.fixture
def kernel(monkeypatch):
    kernel = Mock()
    kernel.CreateJobObjectW.return_value = 42
    kernel.GetCurrentProcess.return_value = -1
    monkeypatch.setattr(job, "_job_api", lambda: kernel)
    return kernel


def test_install_process_job_retains_noninheritable_handle(kernel):
    job.install_process_job()

    kernel.CreateJobObjectW.assert_called_once_with(None, None)
    handle, kind, limits, size = kernel.SetInformationJobObject.call_args.args
    assert handle == 42
    assert kind == 9  # JobObjectExtendedLimitInformation
    assert size == ctypes.sizeof(job._ExtendedLimitInformation)
    assert limits._obj.BasicLimitInformation.LimitFlags == 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    kernel.AssignProcessToJobObject.assert_called_once_with(42, -1)
    kernel.CloseHandle.assert_not_called()


@pytest.mark.parametrize("api", ["SetInformationJobObject", "AssignProcessToJobObject"])
def test_failed_job_setup_closes_handle_and_preserves_error(kernel, api):
    error = OSError("native error")
    getattr(kernel, api).side_effect = error

    with pytest.raises(OSError) as caught:
        job.install_process_job()

    assert caught.value is error
    kernel.CloseHandle.assert_called_once_with(42)


@pytest.mark.skipif(os.name != "nt", reason="uses Windows process handles")
def test_terminating_launcher_terminates_its_process_tree():
    import _winapi

    program = """
import os, subprocess, sys
from basepack.runtime.job import install_process_job

install_process_job()
worker = "import os, time; print(os.getpid(), flush=True); time.sleep(20)"
child = subprocess.Popen([sys.executable, "-c", worker], stdout=subprocess.PIPE, text=True)
print(os.getpid(), child.pid, child.stdout.readline().strip(), flush=True)
sys.stdin.buffer.read(1)
"""
    with subprocess.Popen(
        [sys.executable, "-c", program],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    ) as launcher:
        handles = []
        try:
            ready = launcher.stdout.readline()
            if not ready:
                pytest.fail(launcher.communicate(timeout=5)[1])
            for pid in set(map(int, ready.split())) - {launcher.pid}:
                # SYNCHRONIZE | PROCESS_TERMINATE, including for cleanup on failure.
                handles.append(_winapi.OpenProcess(_winapi.SYNCHRONIZE | 0x0001, False, pid))
            assert handles
            launcher.kill()
            launcher.wait(timeout=5)
            for handle in handles:
                assert _winapi.WaitForSingleObject(handle, 5000) == _winapi.WAIT_OBJECT_0
        finally:
            if launcher.poll() is None:
                launcher.kill()
            for handle in handles:
                try:
                    if _winapi.WaitForSingleObject(handle, 0) != _winapi.WAIT_OBJECT_0:
                        _winapi.TerminateProcess(handle, 1)
                finally:
                    _winapi.CloseHandle(handle)
