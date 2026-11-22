from hashlib import sha256
import json
from types import SimpleNamespace

import pytest

from basepack.memory.inventory_groups import group_sources
from basepack.memory.inventory_work import grouped_tasks
from basepack.memory.privacy import privacy_rules, rules_revision


@pytest.fixture
def observed(tmp_path):
    config = SimpleNamespace(root=tmp_path, raw={"memory": {"project_id": "pilot"}})
    rows = []
    for path, data in {"a.md": b"same\n", "b.md": b"same\n", "note.md": b"note\n"}.items():
        (tmp_path / path).write_bytes(data)
        rows.append({"path": path, "kind": "text", "status": "available", "private": False,
                     "size": len(data), "revision": sha256(data).hexdigest(),
                     "line_count": 1, "registered": None})
    group_map = {"schema_version": 1, "groups": [{"id": "paper", "members": [
        {"path": row["path"], "revision": row["revision"],
         "role": "notes" if row["path"] == "note.md" else "body"} for row in rows
    ]}]}
    (tmp_path / "map.json").write_text(json.dumps(group_map), encoding="utf-8")
    report = {"project_id": "pilot", "privacy_rules_revision": rules_revision(privacy_rules(config)),
              "sources": rows, "group_map": "map.json", **group_sources(config, rows, group_map)}
    receipt = {"workset": {"included": ["a.md", "b.md"]}, "semantic": [
        {"path": row["path"], "current_revision": row["revision"], "accepted_source_version": None}
        for row in rows[:2]
    ]}
    return config, report, receipt


def test_grouped_wave_uses_one_verified_copy_and_keeps_read_only_scope(observed):
    config, report, receipt = observed
    tasks, grouping = grouped_tasks(config, report, receipt, ["map:public:paper"], read_paths=["note.md"])
    assert tasks[0]["paths"] == ["a.md"]
    assert tasks[0]["read_paths"] == ["note.md"]
    assert set(tasks[0]["expected_revisions"]) == {"a.md", "note.md"}
    assert [alias["path"] for alias in grouping["shared_reading"]] == ["b.md"]
    assert [row["path"] for row in receipt["semantic"]] == ["a.md", "b.md"]


def test_grouped_wave_keeps_existing_maintenance_obligation(observed):
    config, report, receipt = observed
    receipt["semantic"][1]["accepted_source_version"] = "already registered since inventory"
    tasks, grouping = grouped_tasks(config, report, receipt, ["map:public:paper"])
    assert tasks[0]["paths"] == ["a.md", "b.md"]
    assert not grouping["shared_reading"]


def test_grouped_wave_only_writes_remaining_authority(observed):
    config, report, receipt = observed
    tasks, grouping = grouped_tasks(config, report, receipt, ["map:public:paper"],
                                    stage={"remaining": {"paths": ["b.md"]}})
    assert tasks[0]["paths"] == ["b.md"]
    assert not grouping["shared_reading"]


@pytest.mark.parametrize("changed", ["a.md", "note.md", "map.json"])
def test_grouped_wave_rejects_stale_selected_proof(observed, changed):
    config, report, receipt = observed
    target = config.root / changed
    if changed == "map.json":
        data = json.loads(target.read_text(encoding="utf-8"))
        data["groups"][0]["members"][0]["role"] = "different"
        target.write_text(json.dumps(data), encoding="utf-8")
    else:
        target.write_bytes(b"changed\n")
    with pytest.raises(ValueError, match="Inventory differs|grouping changed"):
        grouped_tasks(config, report, receipt, ["map:public:paper"], read_paths=["note.md"])
