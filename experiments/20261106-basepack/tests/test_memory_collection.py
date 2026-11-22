from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from basepack.memory import owner
from basepack.memory.collection import codex_trial, collect, load_collection, retained_snapshots
from basepack.memory.maintenance import MaintenanceStopped, _locked


ATTEMPT = "a" * 32


def config(root, project_id="project"):
    return SimpleNamespace(root=root, memory_dir=root / ".basepack" / "memory",
                           raw={"memory": {"codex": {"project_id": project_id,
                                   "registry_complete": True, "other_project_roots": []}}})


def setup_collector(monkeypatch, capture, *, on_close=None, threads=None):
    from basepack.memory import codex, codex_binding

    class Client:
        def __init__(self, executable):
            self.closed = False

        def close(self):
            self.closed = True
            if on_close is not None:
                on_close()

    monkeypatch.setattr(codex, "AppServer", Client)
    if threads is None:
        threads = [{"id": "thread", "projectId": "project"}]
    monkeypatch.setattr(codex, "list_threads", lambda client, checkpoint: threads)
    monkeypatch.setattr(codex_binding, "discover_binding", lambda root, project_id, other_roots: {
        "project_id": project_id, "worktrees": [str(root)], "other_roots": other_roots, "gaps": []})
    monkeypatch.setattr(codex, "collect_codex", capture)


def test_collection_receipt_verifies_exact_snapshot(tmp_path, monkeypatch):
    cfg = config(tmp_path)
    source = cfg.memory_dir / "codex" / "thread.txt"
    source.parent.mkdir(parents=True)
    source.write_text("captured", encoding="utf-8")
    setup_collector(monkeypatch, lambda *args, **kwargs: {
        "paths": [str(source)], "snapshot_hashes": {str(source): sha256(b"captured").hexdigest()},
        "gaps": [], "threads": []})
    result = collect(cfg)
    assert result["status"] == "captured"
    assert result["paths"] == [".basepack/memory/codex/thread.txt"]
    assert load_collection(cfg, result["receipt"]) == result
    source.write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="snapshot changed"):
        load_collection(cfg, result["receipt"])
    source.unlink()
    with pytest.raises(FileNotFoundError):
        load_collection(cfg, result["receipt"])


def test_collection_freezes_selected_project_roots_and_preserves_default(tmp_path, monkeypatch):
    cfg = config(tmp_path)
    first = "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa"
    second = "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb"
    unselected = "cccccccc-cccc-4ccc-cccc-cccccccccccc"
    roots = [first, second, unselected]
    calls = []

    def capture(project_id, thread_ids, *args, **kwargs):
        calls.append(thread_ids)
        return {"paths": [], "snapshot_hashes": {}, "gaps": [], "threads": []}

    setup_collector(monkeypatch, capture, threads=[
        {"id": thread_id, "projectId": "project"} for thread_id in roots])

    default = collect(cfg)
    limited = collect(cfg, thread_ids=[second, first.upper(), first])

    assert calls == [roots, [second, first]]
    assert "selected_root_thread_ids" not in default
    assert limited["discovered"] == 3
    assert load_collection(cfg, limited["receipt"])["selected_root_thread_ids"] == [second, first]


def test_collection_rejects_unmatched_requested_roots_before_capture(tmp_path, monkeypatch):
    cfg = config(tmp_path)
    matched = "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa"
    foreign = "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb"
    unresolved = "cccccccc-cccc-4ccc-cccc-cccccccccccc"
    missing = "dddddddd-dddd-4ddd-dddd-dddddddddddd"
    setup_collector(monkeypatch, lambda *args, **kwargs: pytest.fail("Opened chat capture"), threads=[
        {"id": matched, "projectId": "project"},
        {"id": foreign, "projectId": "other"},
        {"id": unresolved},
    ])
    output = tmp_path / "failed.json"
    with pytest.raises(ValueError, match="do not match this project") as error:
        collect(cfg, output=output, thread_ids=[matched, foreign, unresolved, missing])

    assert all(thread_id in str(error.value) for thread_id in (foreign, unresolved, missing))
    assert matched not in str(error.value)
    assert json.loads(output.read_text(encoding="utf-8"))["status"] == "failed"


