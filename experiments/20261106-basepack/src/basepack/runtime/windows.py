"""Control current-user runtime tasks through Windows Task Scheduler 2.0."""

import base64
import json
import os
from pathlib import Path
import subprocess


# PowerShell receives the task definition through stdin. Only this fixed program
# is encoded into the command passed to Windows PowerShell.
_TASK_PROGRAM = r"""
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$request = ConvertFrom-Json -InputObject ([Console]::In.ReadToEnd())
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$sid = $identity.User.Value

function Test-CurrentUser($userId) {
    if (-not $userId) { return $false }
    if ($userId -eq $sid) { return $true }
    try {
        $resolved = [Security.Principal.NTAccount]::new($userId).Translate([Security.Principal.SecurityIdentifier])
        return $resolved.Value -eq $sid
    } catch [Security.Principal.IdentityNotMappedException] {
        return $false
    }
}

function Get-TaskState($registered) {
    switch ([int]$registered.State) {
        0 { 'unknown' }
        1 { 'disabled' }
        2 { 'queued' }
        3 { 'stopped' }
        4 { 'running' }
        default { throw "Unexpected Task Scheduler state $($registered.State)." }
    }
}

$settings = [ordered]@{
    AllowDemandStart = $true
    AllowHardTerminate = $true
    MultipleInstances = 2 # TASK_INSTANCES_IGNORE_NEW
    ExecutionTimeLimit = 'PT0S'
    RunOnlyIfIdle = $false
    RunOnlyIfNetworkAvailable = $false
    DisallowStartIfOnBatteries = $false
    StopIfGoingOnBatteries = $false
    RestartCount = 2
    RestartInterval = 'PT1M'
}

$scheduler = New-Object -ComObject 'Schedule.Service'
$scheduler.Connect()
$folder = $scheduler.GetFolder('\')
$task = $null
try {
    $task = $folder.GetTask($request.name)
} catch {
    if ($_.Exception.GetBaseException().HResult -ne 0x80070002) { throw }
    # HRESULT_FROM_WIN32(ERROR_FILE_NOT_FOUND)
}

$result = @{ task_name = $request.name }
if ($null -eq $task) {
    if ($request.operation -eq 'register') {
        $definition = $scheduler.NewTask(0)
        $definition.RegistrationInfo.Description = 'BasePack per-user runtime task'
        $definition.Principal.UserId = $sid
        $definition.Principal.LogonType = 3 # TASK_LOGON_INTERACTIVE_TOKEN
        $definition.Principal.RunLevel = 0 # TASK_RUNLEVEL_LUA
        $definition.Settings.Enabled = $true
        foreach ($setting in $settings.GetEnumerator()) {
            $definition.Settings.($setting.Key) = $setting.Value
        }
        $action = $definition.Actions.Create(0) # TASK_ACTION_EXEC
        $action.Path = $request.executable
        $action.Arguments = $request.arguments
        $action.WorkingDirectory = $request.working_directory
        if ($request.at_logon) {
            $trigger = $definition.Triggers.Create(9) # TASK_TRIGGER_LOGON
            $trigger.UserId = $sid
        }
        # TASK_CREATE fails if another registration has taken the name.
        $task = $folder.RegisterTaskDefinition($request.name, $definition, 2, $sid, $null, 3, $null)
        $result.status = 'registered'
        $result.at_logon = $request.at_logon
        $result.last_task_result = $task.LastTaskResult
    } elseif ($request.operation -eq 'start') {
        throw "Task '$($request.name)' is unregistered. Register it before starting it."
    } else {
        $result.status = 'unregistered'
    }
} else {
    $definition = $task.Definition
    $principal = $definition.Principal
    $collision = "Task '$($request.name)' has a different BasePack action or user principal."
    if ($definition.Actions.Count -ne 1 -or $principal.LogonType -ne 3 -or
        $principal.RunLevel -ne 0 -or -not (Test-CurrentUser $principal.UserId)) {
        throw $collision
    }
    $action = $definition.Actions.Item(1)
    if ($action.Type -ne 0 -or $action.Path -cne $request.executable -or
        [string]$action.Arguments -cne $request.arguments -or
        $action.WorkingDirectory -cne $request.working_directory) {
        throw $collision
    }

    $triggerCount = $definition.Triggers.Count
    $atLogon = $false
    for ($index = 1; $index -le $triggerCount; $index++) {
        $trigger = $definition.Triggers.Item($index)
        if ($trigger.Type -eq 9 -and $trigger.Enabled -and (Test-CurrentUser $trigger.UserId)) {
            $atLogon = $true
            break
        }
    }

    $result.at_logon = $atLogon
    switch ($request.operation) {
        'register' {
            if ($request.at_logon -ne $atLogon -or $triggerCount -ne [int]$request.at_logon) {
                throw "Task '$($request.name)' has a different trigger configuration. Stop and unregister it before changing the registration."
            }
            foreach ($setting in $settings.GetEnumerator()) {
                if ($setting.Value -ne $definition.Settings.($setting.Key)) {
                    throw "Task '$($request.name)' has a different $($setting.Key) setting. Stop and unregister it before changing the registration."
                }
            }
            $result.status = 'already-registered'
        }
        'status' {
            $result.status = Get-TaskState $task
        }
        'start' {
            $state = Get-TaskState $task
            if ($state -in @('queued', 'running')) {
                $result.status = $state
            } elseif (-not $task.Enabled -or -not $definition.Settings.AllowDemandStart) {
                throw "Task '$($request.name)' is disabled or disallows demand starts."
            } else {
                $null = $task.Run($null)
                $result.status = 'start-requested'
            }
        }
        'stop' {
            $state = Get-TaskState $task
            if ($state -notin @('stopped', 'disabled')) {
                $task.Stop(0)
                $state = Get-TaskState $task
                if ($state -notin @('stopped', 'disabled')) { $state = 'stop-requested' }
            }
            $result.status = $state
        }
        'unregister' {
            if ((Get-TaskState $task) -notin @('stopped', 'disabled')) {
                throw "Task '$($request.name)' is not confirmed stopped. Stop it before unregistering."
            }
            $folder.DeleteTask($request.name, 0)
            $result.Remove('at_logon')
            $result.status = 'unregistered'
        }
    }
    if ($result.status -ne 'unregistered') {
        $result.last_task_result = $task.LastTaskResult
    }
}

[Console]::WriteLine((ConvertTo-Json -InputObject $result -Compress))
"""


