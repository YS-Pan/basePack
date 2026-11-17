"""Finite-wave CLI, fixed publication and owner boundaries without a live database."""

import argparse
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import shlex
import subprocess
import sys
from types import SimpleNamespace

import pytest

from basepack.memory import owner, waves
from basepack.memory.cli import dispatch, register_commands
from basepack.memory.maintenance import MaintenanceStopped
from basepack.memory.privacy import privacy_rules, rules_revision
from basepack.memory.prompts import maintenance_layout
from basepack.memory.stages import fixed_reference
from basepack.memory.store import PublicationOutcomeUnknown
from basepack.project.config import load_project_config
from basepack.project.init import init_project


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def arguments(*args):
    parser = argparse.ArgumentParser()
    register_commands(parser.add_subparsers(dest="command", required=True))
    return parser.parse_args(["memory", *map(str, args)])


@pytest.fixture
def wave_project(tmp_path):
    machine = tmp_path / "machine.toml"
    machine.write_text("schema_version=1\n", encoding="utf-8")
    config = load_project_config(init_project(tmp_path / "project", machine,
                                              max_concurrent_subagents=4, concurrency_source="isolated integration fixture"))
    control = config.root / "owner.control"
    claimed = owner.acquire(config.memory_dir, config.raw["memory"]["project_id"], "wave integration", control)
    run = claimed["owner"]["run_id"]
    task_list = []
    for index in range(3):
        path = config.root / f"source-{index}.md"
        path.write_bytes(f"Independent toy evidence {index}.\n".encode())
        task_list.append({"id": f"task-{index}", "goal": f"Read toy source {index}", "paths": [path.name],
                          "write_targets": [f"node:toy-{index}"], "outputs": ["draft", "coverage", "errors"]})
    layout = maintenance_layout(config, work_items=3, run_id=run)
    coordinator = "/root/" + layout["teams"][0]["task_name"]
    receipt = write_json(config.root / "receipt.json", {
        "owner_run_id": run, "layout": layout,
        "workset": {"discovered": [task["paths"][0] for task in task_list],
                    "included": [task["paths"][0] for task in task_list], "accepted": []},
        "semantic": [{"path": task["paths"][0], "members": []} for task in task_list],
        "pending_relations": [], "feedback": []})
    tasks = write_json(config.root / "tasks.json", task_list)
    current = SimpleNamespace(config=config, control=control, run=run, receipt=receipt, tasks=tasks,
                              task_list=task_list, wave=None, workers=None, coordinator=coordinator)

    def call(action, *args):
        common = ["wave", action, "--control", control, "--run-id", run]
        if action != "create":
            common += ["--wave-id", current.wave]
        result, status = dispatch(arguments(*common, *args), config)
        assert status == 0
        return result

    def create(count=3):
        write_json(tasks, task_list[:count])
        result = call("create", "--receipt", receipt, "--tasks", tasks, "--coordinator", coordinator,
                      "--readers", min(count, 2))
        current.wave = result["wave_id"]
        current.workers = [worker["task_name"] for worker in result["workers"]]
        return result

    def start_and_seal():
        for worker in current.workers:
            call("started", "--worker", worker, "--handle", coordinator + "/" + worker)
        initialized = call("initialized")
        call("seal")
        return initialized

    def submit(worker, task, *, drafts=(), failed=False):
        coverage = write_json(config.root / f"{task['id']}-coverage.json", {"paths": task["paths"], "unread": []})
        errors = write_json(config.root / f"{task['id']}-errors.json", ["toy task failure"] if failed else [])
        options = ["--worker", worker, "--task-id", task["id"], "--coverage", coverage, "--errors", errors,
                   "--drafts", *drafts]
        if failed:
            options += ["--failed"]
        return call("submit", *options)

    current.call, current.create, current.start_and_seal, current.submit = call, create, start_and_seal, submit
    yield current
    state = owner.status(config.memory_dir)
    if state:
        assert not state["publications"], "The test must explicitly resolve its own uncertain publication"
        owner.stop_owned(config.memory_dir, control)
        owner.release(config.memory_dir, control)