def test_trial_creation_reservation_drains_and_pauses_formal_collection(tmp_path, monkeypatch):
    from basepack.memory import codex

    cfg = config(tmp_path)
    with _locked(cfg.memory_dir / "collection.lock"):
        with pytest.raises(TimeoutError, match="collection.lock"):
            codex_trial(cfg, "begin")
    assert codex_trial(cfg, "status")["pending_reservation"] is None

    trial = "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa"
    token = codex_trial(cfg, "begin")["pending_reservation"]
    monkeypatch.setattr(codex, "AppServer", lambda *a: pytest.fail("Paused collection opened App Server"))
    with pytest.raises(RuntimeError, match="trial creation reservation is pending"):
        collect(cfg)
    with pytest.raises(RuntimeError, match="trial creation reservation is pending"):
        collect(cfg, thread_ids=[trial])
    with pytest.raises(ValueError, match="already pending"):
        codex_trial(cfg, "begin")
    with pytest.raises(ValueError, match="does not match"):
        codex_trial(cfg, "register", reservation="wrong", thread_id=trial)
    with pytest.raises(ValueError, match="does not match"):
        codex_trial(cfg, "cancel", reservation="wrong")
    assert codex_trial(cfg, "status")["pending_reservation"] == token
    registered = codex_trial(cfg, "register", reservation=token, thread_id=trial.upper())
    assert registered["pending_reservation"] is None
    assert registered["excluded_root_thread_ids"] == [trial]
    assert codex_trial(cfg, "register", reservation=token, thread_id=trial) == registered
    assert json.loads(Path(registered["registry"]).read_text(encoding="utf-8"))["registered"] == {trial: token}

    next_token = codex_trial(cfg, "begin")["pending_reservation"]
    assert codex_trial(cfg, "register", reservation=token, thread_id=trial)["pending_reservation"] == next_token
    assert codex_trial(cfg, "cancel", reservation=next_token) == registered


def test_trial_excludes_descendants_before_export_and_candidate_pins_sibling_scope(tmp_path, monkeypatch):
    from basepack.memory import codex

    formal = config(tmp_path)
    candidate = config(tmp_path)
    candidate.memory_dir = tmp_path / ".basepack" / "candidate"
    business, trial, child, grandchild, late_child, fork, missing_ancestor, orphan, business_child = (
        f"{i}0000000-0000-4000-8000-000000000000" for i in range(1, 10))

    def spawned(parent):
        return {"subAgent": {"thread_spawn": {"parent_thread_id": parent}}}

    threads = {
        business: {"id": business, "projectId": "project"},
        trial: {"id": trial, "projectId": "project", "archived": True},
        child: {"id": child, "cwd": str(tmp_path), "parentThreadId": None, "source": spawned(trial)},
        grandchild: {"id": grandchild, "cwd": str(tmp_path), "source": spawned(child)},
        late_child: {"id": late_child, "cwd": str(tmp_path), "source": spawned(trial)},
        fork: {"id": fork, "projectId": "project", "forkedFromId": grandchild},
        orphan: {"id": orphan, "cwd": str(tmp_path), "source": spawned(missing_ancestor)},
        business_child: {"id": business_child, "cwd": str(tmp_path), "source": spawned(business)},
    }
    references = {
        business: [late_child, business_child],
        trial: [child, late_child],
        child: [grandchild],
    }
    items_read = []

    class Client:
        def __init__(self, executable):
            pass

        def close(self):
            pass

        def call(self, method, params):
            thread_id = params["threadId"]
            if method == "thread/read":
                return {"thread": threads[thread_id]}
            assert method == "thread/items/list"
            items_read.append(thread_id)
            items = [{"turnId": "turn", "item": {"type": "agentMessage", "id": "msg", "text": "example"}}]
            if thread_id in references:
                items.insert(0, {"turnId": "turn", "item": {"type": "collabAgentToolCall", "id": "call",
                                                          "receiverThreadIds": references[thread_id]}})
            return {"data": items[-1:] if params["sortDirection"] == "desc" else items}

    monkeypatch.setattr(codex, "AppServer", Client)
    monkeypatch.setattr(codex, "list_threads", lambda *a, **kw: [
        threads[thread_id] for thread_id in (grandchild, business, trial, fork, child, orphan, business_child)])
    token = codex_trial(formal, "begin")["pending_reservation"]
    codex_trial(formal, "register", reservation=token, thread_id=trial)

    captured = collect(formal)
    assert {Path(path).stem for path in captured["paths"]} == {business, business_child}
    assert set(items_read) == {business, business_child}
    assert {row["thread_id"] for row in captured["excluded"]} == {trial, child, grandchild, fork}
    assert captured["unresolved_threads"] == [{"thread_id": orphan, "reason": "codex_trial_ancestry_unavailable"}]
    assert {"thread_id": late_child, "reason": "registered_codex_trial"} in captured["capture"]["gaps"]
    with pytest.raises(ValueError, match="do not match this project"):
        collect(formal, thread_ids=[business, trial])
    assert set(items_read) == {business, business_child}

    items_read.clear()
    captured = collect(candidate, thread_ids=[trial])
    assert captured["selected_root_thread_ids"] == [trial]
    assert {Path(path).stem for path in captured["paths"]} == {trial, child, grandchild, late_child}
    assert set(items_read) == {trial, child, grandchild, late_child}
    child_export = candidate.memory_dir / "codex" / f"{child}.txt"
    assert json.loads(child_export.read_bytes().splitlines()[0])["parent_thread_id"] == trial
    assert load_collection(candidate, captured["receipt"]) == captured
    with pytest.raises(ValueError, match="receipt belongs to another memory directory"):
        load_collection(formal, captured["receipt"])
    del captured["memory_dir"]
    Path(captured["receipt"]).write_text(json.dumps(captured), encoding="utf-8")
    with pytest.raises(ValueError, match="snapshot belongs to another memory directory"):
        load_collection(formal, captured["receipt"])