def _invoke(operation: str, name: str, executable: Path, arguments: list[str],
            working_directory: Path, *, at_logon: bool = False) -> dict:
    if os.name != "nt":
        raise RuntimeError("Windows Task Scheduler is only available on Windows")

    powershell = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    encoded = base64.b64encode(_TASK_PROGRAM.encode("utf-16le")).decode("ascii")
    command = (
        "& ([scriptblock]::Create([Text.Encoding]::Unicode.GetString("
        f"[Convert]::FromBase64String('{encoded}'))))"
    )
    request = {
        "operation": operation,
        "name": name,
        "executable": str(executable),
        "arguments": subprocess.list2cmdline(arguments),
        "working_directory": str(working_directory),
        "at_logon": at_logon,
    }
    result = subprocess.run(
        [str(powershell), "-NoProfile", "-NonInteractive", "-Command", command],
        input=json.dumps(request), capture_output=True, encoding="utf-8",
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    if result.returncode:
        detail = result.stderr.strip()
        raise RuntimeError(f"Task Scheduler {operation} failed for '{name}' ({result.returncode}): {detail}")
    return json.loads(result.stdout)


def register_task(name: str, executable: Path, arguments: list[str], working_directory: Path,
                  *, at_logon: bool) -> dict:
    return _invoke("register", name, executable, arguments, working_directory, at_logon=at_logon)


def task_operation(action: str, name: str, executable: Path, arguments: list[str],
                   working_directory: Path) -> dict:
    if action not in ("status", "start", "stop", "unregister"):
        raise ValueError(f"Unknown Task Scheduler operation: {action}")
    return _invoke(action, name, executable, arguments, working_directory)
