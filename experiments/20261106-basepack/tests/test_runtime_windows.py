import base64
import json
import os
from pathlib import Path
import re
import subprocess

import pytest

from basepack.runtime import windows


pytestmark = pytest.mark.skipif(os.name != "nt", reason="uses Windows PowerShell")

NAME = "BasePack.User.Memory.00000000-0000-0000-0000-000000000000"
ROOT = Path(r"D:\中文 project's scratch & work")
EXE = ROOT / "client" / "pythonw.exe"
ARGS = ["-m", "basepack", "--config", str(ROOT / "project config.toml"), 'a"b', ""]


def test_task_definition_is_data_and_command_is_fixed(monkeypatch):
    def run(command, **kwargs):
        assert command[1:4] == ["-NoProfile", "-NonInteractive", "-Command"]
        encoded = re.search(r"FromBase64String\('([^']+)'\)", command[4])[1]
        assert base64.b64decode(encoded).decode("utf-16le") == windows._TASK_PROGRAM
        assert kwargs["creationflags"] == subprocess.CREATE_NO_WINDOW
        assert json.loads(kwargs["input"]) == {
            "operation": "register",
            "name": NAME,
            "executable": str(EXE),
            "working_directory": str(ROOT),
            "arguments": subprocess.list2cmdline(ARGS),
            "at_logon": True,
        }
        return subprocess.CompletedProcess(command, 0, '{"status":"registered"}', "")

    monkeypatch.setattr(windows.subprocess, "run", run)
    assert windows.register_task(NAME, EXE, ARGS, ROOT, at_logon=True) == {"status": "registered"}


@pytest.fixture
def scheduler(monkeypatch):
    """Use real PowerShell with a fake task service in place of the COM object."""
    program = windows._TASK_PROGRAM

    def install(overrides=""):
        fake = r"""
class FakeCollection {
    [int] $Count
    [object[]] $Values
    FakeCollection([object[]] $values) {
        $this.Values = $values
        $this.Count = $values.Count
    }
    [object] Item([int] $index) { return $this.Values[$index - 1] }
}
$fakeAction = [pscustomobject]@{
    Type = 0
    Path = $request.executable
    Arguments = $request.arguments
    WorkingDirectory = $request.working_directory
}
$fakePrincipal = [pscustomobject]@{ UserId = $sid; LogonType = 3; RunLevel = 0 }
$fakeTask = [pscustomobject]@{
    State = 3
    Enabled = $true
    StateAfterStop = 3
    LastTaskResult = 267011
    Definition = [pscustomobject]@{
        Actions = [FakeCollection]::new(@($fakeAction))
        Triggers = [FakeCollection]::new(@())
        Principal = $fakePrincipal
        Settings = [pscustomobject]$settings
    }
}
$fakeTask | Add-Member ScriptMethod Run { param($parameters); $this.State = 4 }
$fakeTask | Add-Member ScriptMethod Stop { param($flags); $this.State = $this.StateAfterStop }
$fakeFolder = [pscustomobject]@{ Task = $fakeTask; LookupError = 0 }
$fakeFolder | Add-Member ScriptMethod GetTask {
    param($name)
    if ($this.LookupError) {
        throw [Runtime.InteropServices.COMException]::new('Native task lookup', $this.LookupError)
    }
    return $this.Task
}
$fakeFolder | Add-Member ScriptMethod DeleteTask { param($name, $flags); $this.Task = $null }
$scheduler = [pscustomobject]@{ Folder = $fakeFolder }
$scheduler | Add-Member ScriptMethod Connect {}
$scheduler | Add-Member ScriptMethod GetFolder { param($path); return $this.Folder }
"""
        marker = "$scheduler = New-Object -ComObject 'Schedule.Service'"
        assert program.count(marker) == 1
        monkeypatch.setattr(windows, "_TASK_PROGRAM", program.replace(marker, fake + overrides))

    return install


def operate(action):
    return windows.task_operation(action, NAME, EXE, ARGS, ROOT)