def test_collection_records_capture_hash_if_managed_file_changes(tmp_path, monkeypatch):
    cfg = config(tmp_path)
    source = cfg.memory_dir / "codex" / "thread.txt"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"captured")
    digest = sha256(b"captured").hexdigest()
    setup_collector(monkeypatch, lambda *args, **kwargs: {
        "paths": [str(source)], "snapshot_hashes": {str(source): digest},
        "gaps": [], "threads": []}, on_close=lambda: source.write_bytes(b"concurrent"))
    result = collect(cfg, attempt_id=ATTEMPT)
    assert result["snapshots"] == [{"path": ".basepack/memory/codex/thread.txt", "sha256": digest}]
    assert not owner.attempt_control(cfg.memory_dir, ATTEMPT).exists()
    with pytest.raises(ValueError, match="snapshot changed"):
        load_collection(cfg, result["receipt"])


def test_cancelled_attempt_before_app_server_records_failure(tmp_path, monkeypatch):
    from basepack.memory import codex, codex_binding

    cfg = config(tmp_path)
    monkeypatch.setattr(codex_binding, "discover_binding",
                        lambda *args: owner.cancel_attempt(cfg.memory_dir, ATTEMPT))
    monkeypatch.setattr(codex, "AppServer", lambda *args: pytest.fail("Cancelled attempt started App Server"))
    output = tmp_path / "failed.json"
    with pytest.raises(MaintenanceStopped):
        collect(cfg, output=output, attempt_id=ATTEMPT)
    receipt = json.loads(output.read_text(encoding="utf-8"))
    assert receipt["status"] == "failed" and receipt["error"]["type"] == "MaintenanceStopped"
    assert not owner.attempt_control(cfg.memory_dir, ATTEMPT).exists()


def test_cancelled_attempt_before_receipt_publication_records_failure(tmp_path, monkeypatch):
    cfg = config(tmp_path)
    setup_collector(monkeypatch, lambda *args, **kwargs: {
        "paths": [], "snapshot_hashes": {}, "gaps": [], "threads": []},
        on_close=lambda: owner.cancel_attempt(cfg.memory_dir, ATTEMPT))
    output = tmp_path / "failed.json"
    with pytest.raises(MaintenanceStopped):
        collect(cfg, output=output, attempt_id=ATTEMPT)
    receipt = json.loads(output.read_text(encoding="utf-8"))
    assert receipt["status"] == "failed" and receipt["error"]["type"] == "MaintenanceStopped"
    assert not owner.attempt_control(cfg.memory_dir, ATTEMPT).exists()


