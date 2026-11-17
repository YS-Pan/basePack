import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from basepack.memory.collection import collect, load_collection, retained_snapshots


def config(root, project_id="project"):
    return SimpleNamespace(root=root, memory_dir=root / ".basepack" / "memory",
                           raw={"memory": {"codex": {"project_id": project_id,
                                   "registry_complete": True, "other_project_roots": []}}})


def setup_collector(monkeypatch, capture):
    from basepack.memory import codex, codex_binding

    class Client:
        def __init__(self, executable):
            self.closed = False

        def close(self):
            self.closed = True

    monkeypatch.setattr(codex, "AppServer", Client)
    monkeypatch.setattr(codex, "list_threads", lambda client, control: [{"id": "thread"}])
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
        "paths": [str(source)], "gaps": [], "threads": []})
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
    setup_collector(monkeypatch, lambda *args, **kwargs: {"paths": [], "gaps": [], "threads": []})
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


def test_binding_unavailable_and_retained_freshness(tmp_path):
    cfg = config(tmp_path)
    cfg.raw["memory"]["codex"]["registry_complete"] = False
    result = collect(cfg)
    assert result["status"] == "binding_unavailable"
    assert Path(result["receipt"]).is_file()
    assert retained_snapshots(cfg, "project") == {
        "status": "retained", "project_id": "project", "paths": [], "gaps": [],
        "freshness": "unknown"}
