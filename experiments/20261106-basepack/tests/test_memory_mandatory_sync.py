"""Published mandatory knowledge and recovery from changed source evidence."""

from copy import deepcopy
import json

import pytest

from basepack.memory.draft import freeze
from test_memory_maintenance import memory
from test_memory_store import memory as store_memory


OLD_DIRECTION = "本次只迁移，不调整算法、不开展新科学实验。\n"
NEW_DIRECTION = "开展全阵较大正常离散研究，复用已完成的历史实验。\n"
OLD_EVIDENCE = "迁移期间只验证安装与已有计算，不开展新科学实验。\n"
NEW_EVIDENCE = "迁移已结束；现行研究接续较大正常离散与弱模态实验。\n"


def publish_initial(memory):
    for path, text in [("charter.md", OLD_DIRECTION), ("findings.md", OLD_EVIDENCE)]:
        (memory.config.root / path).write_bytes(text.encode("utf-8"))
    prepared = memory.prepare(["charter.md", "findings.md"])
    batch = freeze([direction_batch(prepared, OLD_DIRECTION, accept_evidence=True)])
    memory.apply(batch)
    return deepcopy(memory.read(batch['members'][0]['id'])["member"])


def direction_batch(prepared, direction, *, accept_evidence=False):
    available = [member for source in prepared['sources'] for member in source['members']]
    available += prepared['neighborhood']['members']
    ids = {member['path']: member['id'] for member in available}
    direction_id = ids.get('charter.md', {'member': 0})
    finding_id = ids.get('findings.md', {'member': 1})
    members = [{"kind": "file", "path": "charter.md",
                "start_line": 1, "end_line": 1, "title": "当前纲领", "text": direction,
                "mandatory": True, "evidence": [finding_id]}]
    if isinstance(direction_id, str):
        members[0]['id'] = direction_id
    if accept_evidence:
        members.append({"kind": "chunk", "path": "findings.md",
                        "start_line": 1, "end_line": 1, "title": "迁移与研究边界"})
        if isinstance(finding_id, str):
            members[-1]['id'] = finding_id
    return {"sources": [{"path": item["path"], "revision": item["revision"]}
                        for item in prepared["sources"]],
            "expected": prepared["expected"], "members": members,
            "nodes": [{"id": "direction_basis", "kind": "condition", "text": direction,
                       "evidence": [direction_id, finding_id]}]}


def database_state(memory):
    return {table: sorted(memory._rows(table), key=lambda row: row["id"])
            for table in ("meta", "source", "source_version", "member", "node", "semantic", "change",
                          "knowledge_version", "access_state", "delivery", "feedback")}


def test_source_registration_keeps_old_mandatory_and_semantic_candidate(memory):
    old = publish_initial(memory)
    (memory.config.root / "charter.md").write_bytes(NEW_DIRECTION.encode("utf-8"))
    prepared = memory.prepare(["charter.md"])
    memory.apply(freeze([{"sources": [{"path": "charter.md", "revision": prepared["sources"][0]["revision"]}]}]))

    registered = next(row for row in memory.sources() if row["path"] == "charter.md")
    assert registered["revision"] == prepared["sources"][0]["revision"]
    assert registered["revision"] != old["source_revision"]
    assert memory.changes(["charter.md"], deep=True) == []
    assert memory.read(old['id'])["member"] == old
    brief = memory.brief(limit=0)
    assert brief["mandatory"][0]["text"] == OLD_DIRECTION
    assert brief["mandatory"][0]["stale"] is False
    assert brief["mandatory_pending_count"] == 0
    assert brief["mandatory_known_unsynced_count"] == 1
    assert brief["mandatory"][0]["known_unsynced"] is True
    evidence = brief["mandatory"][0]["sync_evidence"]
    assert evidence["registered_source_revision"] == registered["revision"]
    assert evidence["accepted_source_revision"] == old["source_revision"]

    handoff = memory.maintain([])
    receipt = json.loads(open(handoff["receipt"], encoding="utf-8").read())
    candidate = next(row for row in receipt["semantic"] if row["path"] == "charter.md")
    assert handoff["needs_semantic"]
    assert old['id'] in {row["id"] for row in candidate["members"]}
    assert candidate["uncovered_ranges"][0]["text"] == NEW_DIRECTION
    assert memory.read(old['id'])["member"] == old