def test_busy_collection_records_failure_without_starting_app_server(tmp_path, monkeypatch):
    from basepack.memory import codex

    cfg = config(tmp_path)
    monkeypatch.setattr(codex, "AppServer", lambda *args: pytest.fail("Busy collection started App Server"))
    output = tmp_path / "busy.json"
    with _locked(cfg.memory_dir / "collection.lock"):
        output.write_text('{"status":"captured"}', encoding="utf-8")
        with pytest.raises(TimeoutError, match="Another Codex collection is active"):
            collect(cfg, output=output)
    (failure,) = tmp_path.glob("busy-failed-*.json")
    receipt = json.loads(failure.read_text(encoding="utf-8"))
    assert receipt["receipt"] == str(failure)
    assert json.loads(output.read_text(encoding="utf-8")) == {"status": "captured"}
    assert receipt["status"] == "failed" and receipt["error"]["type"] == "TimeoutError"


def test_repeated_attempt_preserves_its_first_collection_receipt(tmp_path, monkeypatch):
    from basepack.memory import codex

    cfg = config(tmp_path)
    setup_collector(monkeypatch, lambda *a, **kw: {"paths": [], "snapshot_hashes": {}, "gaps": [], "threads": []})
    attempt = "f" * 32
    output = tmp_path / "collection.json"
    acquired = collect(cfg, output=output, attempt_id=attempt)
    monkeypatch.setattr(codex, "AppServer", lambda *args: pytest.fail("Repeated attempt started App Server"))

    with pytest.raises(FileExistsError, match="receipt already exists"):
        collect(cfg, output=output, attempt_id=attempt)

    assert load_collection(cfg, output) == acquired


def test_failed_collection_records_receipt_and_preserves_error(tmp_path, monkeypatch):
    cfg = config(tmp_path)
    failure = OSError("collector unavailable")

    def fail(*args, **kwargs):
        raise failure

    setup_collector(monkeypatch, fail)
    with pytest.raises(OSError) as error:
        collect(cfg, output=".basepack/memory/failed.json")
    assert error.value is failure
    receipt = json.loads((cfg.memory_dir / "failed.json").read_text(encoding="utf-8"))
    assert receipt["status"] == "failed"
    assert receipt["error"]["message"] == "collector unavailable"
    with pytest.raises(ValueError, match="did not capture"):
        load_collection(cfg, receipt["receipt"])


def test_collection_rejects_foreign_root_project_and_manifest_escape(tmp_path, monkeypatch):
    cfg = config(tmp_path)
    setup_collector(monkeypatch, lambda *args, **kwargs: {
        "paths": [], "snapshot_hashes": {}, "gaps": [], "threads": []})
    result = collect(cfg)
    with pytest.raises(ValueError, match="another project"):
        load_collection(config(tmp_path, "foreign"), result["receipt"])
    path = Path(result["receipt"])
    result["root"] = str(tmp_path.parent)
    path.write_text(json.dumps(result), encoding="utf-8")
    with pytest.raises(ValueError, match="another project root"):
        load_collection(cfg, path)
    result["root"] = str(tmp_path)
    result["paths"] = ["../foreign"]
    result["snapshots"] = [{"path": "../foreign", "sha256": "invalid"}]
    path.write_text(json.dumps(result), encoding="utf-8")
    with pytest.raises(ValueError, match="leaves project"):
        load_collection(cfg, path)
    with pytest.raises(ValueError, match="leaves project"):
        collect(cfg, output=tmp_path.parent / "foreign.json")


def test_collection_rejects_foreign_explicit_registry_before_opening_app_server(tmp_path, monkeypatch):
    from basepack.memory import codex

    cfg = config(tmp_path)
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps(config(tmp_path, "foreign").raw["memory"]["codex"]), encoding="utf-8")
    monkeypatch.setattr(codex, "AppServer", lambda *args: pytest.fail("Foreign registry started App Server"))
    output = tmp_path / "failed.json"
    with pytest.raises(ValueError, match="configured Codex project ID"):
        collect(cfg, registry, output=output)
    assert json.loads(output.read_text(encoding="utf-8"))["status"] == "failed"


def test_binding_unavailable_and_retained_freshness(tmp_path):
    cfg = config(tmp_path)
    cfg.raw["memory"]["codex"]["registry_complete"] = False
    result = collect(cfg)
    assert result["status"] == "binding_unavailable"
    assert Path(result["receipt"]).is_file()
    with pytest.raises(ValueError, match="requires a complete project binding"):
        collect(cfg, thread_ids=["aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa"])
    assert retained_snapshots(cfg, "project") == {
        "status": "retained", "project_id": "project", "paths": [], "gaps": [],
        "freshness": "unknown"}
