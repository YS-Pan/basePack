"""One submit and native queue/history state with bounded observation."""

from datetime import datetime
import json
import locale
import math
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import time

from .submit import JobSpec, normalize_spec, prepare_submission


class CondorClient:
    def __init__(self, config):
        self.config = config
        self.machine = config.machine
        self.bin_dir = self.machine.path_value("htcondor", "bin_dir")
        self.env = dict(os.environ, CONDOR_CONFIG=str(self.machine.path_value("htcondor", "config_file")))
        self.encoding = locale.getencoding() if os.name == "nt" else "utf-8"

    def _call(self, command: str, *args, check=True, timeout=25):
        executable = self.bin_dir / (command + (".exe" if os.name == "nt" else ""))
        result = subprocess.run([str(executable), *map(str, args)], env=self.env,
                                capture_output=True, text=True, encoding=self.encoding,
                                timeout=timeout)
        if check and result.returncode:
            raise RuntimeError(f"{command} exited {result.returncode}\n{result.stdout}{result.stderr}")
        return result

    def _ads(self, command, *args):
        output = self._call(command, *args, "-json").stdout
        # HTCondor 25.4 emits empty text for a successful query with no matching ad.
        return json.loads(output) if output.strip() else []

    def _ad(self, job_id):
        if not re.fullmatch(r"\d+\.\d+", job_id):
            raise ValueError(f"Expected cluster.proc job ID: {job_id!r}")
        queue = self._ads("condor_q", job_id)
        if queue:
            return queue[0], False
        history = self._ads("condor_history", job_id, "-limit", "1")
        if not history:
            raise LookupError(f"Job {job_id} is absent from queue and history")
        return history[0], True

    def capacity(self) -> dict:
        machine = socket.gethostname()
        slots = self._ads("condor_status", "-constraint", "PartitionableSlot =?= true")
        local = [slot for slot in slots if slot["Machine"].lower() == machine.lower()]
        if not local:
            raise LookupError(f"Condor has no partitionable slot for {machine}")
        result = []
        for slot in local:
            machine_resources = re.split(r"[\s,]+", slot["MachineResources"])
            has_gpus = any(name.lower() == "gpus" for name in machine_resources)
            resources = {"cpus": "Cpus", "memory_mib": "Memory", "gpus": "GPUs"}
            resources.update({name: name for name in machine_resources
                              if name and name.lower() not in ("cpus", "memory", "gpus")
                              and name in slot and "TotalSlot" + name in slot})
            result.append({
                "name": slot["Name"],
                "total": {key: slot.get("TotalSlot" + attribute, 0) if key == "gpus" and not has_gpus
                          else slot["TotalSlot" + attribute] for key, attribute in resources.items()},
                "available": {key: slot.get(attribute, 0) if key == "gpus" and not has_gpus
                              else slot[attribute] for key, attribute in resources.items()}})
        return {"machine": machine, "slots": result}

    def _check_request(self, spec):
        for key in ("cpus", "memory_mib", "disk_mib", "queue_timeout", "run_timeout"):
            if getattr(spec, key) <= 0:
                raise ValueError(f"{key} must be positive")
        if spec.gpu_memory_mib < 0:
            raise ValueError("gpu_memory_mib must not be negative")
        cwd = Path(spec.cwd)
        if shutil.disk_usage(cwd).free < spec.disk_mib * 1024**2:
            raise ValueError(f"Insufficient project output disk space at {cwd}")

    def submit(self, spec: JobSpec) -> dict:
        spec = normalize_spec(self.config, spec)
        self._check_request(spec)
        token, folder, payload, submit = prepare_submission(self.config, spec, self.encoding)
        submitted = {"submission_id": token, "job_dir": str(folder), "payload": str(payload)}
        try:
            result = self._call("condor_submit", "-terse", submit)
        except (RuntimeError, subprocess.TimeoutExpired) as error:
            # A lost submit response does not authorize another submission.
            try:
                matches = self._ads("condor_q", "-constraint", f'BasePackSubmissionId == "{token}"')
                if not matches:
                    matches = self._ads("condor_history", "-constraint", f'BasePackSubmissionId == "{token}"', "-limit", "1")
            except (RuntimeError, subprocess.TimeoutExpired, OSError, json.JSONDecodeError) as lookup_error:
                raise error from lookup_error
            if not matches:
                raise
            ad = matches[0]
            job_id = f'{ad["ClusterId"]}.{ad["ProcId"]}'
            submitted["submit_response_error"] = str(error)
            if isinstance(error, subprocess.TimeoutExpired):
                submitted["submit_response_error"] += f"\nstdout: {error.stdout!r}\nstderr: {error.stderr!r}"
        else:
            job_id = re.search(r"\d+\.\d+", result.stdout).group()
        submitted["job_id"] = job_id
        (folder / "submission.json").write_text(json.dumps(submitted, indent=2), encoding="utf-8")
        self._call("condor_reschedule")
        return submitted

    def status(self, job_id: str, *, analyze=False) -> dict:
        ad, history = self._ad(job_id)
        number = ad["JobStatus"]
        state = {1: "queued", 2: "running", 3: "removed", 4: "completed", 5: "held", 6: "transferring", 7: "suspended"}[number]
        finished = _terminal_time(ad, self.encoding) if history else None
        started = ad.get("JobCurrentStartExecutingDate") or None
        end = finished if history else time.time()
        result = {
            "job_id": job_id, "state": state, "terminal": history,
            "exit_code": ad.get("ExitCode"), "exit_signal": ad.get("ExitSignal"),
            "reason": ad.get("HoldReason") or ad.get("RemoveReason"),
            "hold_reason_code": ad.get("HoldReasonCode"), "hold_reason_subcode": ad.get("HoldReasonSubCode"),
            "submitted": ad["QDate"], "started": started,
            "finished": finished, "remote_host": ad.get("RemoteHost", ad.get("LastRemoteHost")),
            "elapsed_seconds": end - ad["QDate"] if end is not None else None,
            "queued_seconds": (started if started is not None else end) - ad["QDate"] if started is not None or end is not None else None,
            "running_seconds": end - started if started is not None and end is not None else None,
            "stdout": ad.get("Out"), "stderr": ad.get("Err"), "event_log": ad.get("UserLog"),
        }
        if history and number == 4:
            payload = json.loads(Path(ad["BasePackPayload"]).read_text(encoding="utf-8"))
            missing = [str(Path(payload["spec"]["cwd"]) / output) for output in payload["spec"]["transfer_outputs"]
                       if not (Path(payload["spec"]["cwd"]) / output).exists()]
            result.update(success=ad.get("ExitCode") == 0 and not ad.get("ExitBySignal", False) and not missing,
                          missing_outputs=missing)
        elif history:
            result["success"] = False
            result["timeout"] = None
        if (number == 5 or (number == 3 and ad.get("LastJobStatus") == 5)) and ad.get("HoldReasonCode") in (46, 47):
            result["timeout"] = "execution"
        if analyze and number == 1:
            diagnostic = self._call("condor_q", job_id, "-better-analyze", check=False)
            result["analysis"] = diagnostic.stdout + diagnostic.stderr
        return result

    def cancel(self, job_id: str) -> dict:
        result = self.status(job_id)
        if result["terminal"]:
            return result | {"cancellation_requested": False}
        self._call("condor_rm", job_id)
        return self.status(job_id) | {"cancellation_requested": True}

    def wait(self, job_id: str, *, timeout=300) -> dict:
        """Observe native state; expiry leaves the job running."""
        deadline = time.monotonic() + timeout
        while True:
            result = self.status(job_id)
            if result["terminal"] or result["state"] == "held":
                return result
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return result | {"observation_expired": True}
            waited = self._call("condor_wait", "-wait", max(1, math.ceil(remaining)),
                                result["event_log"], job_id, check=False, timeout=None)
            if waited.returncode:
                if waited.returncode != 1 or (waited.stdout + waited.stderr).strip() != "Time expired.":
                    raise RuntimeError(f"condor_wait exited {waited.returncode}\n{waited.stdout}{waited.stderr}")
                result = self.status(job_id)
                if result["terminal"] or result["state"] == "held":
                    return result
                return result | {"observation_expired": True}
            # The event may precede its queue-to-history transition.
            time.sleep(min(1, max(0, deadline - time.monotonic())))

    def run(self, spec: JobSpec) -> dict:
        submitted = self.submit(spec)
        result = self.wait(submitted["job_id"], timeout=spec.queue_timeout + spec.run_timeout + 30)
        return submitted | result


def _terminal_time(ad: dict, encoding: str) -> int | None:
    if ad.get("CompletionDate"):
        return ad["CompletionDate"]
    # Removed jobs can retain QDate as EnteredCurrentStatus. The native abort event
    # records the removal time.
    log = Path(ad["UserLog"])
    if not log.exists():
        return None
    timestamp = None
    for match in re.finditer(r"^(?:005|009) \((\d+)\.(\d+)\.\d+\) (\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)",
                             log.read_text(encoding=encoding), re.MULTILINE):
        if (int(match[1]), int(match[2])) == (ad["ClusterId"], ad["ProcId"]):
            timestamp = int(datetime.fromisoformat(match[3]).timestamp())
    return timestamp


