"""Direct machine administration, including diagnosis and stop after an upgrade."""

from .registry import deployment_fingerprint, read_marker
from .transport import rpc


def status(machine):
    marker = read_marker(machine, "broker", require_match=False)
    result = rpc(marker, "status", timeout=5, allow_legacy=True)
    running = result["deployment_fingerprint"] if "deployment_fingerprint" in result else result["service_key"]
    target = deployment_fingerprint(machine)
    return result | {"deployment_fingerprint": running,
                     "target_deployment_fingerprint": target,
                     "deployment_matches": running == target}


def stop(machine):
    marker = read_marker(machine, "broker", require_match=False)
    return rpc(marker, "stop", timeout=5, allow_legacy=True)
