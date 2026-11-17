"""Unavailable evidence stays unresolved while exact reviewed gaps stop requeuing."""

from contextlib import contextmanager
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from uuid import uuid4

import pytest

from basepack.memory import feedback, owner
from basepack.memory.draft import compile_proposals, freeze, validate_batch
from basepack.memory.publish import publish
from basepack.memory.store import _record, _sql
from test_memory_history_access import delivery_context
from test_memory_maintenance import memory
from test_memory_store import memory as store_memory


PATH = "private/run.md"
TEXT = "Observed invocation.\nThe original result is unavailable.\nA readable configuration remains.\n"
GAP = "Original result was not retained"
REASON = "Checked the recorded location; the original result is unavailable, so its outcome remains unknown."


# Frozen and natively published by ordinary 0.18.1 on 2026-11-18.
# Producer wheel SHA256: cf8f36029941925d0fa22328810bf5c8d96196ebf18f08243c189d90cd2a7047.
# Preserve the original UUIDs, absent optional fields and CRLF file bytes; never refreeze this sample.
LEGACY_0181_FROZEN = b"""{
  "protocol": 2,
  "batch_id": "66a86762dab347a3965d4273b80772d6",
  "new_members": [
    "member:b40462bb5498464fa38aa6efdae41c3c"
  ],
  "member_mapping": [
    {
      "draft": 0,
      "member": 0,
      "id": "member:b40462bb5498464fa38aa6efdae41c3c"
    }
  ],
  "sources": [
    {
      "path": "private/run.md",
      "revision": "f94469a747b72b48661b7150d3b6f6f2200b5ba7c8ce38c086772800196994dd",
      "private": true
    }
  ],
  "expected": {},
  "members": [
    {
      "kind": "file",
      "path": "private/run.md",
      "start_line": 1,
      "end_line": 3,
      "title": "Observed run; result remains unknown",
      "text": "Invocation observed; no result is claimed.",
      "mandatory": true,
      "coverage_gaps": [
        "Original result was not retained"
      ],
      "id": "member:b40462bb5498464fa38aa6efdae41c3c",
      "evidence": []
    }
  ],
  "privacy_rules": {
    "version": 1,
    "private_scope": []
  },
  "privacy_rules_revision": "379e7175a9c785778369ab32e38bee82b6fa429c5ba967ff234026b2f7663ee9"
}""".replace(b"\n", b"\r\n")
LEGACY_0181_FILE_SHA256 = "c6f0cf30b14b73cc149e2064fb1f8a2ef24d2fdc154104c1a510a66c24bf77cd"
LEGACY_0181_BATCH_HASH = "9866fb7cb826323e8d56260f0ab79079e70f927416b5d5644292d8c6cecac79f"


@contextmanager
def publication_owner(instance):
    control = instance.config.memory_dir / "maintenance" / (uuid4().hex + ".control")
    claim = owner.acquire(instance.config.memory_dir, instance.connection["project_id"], "unavailable-gap test", control)
    assert claim["acquired"]
    try:
        yield str(control)
    finally:
        owner.stop_owned(instance.config.memory_dir, control)
        owner.release(instance.config.memory_dir, control)


def native(instance, identity):
    return instance._execute(f"SELECT * FROM ONLY {_sql(_record(identity))};")[0]


def snapshot(instance, path=PATH):
    source = next(row for row in instance._rows("source") if row["path"] == path)
    return native(instance, source["version"])


def proposal(instance, tmp_path, decisions, *, paths=None, prepared=None, members=None):
    prepared = instance.prepare(paths or [item["path"] for item in decisions]) if prepared is None else prepared
    reading = tmp_path / (uuid4().hex + ".reading.json")
    reading.write_text(json.dumps(prepared, ensure_ascii=False), encoding="utf-8")
    draft = {"prepare": {"path": str(reading), "file_sha256": sha256(reading.read_bytes()).hexdigest()},
             "sources": decisions}
    if members is not None:
        draft["members"] = members
    return draft


def publish_proposal(instance, tmp_path, draft):
    path = tmp_path / (uuid4().hex + ".draft.json")
    path.write_text(json.dumps(draft, ensure_ascii=False), encoding="utf-8")
    frozen = path.with_suffix(".frozen.json")
    result = path.with_suffix(".result.json")
    reference = {"path": str(path), "file_sha256": sha256(path.read_bytes()).hexdigest(), "assignment": "gap-review"}
    with publication_owner(instance) as control:
        published = publish(instance, completed=[reference], output=frozen, result=result, control=control)
    return published, json.loads(frozen.read_text(encoding="utf-8"))


