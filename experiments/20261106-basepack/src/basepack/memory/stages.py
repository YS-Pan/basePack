"""Fixed handoff packages for serial host coordinators in one maintenance run."""

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path


def fixed_reference(path):
    path = Path(path).resolve()
    return {"path": str(path), "file_sha256": sha256(path.read_bytes()).hexdigest()}


def read_fixed_bytes(reference):
    path = Path(reference["path"])
    material = path.read_bytes()
    if sha256(material).hexdigest() != reference["file_sha256"]:
        raise ValueError(f"Stage reference file SHA256 mismatch: {path}")
    return material


def _read_reference(reference):
    return json.loads(read_fixed_bytes(reference).decode("utf-8"))


def receipt_scope(material):
    outcomes = [material["outcome_candidate"]] if "outcome_candidate" in material else []
    return {"paths": [item["path"] for item in material["semantic"]],
            "relations": [item["id"] for item in (*material["pending_relations"],
                                                   *material.get("graph_candidates", ()), *outcomes)],
            "feedback": [item["id"] for item in material.get("feedback", [])]}


def stage_layout(layout, index, run_id):
    layout = deepcopy(layout)
    prefix = f"bp_mem_{run_id[:8]}_s{index}_"
    for team in layout["teams"]:
        team["task_name"] = f"{prefix}coord_{team['team']}"
        team["parent_task_name"] = f"{prefix}coord_0" if team["team"] else None
        team["reader_task_names"] = [f"{prefix}read_{team['team']}_{reader}"
                                     for reader in range(len(team["reader_task_names"]))]
    return layout


def load_stage(receipt, control, stage_path, *, file_sha256=None):
    """Read a saved package without opening ownership, credentials, or the database."""
    stage = (_read_reference({"path": str(Path(stage_path).resolve()), "file_sha256": file_sha256})
             if file_sha256 else json.loads(Path(stage_path).read_text(encoding="utf-8")))
    if stage["receipt"]["path"] != str(Path(receipt).resolve()) or stage["control"] != str(Path(control).resolve()):
        raise ValueError("Stage receipt/control does not match this assignment")
    material = _read_reference(stage["receipt"])
    _read_reference(stage["handoff"])
    if material["owner_run_id"] != stage["owner_run_id"]:
        raise ValueError("Stage owner does not match the fixed receipt")
    return stage


def prepare_stage(config, receipt, control, handoff, output, *, workers_ended, previous_stage=None,
                  available_subagents=None):
    """Validate a host-confirmed boundary and save one new stage; never spawn agents."""
    from .owner import save_stage
    from .prompts import _wave_layout, maintenance_layout, prompt_dispatch
    from .waves import inspect

    if not workers_ended:
        raise ValueError("Confirm that the previous coordinator and its workers ended")
    receipt_ref, handoff_ref = fixed_reference(receipt), fixed_reference(handoff)
    material, boundary = _read_reference(receipt_ref), _read_reference(handoff_ref)
    previous_ref = None
    if previous_stage is not None:
        previous = load_stage(receipt, control, previous_stage)
        previous_ref = {**fixed_reference(previous_stage), "index": previous["index"]}
        scope, layout, index = previous["remaining"], _wave_layout(previous["layout"]), previous["index"] + 1
    else:
        scope, layout, index = receipt_scope(material), _wave_layout(material["layout"]), 1
    # Every original candidate is either finished by this group or carried forward.
    for kind in ("paths", "relations", "feedback"):
        completed, remaining = boundary["completed"][kind], boundary["remaining"][kind]
        if (len(set(completed)) != len(completed) or len(set(remaining)) != len(remaining)
                or set(completed) & set(remaining) or set(completed) | set(remaining) != set(scope[kind])):
            raise ValueError(f"Handoff completed/remaining {kind} must exactly partition the previous scope")
    wave = inspect(config.memory_dir, control, material["owner_run_id"], boundary["wave_id"])
    if not wave["closed"]:
        raise ValueError("Close the wave after publication and notification resolution before a stage handoff")
    graph_scope = {item["id"] for item in material.get("graph_candidates", ())} & set(scope["relations"])
    resolved = set(wave.get("resolved_graph_candidates", ())) & graph_scope
    if set(boundary["completed"]["relations"]) & graph_scope != resolved:
        raise ValueError("Completed graph candidates must match closed wave reviews and publications")
    outcome = material.get("outcome_candidate")
    if outcome and outcome["id"] in scope["relations"]:
        resolved = outcome["id"] in wave.get("resolved_outcome_candidates", ())
        if (outcome["id"] in boundary["completed"]["relations"]) != resolved:
            raise ValueError("Completed outcome candidate must match its closed wave review and publication")
    receipts = []
    for ref in wave["history"]:
        previous_wave = _read_reference(ref)
        if previous_wave["run_id"] != material["owner_run_id"]:
            continue
        if previous_wave["receipt"] is None:
            raise ValueError("An earlier wave in this run has no fixed execution receipt")
        receipts.append(_read_reference(previous_wave["receipt"]))
    receipts.append(_read_reference(wave["receipt"]))
    expected_handles = {name: worker["handle"] for receipt in receipts
                        for name, worker in receipt["workers"].items() if worker["handle"]}
    workers = boundary["workers"]
    names = [worker["task_name"] for worker in workers]
    if not layout["teams"] or layout["teams"][0]["task_name"] not in names:
        raise ValueError("Handoff must identify the ended publisher coordinator")
    if len(set(names)) != len(names) or any(worker["status"] != "ended" or not worker["handle"] for worker in workers):
        raise ValueError("Handoff workers must have unique task names and ended host handles")
    observed = {worker["task_name"]: worker["handle"] for worker in workers}
    if any(observed.get(name) != handle for name, handle in expected_handles.items()):
        raise ValueError("Handoff must identify each started wave worker's ended host handle")
    for reference in boundary["completed_drafts"]:
        if not reference["assignment"].strip():
            raise ValueError("Completed draft must identify its assignment")
        _read_reference(reference)
    for reference in boundary["publication_results"]:
        _read_reference(reference)
    if not any(boundary["remaining"].values()):
        raise ValueError("No remaining work requires a new stage; finish the original run")
    next_layout = maintenance_layout(config, mode=layout["mode"],
                                     available_subagents=available_subagents,
                                     work_items=max(len(boundary["remaining"][kind])
                                                    for kind in ("paths", "relations", "feedback")),
                                     run_id=material["owner_run_id"])
    if not next_layout["teams"]:
        raise ValueError("A coordinator, reader and reserved recovery seat are required for a new stage")
    stage = {"index": index, "receipt": receipt_ref, "control": str(Path(control).resolve()),
             "owner_run_id": material["owner_run_id"], "previous_stage": previous_ref,
             "handoff": handoff_ref, "completed": boundary["completed"], "remaining": boundary["remaining"],
             "layout": stage_layout(next_layout, index, material["owner_run_id"]), "workers_ended": True,
             "errors": boundary["errors"], "jobs": boundary["jobs"],
             "completion": "Previous bounded group ended; the maintenance run remains open."}
    reference = save_stage(config.memory_dir, control, stage, output)
    return {"stage": reference, "receipt": receipt_ref["path"], "control": stage["control"],
            "owner_run_id": stage["owner_run_id"], "remaining": stage["remaining"],
            "worker": prompt_dispatch(config, receipt, control, layout=stage["layout"],
                                      stage=reference["path"], stage_sha256=reference["file_sha256"]),
            "completion": stage["completion"]}
