"""Native LitServe diagnostics and Windows service control."""

import json
import subprocess
from urllib.request import ProxyHandler, build_opener


def status(machine):
    endpoint = machine.raw["embedding"]["endpoint"].rstrip("/")
    opener = build_opener(ProxyHandler({}))
    with opener.open(endpoint + "/health", timeout=5) as response:
        health = response.status
    with opener.open(endpoint + "/info", timeout=5) as response:
        info = json.load(response)
    return {"endpoint": endpoint, "health": health, **info}


def stop(machine):
    name = machine.raw["embedding"]["service_name"]
    result = subprocess.run(["sc.exe", "stop", name], check=True, capture_output=True, text=True)
    return {"service_name": name, "control_result": result.stdout,
            "note": "Stop accepted; use Get-Service to observe the Stopped state."}