def seed(instance, *, path=PATH, gaps=(GAP,), end_line=3):
    original = instance.config.root / path
    original.parent.mkdir(parents=True, exist_ok=True)
    original.write_bytes(TEXT.encode("utf-8"))
    source = instance.prepare([path])["sources"][0]
    batch = freeze([{"sources": [{"path": path, "revision": source["revision"]}],
                     "members": [{"kind": "file", "path": path, "start_line": 1, "end_line": end_line,
                                  "title": "Observed run; result remains unknown", "text": "Invocation observed; no result is claimed.",
                                  "mandatory": True, "coverage_gaps": list(gaps)}]}], config=instance.config)
    instance.apply(batch)
    return native(instance, batch["members"][0]["id"]), batch


def unavailable(member, gap=GAP):
    return {"member": member["id"], "knowledge_revision": member["knowledge_revision"], "gap": gap, "reason": REASON}


def review(instance, tmp_path, entries, *, path=PATH):
    return publish_proposal(instance, tmp_path, proposal(instance, tmp_path, [{"path": path, "unavailable_gaps": entries}]))


def receipt(instance):
    result = instance.maintain([])
    return result, json.loads(Path(result["receipt"]).read_text(encoding="utf-8"))


def test_review_suppresses_only_exact_gap_without_accepting_unknown_evidence(memory, tmp_path):
    member, _ = seed(memory, gaps=(GAP, "A second unavailable artifact"))
    memory.record_delivery("before-review", [{"id": member["id"], "knowledge_revision": member["knowledge_revision"]}],
                           context=delivery_context())
    before = native(memory, member["id"])
    delivery = memory._execute("SELECT * FROM ONLY meta:delivery;")[0]
    read = memory.read(member["id"])
    first = unavailable(member)
    published, frozen = review(memory, tmp_path, [first])
    assert published["members"] == published["invalidated"] == 0
    assert frozen["expected"][member["id"]] == member["knowledge_revision"]
    assert member["id"] in frozen["dependency_closure"]
    result, material = receipt(memory)
    assert result["needs_semantic"]
    assert material["semantic"][0]["members"][0]["reasons"] == ["coverage_gaps"]

    entries = [first, unavailable(member, "A second unavailable artifact")]
    review(memory, tmp_path, entries)
    assert not receipt(memory)[0]["needs_semantic"]
    assert not receipt(memory)[0]["needs_semantic"]
    assert snapshot(memory)["unavailable_gaps"] == entries
    assert "deferred_refinement" not in snapshot(memory) and "dispositions" not in snapshot(memory)
    assert native(memory, member["id"]) == before  # Includes vectors, exact KV, gaps, mandatory and private.
    assert before["private"] and before["mandatory"] and before["coverage_gaps"] == [GAP, "A second unavailable artifact"]
    assert memory.read(member["id"]) == read
    brief = memory.brief()
    assert next(row for row in brief["coverage_gaps"] if row["id"] == member["id"])["gaps"] == before["coverage_gaps"]
    assert memory._execute("SELECT * FROM ONLY meta:delivery;")[0] == delivery


def test_review_omission_retains_same_raw_lists_replace_or_clear_and_new_raw_starts_unreviewed(memory, tmp_path):
    member, _ = seed(memory, gaps=(GAP, "Another unknown result"))
    first, second = unavailable(member), unavailable(member, "Another unknown result")
    review(memory, tmp_path, [first])
    publish_proposal(memory, tmp_path, proposal(memory, tmp_path, [{"path": PATH}]))
    assert snapshot(memory)["unavailable_gaps"] == [first]
    review(memory, tmp_path, [second])
    assert snapshot(memory)["unavailable_gaps"] == [second]
    review(memory, tmp_path, [])
    assert snapshot(memory)["unavailable_gaps"] == [] and receipt(memory)[0]["needs_semantic"]
    review(memory, tmp_path, [first])
    (memory.config.root / PATH).write_text(TEXT + "New observation.\n", encoding="utf-8")
    publish_proposal(memory, tmp_path, proposal(memory, tmp_path, [{"path": PATH}]))
    assert "unavailable_gaps" not in snapshot(memory)
    assert receipt(memory)[0]["needs_semantic"]