@pytest.mark.parametrize("native,state", [(1, "disabled"), (2, "queued"), (3, "stopped"), (4, "running")])
def test_status_uses_native_state(scheduler, native, state):
    scheduler(f"$fakeTask.State = {native}")
    assert operate("status") == {
        "task_name": NAME, "status": state, "at_logon": False, "last_task_result": 267011,
    }


def test_missing_and_denied_lookup_have_distinct_outcomes(scheduler):
    scheduler("$fakeFolder.LookupError = 0x80070002")
    assert operate("status") == {"task_name": NAME, "status": "unregistered"}
    with pytest.raises(RuntimeError, match="is unregistered"):
        operate("start")
    scheduler("$fakeFolder.LookupError = 0x80070005")
    with pytest.raises(RuntimeError, match="Native task lookup"):
        operate("status")


@pytest.mark.parametrize("override,operation", [
    ("$fakeAction.Arguments += ' changed'", "start"),
    ("$fakeAction.WorkingDirectory += ' changed'", "stop"),
    ("$fakePrincipal.UserId = 'S-1-5-18'", "unregister"),
    ("$fakePrincipal.UserId = 'no-account-80c4df709cc14e7eb421ac823bda2970'", "unregister"),
    ("$fakePrincipal.RunLevel = 1", "status"),
])
def test_changed_binding_blocks_task_management(scheduler, override, operation):
    scheduler(override)
    with pytest.raises(RuntimeError, match="different BasePack action or user principal"):
        operate(operation)


def test_principal_and_trigger_accept_local_name_for_same_sid(scheduler):
    scheduler(r"""
$account = ($identity.Name -split '\\')[-1]
$fakePrincipal.UserId = $account
$logon = [pscustomobject]@{ Type = 9; Enabled = $true; UserId = $account }
$fakeTask.Definition.Triggers = [FakeCollection]::new(@($logon))
""")
    assert windows.register_task(NAME, EXE, ARGS, ROOT, at_logon=True)["status"] == "already-registered"


def test_matching_registration_is_idempotent_and_option_drift_requires_unregister(scheduler):
    scheduler()
    assert windows.register_task(NAME, EXE, ARGS, ROOT, at_logon=False)["status"] == "already-registered"
    with pytest.raises(RuntimeError, match="different trigger configuration"):
        windows.register_task(NAME, EXE, ARGS, ROOT, at_logon=True)
    scheduler("""
$logon = [pscustomobject]@{ Type = 9; Enabled = $true; UserId = $sid }
$fakeTask.Definition.Triggers = [FakeCollection]::new(@($logon))
""")
    assert operate("status")["at_logon"] is True
    assert windows.register_task(NAME, EXE, ARGS, ROOT, at_logon=True)["status"] == "already-registered"
    scheduler("$fakeTask.Definition.Settings.RestartCount = 3")
    with pytest.raises(RuntimeError, match="different RestartCount setting"):
        windows.register_task(NAME, EXE, ARGS, ROOT, at_logon=False)


def test_requests_and_stop_confirmation(scheduler):
    scheduler()
    assert operate("start")["status"] == "start-requested"
    assert operate("unregister") == {"task_name": NAME, "status": "unregistered"}
    scheduler("$fakeTask.Enabled = $false")
    with pytest.raises(RuntimeError, match="disabled or disallows demand starts"):
        operate("start")
    scheduler("$fakeTask.State = 4")
    with pytest.raises(RuntimeError, match="before unregistering"):
        operate("unregister")
    assert operate("stop")["status"] == "stopped"
    scheduler("$fakeTask.State = 4; $fakeTask.StateAfterStop = 4")
    assert operate("stop")["status"] == "stop-requested"


@pytest.mark.parametrize("native,state", [(2, "queued"), (4, "running")])
def test_start_uses_active_instance_without_calling_run(scheduler, native, state):
    scheduler(f"""
$fakeTask.State = {native}
$fakeTask | Add-Member -Force ScriptMethod Run {{ throw 'Unexpected Run' }}
""")
    assert operate("start")["status"] == state
