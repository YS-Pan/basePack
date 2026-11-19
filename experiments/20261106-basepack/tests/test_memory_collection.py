from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from basepack.memory import owner
from basepack.memory.collection import collect, load_collection, retained_snapshots
from basepack.memory.maintenance import MaintenanceStopped, _locked


ATTEMPT = "a" * 32


def config(root, project_id="project"):
    return SimpleNamespace(root=root, memory_dir=root / ".basepack" / "memory",
                           raw={"memory": {"codex": {"project_id": project_id,
                                   "registry_complete": True, "other_project_roots": []}}})


def setup_collector(monkeypatch, capture, *, on_close=None):
    from basepack.memory import codex, codex_binding

    class Client:
        def __init__(self, executable):
            self.closed = False

        def close(self):
            self.closed = True
            if on_close is not None:
                on_close()

    monkeypatch.setattr(codex, "AppServer", Client)
    monkeypatch.setattr(codex, "list_threads", lambda client, checkpoint: [{"id": "thread"}])
    monkeypatch.setattr(codex_binding, "discover_binding", lambda *args: {"gaps": []})
    monkeypatch.setattr(codex_binding, "classify_threads", lambda *args: {
        "matched": [{"id": "thread"}], "excluded": [], "unresolved": [], "gaps": []})
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
    assert retained_snapshots(cfg, "project") == {
        "status": "retained", "project_id": "project", "paths": [], "gaps": [],
        "freshness": "unknown"}