@pytest.mark.parametrize("invalid", ["unknown-member", "wrong-source", "wrong-version", "wrong-gap", "empty-reason", "null-list", "stale", "retired", "unknown-fresh", "changed-raw"])
def test_invalid_unavailable_review_never_writes_source_metadata(memory, tmp_path, invalid):
    member, _ = seed(memory)
    entry = unavailable(member)
    path = PATH
    if invalid == "unknown-member":
        entry["member"] = "member:" + uuid4().hex
    elif invalid == "wrong-source":
        path = "other.md"
        seed(memory, path=path)
    elif invalid == "wrong-version":
        entry["knowledge_revision"] = "not-the-observed-version"
    elif invalid == "wrong-gap":
        entry["gap"] = "Different unresolved question"
    elif invalid == "empty-reason":
        entry["reason"] = " \n "
    elif invalid in {"stale", "retired"}:
        memory._execute(f"UPDATE {_sql(_record(member['id']))} SET {invalid}=true;")
    elif invalid == "unknown-fresh":
        memory._execute(f"UPDATE {_sql(_record(member['id']))} SET stale=NULL;")
    entries = None if invalid == "null-list" else [entry]
    draft = proposal(memory, tmp_path, [{"path": path, "unavailable_gaps": entries}], paths=list(dict.fromkeys([path, PATH])))
    if invalid == "changed-raw":
        (memory.config.root / PATH).write_text("A different invocation.\n", encoding="utf-8")
    before = snapshot(memory, path)
    members = memory._execute("SELECT * FROM member ORDER BY id;")[0]
    with pytest.raises(ValueError):
        publish_proposal(memory, tmp_path, draft)
    assert snapshot(memory, path) == before
    assert memory._execute("SELECT * FROM member ORDER BY id;")[0] == members


def test_fresh_member_keeps_its_historical_source_pin_when_current_snapshot_has_same_raw(memory, tmp_path):
    member, _ = seed(memory)
    old_source_version = member["source_version"]
    # A project policy revision creates a new source snapshot without changing this private source's bytes or marker.
    memory.connection["private_scope"] = ["unrelated.md"]
    publish_proposal(memory, tmp_path, proposal(memory, tmp_path, [{"path": PATH}]))
    current_source = next(row for row in memory._rows("source") if row["path"] == PATH)
    assert current_source["version"] != old_source_version
    assert current_source["revision"] == member["source_revision"]
    assert native(memory, member["id"]) == member
    entry = unavailable(member)
    _, frozen = review(memory, tmp_path, [entry])
    assert frozen["sources"][0]["unavailable_gaps"] == [entry]
    assert native(memory, member["id"])["source_version"] == old_source_version
    assert not receipt(memory)[0]["needs_semantic"]


def test_compiler_rejects_old_gap_pin_after_same_raw_member_gets_a_new_knowledge_version(memory, tmp_path):
    member, _ = seed(memory)
    old = unavailable(member)
    frozen_before_change = compile_proposals(
        [proposal(memory, tmp_path, [{"path": PATH, "unavailable_gaps": [old]}])], config=memory.config)
    replacement = {key: member[key] for key in ("id", "kind", "path", "start_line", "end_line", "text", "mandatory", "coverage_gaps")}
    replacement["title"] = "Revised reading; result still unavailable"
    publish_proposal(memory, tmp_path, proposal(memory, tmp_path, [{"path": PATH}], members=[replacement]))
    current = native(memory, member["id"])
    assert current["knowledge_revision"] != member["knowledge_revision"]
    assert current["source_revision"] == member["source_revision"]
    with pytest.raises(ValueError):
        memory.apply(frozen_before_change)
    assert native(memory, member["id"]) == current
    draft = proposal(memory, tmp_path, [{"path": PATH, "unavailable_gaps": [old]}])
    with pytest.raises(ValueError):
        compile_proposals([draft], config=memory.config)
    assert "unavailable_gaps" not in snapshot(memory)