def complete_wave(project, *, draft=False):
    project.create(count=1)
    project.start_and_seal()
    worker = project.workers[0]
    task = project.call("claim", "--worker", worker)["task"]
    drafts = []
    if draft:
        rules = privacy_rules(project.config)
        path = task["paths"][0]
        reading = write_json(project.config.root / "reading.json", {
            "sources": [{"path": path, "revision": sha256((project.config.root / path).read_bytes()).hexdigest(),
                         "kind": "text", "members": []}],
            "neighborhood": {"members": [], "nodes": [], "edges": []}, "expected": {},
            "privacy_rules": rules, "privacy_rules_revision": rules_revision(rules)})
        drafts = [write_json(project.config.root / "proposal.json", {
            "prepare": fixed_reference(reading), "sources": [path],
            "members": [{"kind": "chunk", "path": path, "start_line": 1, "end_line": 1, "title": "Toy evidence"}]})]
    project.submit(worker, task, drafts=drafts)
    retired = project.call("claim", "--worker", worker)
    assert retired["notification"]["worker"] == worker
    project.call("notification-pending", "--worker", worker)
    assert project.call("finish")["already_finished"] is False
    return worker, task, drafts


def acknowledge(project, worker, *, accepted=True):
    response = write_json(project.config.root / "host-response.json", {
        "kind": "program fixture, not an actual host call", "accepted": accepted,
        "result": "accepted request" if accepted else "original host error"})
    return project.call("notification-result", "--worker", worker,
                        "--accepted" if accepted else "--failed", "--result", response)


def publication_inputs(project, task, drafts):
    completed = write_json(project.config.root / "completed.json", [
        {**fixed_reference(path), "assignment": task["id"]} for path in drafts])
    return ["--completed", completed, "--frozen", project.config.root / "frozen.json",
            "--result", project.config.root / "published.json"]


def prompted_prepare_paths(prompt):
    command = next(line for line in prompt.splitlines() if "--paths" in line and "--output" in line)
    tokens = shlex.split(command)
    return tokens[tokens.index("--paths") + 1:tokens.index("--output")]


def owner_admitted_boundary(project, monkeypatch, *, error=None, uncertain=False, stop_at_construction=False):
    """Replace only native DB apply; keep the actual owner publication admission."""
    calls, admissions = [], []

    class DatabaseBoundary:
        def __init__(self, config):
            self.config = config
            if stop_at_construction:
                owner.stop_owned(config.memory_dir, project.control)

        def apply(self, batch, *, control, timeout):
            token = owner.begin_publication(self.config.memory_dir, control, batch["batch_id"])
            admissions.append(token)
            assert token in owner.status(self.config.memory_dir)["publications"]
            calls.append(deepcopy(batch))
            if error:
                if not uncertain:
                    owner.finish_publication(self.config.memory_dir, control, token)
                raise error
            owner.finish_publication(self.config.memory_dir, control, token)
            return {"sources": len(batch["sources"]), "members": len(batch["members"]),
                    "nodes": len(batch.get("nodes", [])), "edges": len(batch.get("edges", [])), "invalidated": []}

    monkeypatch.setattr("basepack.memory.store.Memory", DatabaseBoundary)
    return calls, admissions


def test_wave_cli_gate_and_claimed_prompt_use_fixed_receipt_and_actual_worker(wave_project):
    project = wave_project
    created = project.create()
    assert len(created["workers"]) == 2
    for worker in created["workers"]:
        supplied = worker["spawn_arguments"]
        assert set(supplied) == {"task_name", "fork_turns", "model", "reasoning_effort", "message"}
        assert supplied["task_name"] == worker["task_name"]
        assert (supplied["model"], supplied["reasoning_effort"], supplied["fork_turns"]) == ("gpt-6-luna", "max", "none")
        assert "worker-prompt" in supplied["message"] and worker["task_name"] in supplied["message"]
    first, second = project.workers
    project.call("started", "--worker", first, "--handle", project.coordinator + "/" + first)
    pending = project.call("claim", "--worker", first)
    assert pending == {"startup_pending": True, "task": None, "retired": False}
    with pytest.raises(ValueError):
        project.call("seal")
    project.call("started", "--worker", second, "--handle", project.coordinator + "/" + second)
    with pytest.raises(ValueError, match="initialization"):
        project.call("seal")
    initialization = project.call("initialized")
    assert initialization == project.call("initialized")
    assert fixed_reference(initialization["path"]) == initialization
    worker_prompt = project.call("worker-prompt", "--worker", first)["prompt"]
    assert "go" in worker_prompt and project.coordinator in worker_prompt
    with pytest.raises(PermissionError):
        project.call("task-prompt", "--worker", first, "--task-id", "task-0")
    project.call("seal")
    task = project.call("claim", "--worker", first)["task"]
    prompt = project.call("task-prompt", "--worker", first, "--task-id", task["id"])
    assert task["paths"][0] in prompt["prompt"]
    assert "explicit field allowlists" in prompt["prompt"]
    with pytest.raises(PermissionError):
        project.call("task-prompt", "--worker", second, "--task-id", task["id"])