def test_conflicting_evidence_requires_explicit_original_and_reacceptance(memory):
    old = publish_initial(memory)
    direction, finding = old['id'], old['basis'][0]['member']
    old_original = memory.read(direction)["original"]
    old_finding = memory.read(finding)["member"]
    for path, text in [("charter.md", NEW_DIRECTION), ("findings.md", NEW_EVIDENCE)]:
        (memory.config.root / path).write_bytes(text.encode("utf-8"))
    # A source-only publication registers bytes without accepting either claim.
    registration = memory.prepare(["charter.md", "findings.md"])
    memory.apply(freeze([{"sources": [{"path": item["path"], "revision": item["revision"]}
                              for item in registration["sources"]]}]))

    for _ in range(2):
        prepared = memory.prepare(["charter.md"])
        assert [row["path"] for row in prepared["sources"]] == ["charter.md"]
        evidence = next(row for row in prepared["neighborhood"]["members"]
                        if row["id"] == finding)
        assert evidence == {key: value for key, value in old_finding.items()
                            if key != "record_type" and not key.startswith("access_")}
        assert prepared["expected"][evidence["id"]] == old_finding["knowledge_revision"]
        draft = freeze([direction_batch(prepared, NEW_DIRECTION)])
        before = database_state(memory)
        with pytest.raises(ValueError, match="Evidence source revision mismatch for findings.md"):
            memory.apply(draft)
        assert database_state(memory) == before
        assert memory.brief(limit=0)["mandatory"][0]["text"] == OLD_DIRECTION

    reread = memory.prepare(["charter.md", "findings.md"])
    findings = next(row for row in reread["sources"] if row["path"] == "findings.md")
    assert NEW_EVIDENCE.strip() in findings["numbered_text"]
    assert OLD_EVIDENCE.strip() in memory.read(finding)["original"]["text"]
    # Preparing the current original alone does not replace old accepted evidence.
    before = database_state(memory)
    with pytest.raises(ValueError, match="Evidence must be reread and accepted"):
        memory.apply(freeze([direction_batch(reread, NEW_DIRECTION)]))
    assert database_state(memory) == before

    memory.apply(freeze([direction_batch(reread, NEW_DIRECTION, accept_evidence=True)]))
    mandatory = memory.brief(limit=0)["mandatory"][0]
    assert mandatory["text"] == NEW_DIRECTION
    assert mandatory["stale"] is False
    assert mandatory["knowledge_revision"] != old["knowledge_revision"]
    assert memory.read(finding)["original"]["text"] == NEW_EVIDENCE
    assert memory.read(direction, source_version=old["source_version"],
                       start_line=1, end_line=1)["original"] == old_original

    # The earlier knowledge revision remains a conflict after successful recovery.
    before = database_state(memory)
    with pytest.raises(RuntimeError, match="Knowledge revision changed"):
        memory.apply(draft)
    assert database_state(memory) == before
    assert memory.brief(limit=0)["mandatory"][0]["text"] == NEW_DIRECTION


def test_brief_keeps_original_changes_unknown_without_reading_files(memory, monkeypatch):
    old = publish_initial(memory)
    (memory.config.root / "charter.md").write_bytes(NEW_DIRECTION.encode("utf-8"))

    def no_original_read(*args, **kwargs):
        pytest.fail("brief must not discover or scan business originals")

    monkeypatch.setattr(memory, "_load_source", no_original_read)
    brief = memory.brief(limit=0)
    assert brief["mandatory"][0]["source_revision"] == old["source_revision"]
    assert brief["mandatory"][0]["text"] == OLD_DIRECTION
    assert brief["mandatory"][0]["stale"] is False
    assert brief["mandatory"][0]["known_unsynced"] is False
    assert brief["mandatory_known_unsynced_count"] == 0
    assert brief["mandatory"][0]["sync_evidence"]["note"] == (
        "Registered source metadata only; originals not checked.")
    assert brief["change_check"] == "not checked by brief; use memory changes for maintenance"


def test_brief_checks_the_accepted_basis_version_after_evidence_reacceptance(memory):
    old = publish_initial(memory)
    finding = old['basis'][0]['member']
    old_evidence = memory.read(finding)["member"]
    (memory.config.root / "findings.md").write_bytes(NEW_EVIDENCE.encode("utf-8"))
    prepared = memory.prepare(["findings.md"])
    source = prepared["sources"][0]
    # Updating evidence independently must not make an old mandatory basis current.
    memory.apply(freeze([{"sources": [{"path": "findings.md", "revision": source["revision"]}],
                  "expected": prepared["expected"], "members": [
                      {"id": finding, "kind": "chunk", "path": "findings.md",
                       "start_line": 1, "end_line": 1, "title": "迁移与研究边界"}]}]))
    mandatory = memory.brief(limit=0)["mandatory"][0]
    assert mandatory["text"] == OLD_DIRECTION
    assert mandatory["source_revision"] == old["source_revision"]
    assert mandatory["known_unsynced"] is True
    evidence = mandatory["sync_evidence"]
    assert evidence["registered_source_revision"] == evidence["accepted_source_revision"]
    mismatch, = evidence["basis_mismatches"]
    assert mismatch["id"] == finding
    assert mismatch["accepted_source_revision"] == old_evidence["source_revision"]
    assert mismatch["registered_source_revision"] == source["revision"]
    assert memory.brief(limit=0)["mandatory_known_unsynced_count"] == 1