@pytest.mark.parametrize("pending", ["readable-range", "changed", "stale", "missing", "feedback"])
def test_review_does_not_hide_readable_ranges_or_other_maintenance_work(memory, tmp_path, pending):
    member, _ = seed(memory, end_line=2 if pending == "readable-range" else 3)
    review(memory, tmp_path, [unavailable(member)])
    if pending != "readable-range":
        assert not receipt(memory)[0]["needs_semantic"]
    if pending == "changed":
        (memory.config.root / PATH).write_text("Changed invocation.\n" + TEXT, encoding="utf-8")
    elif pending == "stale":
        memory._execute(f"UPDATE {_sql(_record(member['id']))} SET stale=true;")
    elif pending == "missing":
        (memory.config.root / PATH).unlink()
    elif pending == "feedback":
        report = feedback.report(memory, kind="retrieval", issue="New evidence is missing", query="run result")
    result, material = receipt(memory)
    assert result["needs_semantic"]
    if pending == "feedback":
        assert material["semantic"] == [] and [item["id"] for item in material["feedback"]] == [report["id"]]
    else:
        source = next(item for item in material["semantic"] if item["path"] == PATH)
        if pending == "readable-range":
            assert source["uncovered_ranges"] == [{"start_line": 3, "end_line": 3, "text": "A readable configuration remains.\n"}]
            assert all("coverage_gaps" not in row["reasons"] for row in source["members"])
        else:
            assert any(pending in row["reasons"] for row in source["members"])


def test_unavailable_and_fine_refinement_remain_independent_source_decisions(memory, tmp_path):
    fine_gap = "Coarse reading is sufficient; refine searchable chunks later"
    member, _ = seed(memory, gaps=(GAP, fine_gap))
    fine = {"start_line": 1, "end_line": 3, "reason": "Read all originals; detailed chunking can wait.",
            "gaps": [{"member": member["id"], "knowledge_revision": member["knowledge_revision"], "gap": fine_gap}]}
    publish_proposal(memory, tmp_path, proposal(memory, tmp_path, [{"path": PATH, "deferred_refinement": [fine],
                                                                  "unavailable_gaps": [unavailable(member)]}]))
    assert not receipt(memory)[0]["needs_semantic"]
    assert snapshot(memory)["deferred_refinement"] == [fine]
    review(memory, tmp_path, [])
    assert snapshot(memory)["deferred_refinement"] == [fine]
    assert receipt(memory)[0]["needs_semantic"]
    assert native(memory, member["id"])["coverage_gaps"] == [GAP, fine_gap]


def test_public_source_cannot_store_unavailable_review_of_member_with_private_basis(memory, tmp_path):
    evidence, _ = seed(memory)
    path = "public.md"
    (memory.config.root / path).write_bytes(TEXT.encode("utf-8"))
    _, batch = publish_proposal(memory, tmp_path, proposal(memory, tmp_path, [{"path": path}], paths=[path, PATH], members=[{
        "kind": "file", "path": path, "start_line": 1, "end_line": 3, "text": "Observed invocation; result unknown.",
        "coverage_gaps": [GAP], "evidence": [evidence["id"]]}]))
    member = native(memory, batch["members"][0]["id"])
    before = snapshot(memory, path)
    assert before["private"] is False and member["private"] is True
    with pytest.raises(ValueError):
        review(memory, tmp_path, [unavailable(member)], path=path)
    # Direct frozen admission enforces the same privacy boundary as the proposal compiler.
    frozen = freeze([{"sources": [{"path": path, "revision": before["revision"], "unavailable_gaps": [unavailable(member)]}],
                      "expected": {member["id"]: member["knowledge_revision"]}}], config=memory.config)
    with pytest.raises(ValueError):
        memory.apply(frozen)
    assert snapshot(memory, path) == before
    assert native(memory, member["id"]) == member


def test_legacy_spoofed_private_source_cannot_expose_private_member_gap(memory, tmp_path):
    evidence, _ = seed(memory)
    path = "public.md"
    (memory.config.root / path).write_bytes(TEXT.encode("utf-8"))
    _, batch = publish_proposal(memory, tmp_path, proposal(memory, tmp_path, [{"path": path}], paths=[path, PATH], members=[{
        "kind": "file", "path": path, "start_line": 1, "end_line": 3, "text": "Observed invocation; result unknown.",
        "coverage_gaps": [GAP], "evidence": [evidence["id"]]}]))
    member = native(memory, batch["members"][0]["id"])
    before = snapshot(memory, path)
    assert before["private"] is False and member["private"] is True
    legacy = freeze([{"sources": [{"path": path, "revision": before["revision"],
                                   "unavailable_gaps": [unavailable(member)]}],
                      "expected": {member["id"]: member["knowledge_revision"]}}], config=memory.config)
    legacy.pop("privacy_rules")
    legacy.pop("privacy_rules_revision")
    legacy["sources"][0]["private"] = True
    with pytest.raises(ValueError, match="private member"):
        memory.apply(legacy)
    assert snapshot(memory, path) == before
    assert native(memory, member["id"]) == member
    assert native(memory, "meta:batch_" + legacy["batch_id"]) is None