def test_wave_cli_two_process_loops_have_unique_last_notification(wave_project):
    project = wave_project
    project.create()
    project.start_and_seal()
    coverage = write_json(project.config.root / "coverage.json", {"toy": True})
    errors = write_json(project.config.root / "errors.json", [])
    script = r'''
import argparse,json,sys
from basepack.memory.cli import register_commands,dispatch
from basepack.project.config import load_project_config
config,control,run,wave,worker,coverage,errors=sys.argv[1:]
config=load_project_config(config)
parser=argparse.ArgumentParser()
register_commands(parser.add_subparsers(dest="command",required=True))
def call(action,*args):
    result,status=dispatch(parser.parse_args(["memory","wave",action,"--control",control,
        "--run-id",run,"--wave-id",wave,*args]),config)
    assert status==0
    return result
claimed=[]
while True:
    value=call("claim","--worker",worker)
    if value["retired"]:
        print(json.dumps({"claimed":claimed,"notification":value["notification"]}),flush=True)
        break
    task=value["task"]["id"]
    claimed.append(task)
    call("submit","--worker",worker,"--task-id",task,"--coverage",coverage,"--errors",errors)
'''
    processes = [subprocess.Popen([sys.executable, "-X", "utf8", "-c", script, str(project.config.path),
                    str(project.control), project.run, project.wave, worker, str(coverage), str(errors)],
                    cwd=project.config.root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
                 for worker in project.workers]
    outputs = []
    for process in processes:
        stdout, stderr = process.communicate(timeout=30)
        assert process.returncode == 0, stderr
        outputs.append(json.loads(stdout))
    assert sorted(task for result in outputs for task in result["claimed"]) == ["task-0", "task-1", "task-2"]
    assert sum(result["notification"] is not None for result in outputs) == 1
    state = project.call("inspect")
    assert all(task["status"] == "submitted" for task in state["tasks"])
    assert all(worker["status"] == "retired" for worker in state["workers"].values())
    assert fixed_reference(state["receipt"]["path"]) == state["receipt"]


@pytest.mark.parametrize("claimed_before_failure", [False, True])
def test_wave_cli_all_host_failures_keep_recovery_without_normal_notifier(wave_project, claimed_before_failure):
    project = wave_project
    project.create()
    if claimed_before_failure:
        project.start_and_seal()
        project.call("claim", "--worker", project.workers[0])
    for worker in project.workers:
        project.call("worker-failed", "--worker", worker, "--error", "original host failure")
    if not claimed_before_failure:
        project.call("initialized")
        project.call("seal")
    state = project.call("inspect")
    assert state["receipt"] and state["notification"] is None
    assert all(worker["error"] == "original host failure" for worker in state["workers"].values())
    statuses = [task["status"] for task in state["tasks"]]
    assert statuses == (["claimed", "unclaimed", "unclaimed"] if claimed_before_failure else ["unclaimed"] * 3)
    project.call("finish")
    closed = project.call("close", "--no-publication")
    assert closed["closed"] and [task["status"] for task in closed["tasks"]] == statuses


@pytest.mark.parametrize("accepted", [False, True])
def test_wave_cli_pending_callback_needs_parent_ack_before_close_or_next_wave(wave_project, accepted):
    project = wave_project
    worker, _, _ = complete_wave(project)
    state = project.call("inspect")
    fixed_bytes = Path(state["receipt"]["path"]).read_bytes()
    assert project.call("finish")["already_finished"] is True
    with pytest.raises(PermissionError):
        project.call("notification-pending", "--worker", worker)
    with pytest.raises(RuntimeError, match="notification"):
        project.call("close", "--no-publication")
    with pytest.raises(RuntimeError):
        project.create()
    assert project.call("inspect")["notification"]["status"] == "pending"
    notice = acknowledge(project, worker, accepted=accepted)
    assert notice["status"] == ("accepted" if accepted else "failed")
    closed = project.call("close", "--no-publication")
    assert Path(state["receipt"]["path"]).read_bytes() == fixed_bytes
    prior = project.wave
    project.create()
    assert project.wave != prior
    assert project.call("inspect")["history"][-1] == closed["closure"]


def test_wave_cli_projection_write_failure_resumes_same_frozen_and_callback_once(wave_project, monkeypatch):
    project = wave_project
    worker, task, drafts = complete_wave(project, draft=True)
    calls, admissions = owner_admitted_boundary(project, monkeypatch)
    options = publication_inputs(project, task, drafts)
    frozen, result = project.config.root / "frozen.json", project.config.root / "published.json"
    write_text = Path.write_text
    original = OSError("local result projection unavailable after apply returned")
    fail_once = True

    def failed_projection(path, *args, **kwargs):
        nonlocal fail_once
        if path == result and fail_once:
            fail_once = False
            raise original
        return write_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", failed_projection)
    with pytest.raises(OSError) as failure:
        project.call("publish", *options)
    assert failure.value is original
    material = frozen.read_bytes()
    batch = json.loads(material)
    assert owner.status(project.config.memory_dir)["publications"] == []
    assert project.call("inspect")["publication"]["status"] == "intent"
    assert project.call("finish")["already_finished"] is True
    project.call("publish", *options)
    committed = project.call("publish", *options)
    assert committed["status"] == "committed"
    assert frozen.read_bytes() == material
    assert len(calls) == len(admissions) == 2
    assert all(call["batch_id"] == batch["batch_id"] and call["members"] == batch["members"] for call in calls)
    with pytest.raises(RuntimeError, match="notification"):
        project.call("close")
    acknowledge(project, worker)
    assert project.call("close")["unpublished"] == []


@pytest.mark.parametrize("uncertain", [False, True])
def test_wave_cli_definite_failure_is_distinct_from_owner_uncertainty(wave_project, monkeypatch, uncertain):
    project = wave_project
    worker, task, drafts = complete_wave(project, draft=True)
    acknowledge(project, worker)
    original = PublicationOutcomeUnknown("original transaction response lost") if uncertain else ValueError("original source revision mismatch")
    calls, admissions = owner_admitted_boundary(project, monkeypatch, error=original, uncertain=uncertain)
    options = publication_inputs(project, task, drafts)
    with pytest.raises(type(original)) as failure:
        project.call("publish", *options)
    assert failure.value is original and len(calls) == 1
    failure_options = ["--error", str(original), "--publisher-ended", "--no-commit"]
    if uncertain:
        with pytest.raises(RuntimeError, match="uncertain"):
            project.call("publication-failed", *failure_options)
        with pytest.raises(RuntimeError, match="uncertain"):
            project.call("close")
        # The fixture knows its DB boundary did not commit. Model the parent's
        # explicit verification, never an automatic retry or timeout takeover.
        owner.finish_publication(project.config.memory_dir, project.control, admissions[0])
    failed = project.call("publication-failed", *failure_options)
    assert failed["status"] == "failed" and failed["error"] == str(original)
    with pytest.raises(ValueError, match="definitively failed"):
        project.call("publish", *options)
    closed = project.call("close")
    assert closed["unpublished"] == [{**fixed_reference(drafts[0]), "assignment": task["id"]}]
    assert len(calls) == 1


def test_wave_cli_stop_race_is_rechecked_by_real_publication_admission(wave_project, monkeypatch):
    project = wave_project
    worker, task, drafts = complete_wave(project, draft=True)
    acknowledge(project, worker)
    calls, admissions = owner_admitted_boundary(project, monkeypatch, stop_at_construction=True)
    with pytest.raises(MaintenanceStopped):
        project.call("publish", *publication_inputs(project, task, drafts))
    assert calls == admissions == []
    assert owner.status(project.config.memory_dir)["publications"] == []


def test_wave_cli_late_callback_after_stop_has_no_publish_side_effect(wave_project, monkeypatch):
    project = wave_project
    _, task, drafts = complete_wave(project, draft=True)
    options = publication_inputs(project, task, drafts)
    owner.stop_owned(project.config.memory_dir, project.control)
    wave_path = project.config.memory_dir / "maintenance/wave.json"
    previous = wave_path.read_bytes()
    monkeypatch.setattr("basepack.memory.store.Memory", lambda *args: pytest.fail("stopped callback reached publisher"))
    for operation in (lambda: project.call("finish"), lambda: project.call("publish", *options)):
        with pytest.raises(MaintenanceStopped):
            operation()
    assert wave_path.read_bytes() == previous
    assert not (project.config.root / "frozen.json").exists()


def test_wave_cli_legacy_receipts_and_reader_bypass_entries_are_rejected(wave_project, monkeypatch):
    project = wave_project
    monkeypatch.setattr("basepack.memory.store.Memory", lambda *args: pytest.fail("legacy route accessed DB"))
    for args in (("pending-dispatch", "--receipt", project.receipt, "--available-subagents", "2"),
                 ("prompt", "--receipt", project.receipt, "--control", project.control, "--role", "reader", "--paths", "source-0.md")):
        with pytest.raises(SystemExit) as failure:
            arguments(*args)
        assert failure.value.code == 2
    material = json.loads(project.receipt.read_text(encoding="utf-8"))
    del material["layout"]["organization"]
    write_json(project.receipt, material)
    with pytest.raises(ValueError, match="[Ll]egacy|[Oo]ld maintenance"):
        project.create()
    with pytest.raises(ValueError, match="[Ll]egacy|[Oo]ld maintenance"):
        dispatch(arguments("prompt", "--receipt", project.receipt, "--control", project.control), project.config)
    assert not (project.config.memory_dir / "maintenance/wave.json").exists()


@pytest.mark.parametrize("accepted", [False, True])
def test_wave_cli_parent_recovers_unknown_notification_only_with_host_facts(wave_project, accepted):
    project = wave_project
    complete_wave(project)
    state_path = project.config.memory_dir / "maintenance/wave.json"
    pending = state_path.read_bytes()
    # A callback may finish before the notifier records the host response. Its
    # absence is uncertainty, and neither close nor a timeout resolves it.
    with pytest.raises(RuntimeError, match="notification"):
        project.call("close", "--no-publication")
    with pytest.raises(SystemExit) as failure:
        project.call("notification-recover", "--accepted", "--evidence", "outcome not yet verified")
    assert failure.value.code == 2
    assert state_path.read_bytes() == pending
    evidence = "Program fixture: parent observed notifier ended; host request " + ("accepted" if accepted else "rejected")
    recovered = project.call("notification-recover", "--accepted" if accepted else "--failed",
                             "--evidence", evidence, "--worker-ended", "--host-verified")
    assert recovered["result"] == evidence
    assert recovered["recovery"] == {"worker_ended": True, "host_verified": True}
    with pytest.raises(ValueError, match="awaiting recovery"):
        project.call("notification-recover", "--failed", "--evidence", "repeat observation",
                     "--worker-ended", "--host-verified")
    assert project.call("close", "--no-publication")["closed"]


def test_wave_cli_fixed_workset_allows_stable_sources_but_not_directory_or_outside(wave_project):
    project = wave_project
    material = json.loads(project.receipt.read_text(encoding="utf-8"))
    material["semantic"] = []  # Stable evidence is still in the included workset.
    write_json(project.receipt, material)
    original = project.task_list[0]["paths"]
    for paths in (["outside.md"], ["."]):
        project.task_list[0]["paths"] = paths
        with pytest.raises(ValueError, match="fixed wave scope|identify files"):
            project.create(count=1)
        assert not (project.config.memory_dir / "maintenance/wave.json").exists()
    project.task_list[0]["paths"] = original
    project.create(count=1)
    assert project.call("inspect")["tasks"][0]["paths"] == original


@pytest.mark.parametrize("entry", ["sources", "members"])
def test_wave_cli_read_dependencies_are_preparable_but_not_write_authority(wave_project, entry):
    project = wave_project
    project.task_list[0]["read_paths"] = ["source-1.md"]
    project.create(count=1)
    project.start_and_seal()
    worker = project.workers[0]
    task = project.call("claim", "--worker", worker)["task"]
    prompt = project.call("task-prompt", "--worker", worker, "--task-id", task["id"])["prompt"]
    assert prompted_prepare_paths(prompt) == ["source-0.md", "source-1.md"]
    proposal = {"sources": ["source-0.md"], "members": []}
    if entry == "sources":
        proposal["sources"].append("source-1.md")
    else:
        proposal["members"].append({"kind": "chunk", "path": "source-1.md"})
    draft = write_json(project.config.root / "out-of-scope.json", proposal)
    with pytest.raises(ValueError, match="outside its paths: source-1.md"):
        project.submit(worker, task, drafts=[draft])
    state = project.call("inspect")
    assert state["tasks"][0]["status"] == "claimed" and state["tasks"][0]["result"] is None
    # The direct Python entry has the same guard as the CLI, not a bypass.
    with pytest.raises(ValueError, match="outside its paths"):
        waves.submit(project.config.memory_dir, project.control, project.run, project.wave, worker, task["id"],
                     drafts=[draft], coverage=project.config.root / "task-0-coverage.json",
                     errors=project.config.root / "task-0-errors.json")
    write_json(draft, {"sources": ["source-0.md"], "members": []})
    assert project.submit(worker, task, drafts=[draft])["status"] == "submitted"


def test_wave_cli_graph_only_task_keeps_empty_write_paths_with_read_evidence(wave_project):
    project = wave_project
    project.task_list[0]["paths"] = []
    project.task_list[0]["read_paths"] = ["source-1.md"]
    project.create(count=1)
    project.start_and_seal()
    worker = project.workers[0]
    task = project.call("claim", "--worker", worker)["task"]
    prompt = project.call("task-prompt", "--worker", worker, "--task-id", task["id"])["prompt"]
    assert prompted_prepare_paths(prompt) == ["source-1.md"] and task["paths"] == []
    draft = write_json(project.config.root / "graph.json", {"sources": [], "nodes": [{"title": "Toy graph change"}]})
    assert project.submit(worker, task, drafts=[draft])["status"] == "submitted"


def test_wave_cli_receipt_changed_between_dispatch_and_locked_create_is_rejected(wave_project, monkeypatch):
    project = wave_project
    original = waves.create

    def changed_receipt(*args, **kwargs):
        project.receipt.write_bytes(project.receipt.read_bytes() + b"\n")
        return original(*args, **kwargs)

    monkeypatch.setattr(waves, "create", changed_receipt)
    with pytest.raises(ValueError, match="receipt changed during wave creation"):
        project.create(count=1)
    assert not (project.config.memory_dir / "maintenance/wave.json").exists()


def test_wave_cli_requires_current_owner_stage_and_uses_its_remaining_scope(wave_project):
    project = wave_project
    receipt = json.loads(project.receipt.read_text(encoding="utf-8"))
    handoff = write_json(project.config.root / "handoff.json", {"kind": "isolated stage fixture"})
    package = {"owner_run_id": project.run, "control": str(project.control.resolve()),
               "receipt": fixed_reference(project.receipt), "handoff": fixed_reference(handoff),
               "remaining": {"paths": ["source-0.md"], "relations": [], "feedback": []},
               "layout": receipt["layout"], "index": 1, "previous_stage": None}
    old = owner.save_stage(project.config.memory_dir, project.control, package, project.config.root / "stage-1.json")
    with pytest.raises(PermissionError, match="stage must be supplied"):
        project.create(count=1)
    package = {**package, "index": 2, "previous_stage": old}
    current = owner.save_stage(project.config.memory_dir, project.control, package, project.config.root / "stage-2.json")
    common = ["--receipt", project.receipt, "--tasks", project.tasks, "--coordinator", project.coordinator, "--readers", 1]
    write_json(project.tasks, project.task_list[:1])
    with pytest.raises(PermissionError, match="current owner stage"):
        project.call("create", *common, "--stage", old["path"], "--stage-sha256", old["file_sha256"])
    write_json(project.tasks, project.task_list[:2])
    with pytest.raises(ValueError, match="fixed wave scope"):
        project.call("create", *common, "--stage", current["path"], "--stage-sha256", current["file_sha256"])
    write_json(project.tasks, project.task_list[:1])
    created = project.call("create", *common, "--stage", current["path"], "--stage-sha256", current["file_sha256"])
    project.wave = created["wave_id"]
    assert project.call("inspect")["write_scope"] == ["source-0.md"]


@pytest.mark.parametrize("task_count,readers", [(3, 0), (3, -1), (3, 3), (1, 2)])
def test_wave_cli_fixed_reader_pool_rejects_invalid_size_without_silent_shrink(wave_project, task_count, readers):
    project = wave_project
    write_json(project.tasks, project.task_list[:task_count])
    with pytest.raises(ValueError, match="Reader count"):
        project.call("create", "--receipt", project.receipt, "--tasks", project.tasks,
                     "--coordinator", project.coordinator, "--readers", readers)
    assert not (project.config.memory_dir / "maintenance/wave.json").exists()


def test_wave_cli_requires_pool_choice_and_rejects_generic_output_overwrite(wave_project):
    project = wave_project
    common = ["wave", "create", "--control", project.control, "--run-id", project.run,
              "--receipt", project.receipt, "--tasks", project.tasks, "--coordinator", project.coordinator]
    for options in ([], ["--readers", 2, "--output", project.receipt]):
        before = project.receipt.read_bytes()
        with pytest.raises(SystemExit) as failure:
            arguments(*common, *options)
        assert failure.value.code == 2
        assert project.receipt.read_bytes() == before
    assert not (project.config.memory_dir / "maintenance/wave.json").exists()