def test_legacy_public_gap_admission_and_old_batch_replay_use_actual_privacy(memory):
    path = "public.md"
    member, _ = seed(memory, path=path)
    assert member["private"] is False
    source = snapshot(memory, path)
    old = freeze([{"sources": [{"path": path, "revision": source["revision"]}]}], config=memory.config)
    old.pop("privacy_rules")
    old.pop("privacy_rules_revision")
    first = memory.apply(old)
    old_copy = deepcopy(old)
    decision = unavailable(member)
    legacy = freeze([{"sources": [{"path": path, "revision": source["revision"], "unavailable_gaps": [decision]}],
                      "expected": {member["id"]: member["knowledge_revision"]}}], config=memory.config)
    legacy.pop("privacy_rules")
    legacy.pop("privacy_rules_revision")
    legacy["sources"][0]["private"] = True
    memory.apply(legacy)
    reviewed = snapshot(memory, path)
    assert reviewed["private"] is False and reviewed["unavailable_gaps"] == [decision]
    assert memory.apply(old) == first and old == old_copy
    assert snapshot(memory, path) == reviewed


def test_private_to_public_review_needs_semantic_decision_without_blocking_safe_mechanical_work(memory, tmp_path):
    path = "run.md"
    memory.connection["private_scope"] = [path]
    member, _ = seed(memory, path=path)
    safe, _ = seed(memory, path="safe.md", gaps=())
    review(memory, tmp_path, [unavailable(member)], path=path)
    before = snapshot(memory, path)
    memory.connection["private_scope"] = ["safe.md"]
    result, material = receipt(memory)
    pending = next(item for item in material["semantic"] if item["path"] == path)
    assert result["needs_semantic"] and pending["reason"] == "unavailable_gaps_privacy_review"
    assert result["mechanical_batches"] >= 1 and native(memory, safe["id"])["private"] is True
    assert snapshot(memory, path) == before and native(memory, member["id"]) == member
    with pytest.raises(ValueError):
        publish_proposal(memory, tmp_path, proposal(memory, tmp_path, [{"path": path}]))
    with pytest.raises(ValueError):
        review(memory, tmp_path, [unavailable(member)], path=path)
    assert snapshot(memory, path) == before
    review(memory, tmp_path, [], path=path)
    assert snapshot(memory, path)["unavailable_gaps"] == []
    assert snapshot(memory, path)["private"] is False
    assert native(memory, member["id"]) == member


def test_legacy_frozen_hash_and_replay_cannot_erase_later_unavailable_review(memory, tmp_path):
    original = memory.config.root / PATH
    original.parent.mkdir(parents=True)
    original.write_bytes(TEXT.encode("utf-8"))
    assert sha256(LEGACY_0181_FROZEN).hexdigest() == LEGACY_0181_FILE_SHA256
    legacy = json.loads(LEGACY_0181_FROZEN)
    assert "unavailable_gaps" not in legacy["sources"][0]
    legacy_copy = deepcopy(legacy)
    canonical = json.dumps(legacy, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    assert sha256(canonical.encode("utf-8")).hexdigest() == LEGACY_0181_BATCH_HASH
    validate_batch(legacy)
    assert legacy == legacy_copy
    memory.apply(legacy)
    assert legacy == legacy_copy
    member = native(memory, legacy["members"][0]["id"])
    receipt_id = "meta:batch_" + legacy["batch_id"]
    original_receipt = native(memory, receipt_id)
    assert original_receipt["batch_hash"] == sha256(canonical.encode("utf-8")).hexdigest()
    frozen_path = tmp_path / "legacy.frozen.json"
    frozen_path.write_bytes(LEGACY_0181_FROZEN)
    frozen_bytes = frozen_path.read_bytes()
    entries = [unavailable(member)]
    review(memory, tmp_path, entries)
    with publication_owner(memory) as control:
        publish(memory, frozen=frozen_path, result=tmp_path / "legacy.replay.json", control=control)
    assert frozen_path.read_bytes() == frozen_bytes
    assert snapshot(memory)["unavailable_gaps"] == entries
    assert native(memory, receipt_id) == original_receipt
    assert native(memory, member["id"]) == member
    assert not receipt(memory)[0]["needs_semantic"]
