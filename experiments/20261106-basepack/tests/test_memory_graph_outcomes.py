import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from basepack.memory import graph_outcomes
from basepack.memory.stages import fixed_reference
from test_memory_store import memory


def _write(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")
    return fixed_reference(path)


def _source(path, revision, modified=1, *, version=None):
    return {"path": path, "revision": revision, "version": version or f"source_version:{revision}",
            "mtime_ns": modified, "private": False}


def _coverage(candidate, status, through, **fields):
    return {"outcome_review": {"candidate": candidate["id"], "revision": candidate["revision"],
                               "source_version": candidate["source_version"],
                               "status": status, "checked_through": through,
                               "reason": "Checked available original evidence.", **fields}}


def _review(tmp_path, candidate, coverage, *, draft=True, published=False):
    task = {"id": "outcome", "outcome_candidate": candidate, "status": "submitted",
            "result": {"drafts": [{"path": "draft", "file_sha256": "hash"}] if draft else [],
                       "coverage": _write(tmp_path / "coverage.json", coverage),
                       "errors": _write(tmp_path / "errors.json", [])}}
    accepted = [{**ref, "assignment": task["id"]} for ref in task["result"]["drafts"]] if published else []
    return graph_outcomes.closure_review({"tasks": [task]}, accepted)


def _checkpoint(maintenance, name, review):
    ref = _write(maintenance / name, {"outcome_review": review})
    return ref, graph_outcomes.checkpoint(review, ref)


def test_outcome_continues_same_chat_after_accepted_draft_then_exhausts(tmp_path):
    path = "codex/chat.txt"
    sources = {path: _source(path, "current")}
    maintenance = tmp_path / "maintenance"
    maintenance.mkdir()

    def nominate():
        return graph_outcomes.nominate(tmp_path, sources, [path], lambda _: 12)

    candidate = nominate()
    assert candidate["start_line"] == 1 and candidate["end_line"] == 12
    review = _review(tmp_path, candidate, _coverage(candidate, "continue", 7), published=True)
    assert review["status"] == "continue"
    reference, checkpoint = _checkpoint(maintenance, "closure-1.json", review)
    _write(maintenance / "wave.json", {"outcome_reviews": {path: checkpoint}})
    resumed = nominate()
    assert resumed["id"] == candidate["id"] and resumed["start_line"] == 8
    assert resumed["previous"] == reference

    review = _review(tmp_path, resumed, _coverage(resumed, "exhausted", 12), draft=False)
    _, checkpoint = _checkpoint(maintenance, "closure-2.json", review)
    _write(maintenance / "wave.json", {"outcome_reviews": {path: checkpoint}})
    assert nominate() is None

    sources[path]["version"] = "source_version:privacy-refreshed"
    changed = nominate()
    assert changed["id"] != candidate["id"] and changed["start_line"] == 1
    assert changed["revision"] == candidate["revision"]


def test_unpublished_outcome_preserves_breakpoint_and_leaves_other_chats_available(tmp_path):
    first, second = "codex/new.txt", "codex/old.txt"
    sources = {first: _source(first, "new", 2), second: _source(second, "old")}
    maintenance = tmp_path / "maintenance"
    maintenance.mkdir()
    candidate = graph_outcomes.nominate(tmp_path, sources, [first, second], lambda _: 20)
    review = _review(tmp_path, candidate, _coverage(candidate, "exhausted", 20))
    assert review["status"] == "retry" and review["resume_line"] == 1
    reference, checkpoint = _checkpoint(maintenance, "closure.json", review)
    _write(maintenance / "wave.json", {"outcome_reviews": {first: checkpoint}})
    assert graph_outcomes.nominate(tmp_path, sources, [first, second], lambda _: 20)["path"] == second
    resumed = graph_outcomes.nominate(tmp_path, sources, [first], lambda _: 20)
    assert resumed["id"] == candidate["id"] and resumed["start_line"] == 1


def test_blocked_outcome_is_deferred_until_its_missing_original_is_accepted(tmp_path):
    path, missing = "codex/chat.txt", "inputs/missing.txt"
    sources = {path: _source(path, "current")}
    maintenance = tmp_path / "maintenance"
    maintenance.mkdir()
    candidate = graph_outcomes.nominate(tmp_path, sources, [path], lambda _: 20)
    review = _review(tmp_path, candidate, _coverage(candidate, "blocked", 5, missing_paths={missing: None}), draft=False)
    reference, checkpoint = _checkpoint(maintenance, "closure.json", review)
    _write(maintenance / "wave.json", {"outcome_reviews": {path: checkpoint}})
    assert graph_outcomes.nominate(tmp_path, sources, [path], lambda _: 20) is None
    sources[missing] = _source(missing, "accepted")
    two_newer = ["codex/new1.txt", "codex/new2.txt"]
    sources.update({other: _source(other, "new", 5) for other in two_newer})
    resumed = graph_outcomes.nominate(tmp_path, sources, [*two_newer, path], lambda _: 20)
    assert resumed["id"] == candidate["id"] and resumed["previous"] == reference
    review = _review(tmp_path, resumed, _coverage(resumed, "blocked", 5, missing_paths={missing: None}), draft=False)
    assert review["missing_paths"] == {missing: None}
    assert review["offered_paths"] == {missing: "source_version:accepted"}
    reference, checkpoint = _checkpoint(maintenance, "closure-reopen.json", review)
    _write(maintenance / "wave.json", {"outcome_reviews": {path: checkpoint}})
    assert graph_outcomes.nominate(tmp_path, sources, [path], lambda _: 20) is None
    assert graph_outcomes.nominate(tmp_path, sources, [*two_newer, path], lambda _: 20)["path"] in two_newer


def test_nomination_reads_original_and_closure_only_for_selected_checkpoint(tmp_path, monkeypatch):
    newer, blocked, selected = "codex/exhausted.txt", "codex/blocked.txt", "codex/continue.txt"
    sources = {path: _source(path, str(index), 3 - index) for index, path in enumerate((newer, blocked, selected))}
    maintenance = tmp_path / "maintenance"
    maintenance.mkdir()
    reviews = {}
    for path, status, through in [(newer, "exhausted", 20), (blocked, "blocked", 3), (selected, "continue", 4)]:
        candidate = graph_outcomes.nominate(tmp_path, sources, [path], lambda _: 20)
        review = _review(tmp_path, candidate, _coverage(candidate, status, through), draft=False)
        _, reviews[path] = _checkpoint(maintenance, status + ".json", review)
    _write(maintenance / "wave.json", {"outcome_reviews": reviews})
    sources.update({path: _source(path, "new", 5) for path in ("codex/new1.txt", "codex/new2.txt")})
    original_reads, closure_reads = [], []
    read_reference = graph_outcomes._read_reference

    def track_reference(reference):
        closure_reads.append(reference)
        return read_reference(reference)

    monkeypatch.setattr(graph_outcomes, "_read_reference", track_reference)
    candidate = graph_outcomes.nominate(tmp_path, sources, sources, lambda path: original_reads.append(path) or 20)
    assert candidate["path"] == selected and candidate["start_line"] == 5
    assert original_reads == [selected] and closure_reads == [reviews[selected]["closure"]]


def test_outcome_grant_is_source_read_only_and_keeps_new_edge_authority(tmp_path):
    path = "codex/chat.txt"
    candidate = graph_outcomes.nominate(tmp_path, {path: _source(path, "current")}, [path], lambda _: 3)
    task = {"id": "outcome", "outcome_candidate": candidate["id"], "paths": [],
            "write_targets": [candidate["id"]]}
    grant = graph_outcomes.grant(task, candidate, set())
    assert grant["read_paths"] == [path] and grant["expected_revisions"] == {path: "current"}
    with pytest.raises(PermissionError, match="already reviewed"):
        graph_outcomes.grant(task, candidate, {candidate["id"]})
    with pytest.raises(PermissionError, match="empty write paths"):
        graph_outcomes.grant({**task, "paths": [path]}, candidate, set())
    with pytest.raises(PermissionError, match="only new relationships"):
        graph_outcomes.validate_draft(grant, {"sources": [], "edges": [{"id": "semantic:existing"}]}, "draft")
    prepare = _write(tmp_path / "prepare.json", {"sources": [{"path": path, "revision": "current",
                     "previous": {"source_version": "source_version:current"}}], "neighborhood": {"edges": []}})
    draft = {"prepare": prepare, "sources": [], "edges": [
        {"in": "member:one", "out": "member:two", "type": kind} for kind in ("derived_from", "uses")]}
    graph_outcomes.validate_draft(grant, draft, "draft")
    with pytest.raises(ValueError, match="Duplicate relationship"):
        graph_outcomes.validate_draft(grant, {**draft, "edges": [draft["edges"][0]] * 2}, "draft")
    wrong = _write(tmp_path / "wrong.json", {"sources": [{"path": path, "revision": "current",
                   "previous": {"source_version": "source_version:other"}}]})
    with pytest.raises(ValueError, match="exact selected chat source version"):
        graph_outcomes.validate_draft(grant, {**draft, "prepare": wrong}, "draft")
    mismatched = _coverage(candidate, "exhausted", 3)
    mismatched["outcome_review"]["revision"] = "another"
    with pytest.raises(ValueError, match="exact revision"):
        graph_outcomes.read_review(grant, _write(tmp_path / "coverage.json", mismatched))


def test_manual_outcome_with_zero_other_work_publishes_and_resumes(memory):
    from basepack.memory import owner, waves
    from basepack.memory.cli import _maintain
    from basepack.memory.draft import freeze
    from basepack.memory.prompts import render_prompt
    from basepack.memory.stages import receipt_scope
    from basepack.memory.wave_cli import publish, task_prompt

    config = memory.config
    codex_project, thread = str(uuid4()), str(uuid4())
    chat = f".basepack/memory/codex/{thread}.txt"
    paths = [[f"{kind}-{number}.txt" for kind in ("accepted", "result", "input")] for number in (1, 2)]
    texts = {name: text for number, (accepted, result, input_) in enumerate(paths, 1) for name, text in
             [(input_, f"input {number}\n"), (result, f"executed from {input_}\n"),
              (accepted, f"delivered {result}\n")]}
    body = "".join(texts.values()).rstrip("\n")
    header = {"project_id": codex_project, "thread_id": thread, "byte_length": len(body.encode())}
    texts[chat] = json.dumps(header) + "\n" + body + "\n"
    for path, text in texts.items():
        target = config.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(text.encode())
    originals = list(texts)
    config.raw["memory"].update(source_scope=originals[:-1], codex={"project_id": codex_project})
    ai = {"model": "fixture", "reasoning_effort": "low"}
    config.raw["ai"] = {"max_concurrent_subagents": 4, "concurrency_source": "fixture",
                        "levels": {"1": ai, "2": ai}}
    prepared = memory.prepare(originals)
    current = {source["path"]: source for source in prepared["sources"]}
    memory.apply(freeze([{"sources": [{"path": chat, "revision": current[chat]["revision"]}],
                         "members": [{"path": chat, "kind": "chunk", "start_line": 1, "end_line": 7}]}], config=config))
    member, = memory._rows("member")
    duplicate = {"kind": "duplicate", "start_line": 1, "end_line": 1, "reason": "Verbatim chat copy",
                 "representations": [{key: member[key] for key in ("id", "knowledge_revision")}]}
    memory.apply(freeze([{"sources": [{"path": path, "revision": current[path]["revision"],
                                      "dispositions": [duplicate]} for path in originals[:-1]],
                          "expected": {member["id"]: member["knowledge_revision"]}}], config=config))
    prepared = memory.prepare(originals)
    versions = {source["path"]: source["previous"]["source_version"] for source in prepared["sources"]}
    references = config.root / ".basepack/diagnostics"
    references.mkdir()

    def preflight(tag):
        control = config.memory_dir / f"maintenance/{tag}.control"
        claim = owner.acquire(config.memory_dir, memory.connection["project_id"], "fixture-parent", control)
        args = SimpleNamespace(mode="manual", scope=None, available_subagents=4,
                               collection=None, retained=True, timeout=45)
        assessment = _maintain(config, args, claim, memory=memory)
        material = json.loads(Path(assessment["receipt"]).read_bytes())
        for field in ("changes", "semantic", "pending_relations", "feedback", "graph_candidates"):
            assert material[field] == []
        return control, assessment, material.get("outcome_candidate")

    def release(control):
        owner.stop_owned(config.memory_dir, control)
        owner.release(config.memory_dir, control)
        assert owner.status(config.memory_dir) is None

    def wave(tag, group, status, through, *, reject=None):
        control, assessment, candidate = preflight(tag)
        assert assessment["needs_semantic"] and assessment["outcome_candidates"] == 1 and assessment["worker"]
        assert candidate["source_version"] == versions[chat]
        run = assessment["owner"]["run_id"]
        receipt = assessment["receipt"]
        assert candidate["id"] in render_prompt(config, receipt, control)["prompt"]
        assert receipt_scope(json.loads(Path(receipt).read_bytes()))["relations"] == [candidate["id"]]
        root = config.memory_dir
        task = {"id": "discover", "goal": "Read one outcome", "paths": [], "outputs": ["coverage", "draft"],
                "write_targets": [candidate["id"]], "outcome_candidate": candidate["id"]}
        wave_id = waves.create(root, control, run, receipt, [task], ["reader"])["wave_id"]
        waves.started(root, control, run, wave_id, "reader", "actual-test-host-reader")
        waves.initialization_receipt(root, control, run, wave_id)
        waves.seal(root, control, run, wave_id)
        assert waves.claim(root, control, run, wave_id, "reader")["task"]["read_paths"] == [chat]
        assert candidate["revision"] in task_prompt(config, control, run, wave_id, "reader", "discover")["prompt"]
        selected = [chat, *group]
        package = _write(references / f"{tag}-prepare.json", memory.prepare(selected))
        edges = [{"in": versions[left], "out": versions[right], "type": "derived_from",
                  "text": texts[left].strip(), "basis": [{"source_version": versions[left], "start_line": 1, "end_line": 1}]}
                 for left, right in zip(group, group[1:])]
        draft = _write(references / f"{tag}-draft.json", {"prepare": package, "sources": [], "edges": edges})
        coverage = _write(references / f"{tag}-coverage.json", _coverage(candidate, status, through))
        errors = _write(references / f"{tag}-errors.json", [])
        with pytest.raises(ValueError, match="at most one draft"):
            waves.submit(root, control, run, wave_id, "reader", "discover", drafts=[draft["path"]] * 2,
                         coverage=coverage["path"], errors=errors["path"])
        waves.submit(root, control, run, wave_id, "reader", "discover", drafts=[draft["path"]],
                     coverage=coverage["path"], errors=errors["path"])
        assert waves.claim(root, control, run, wave_id, "reader")["retired"]
        waves.notification_pending(root, control, run, wave_id, "reader")
        waves.notification_result(root, control, run, wave_id, "reader", accepted=True, result={"ok": True})
        waves.finish(root, control, run, wave_id)
        completed = [{**draft, "assignment": "discover"}]
        frozen, result = references / f"{tag}-frozen.json", references / f"{tag}-result.json"
        options = SimpleNamespace(control=control, run_id=run, wave_id=wave_id, frozen=frozen, result=result, timeout=45)
        if reject == "duplicate":
            with pytest.raises(ValueError, match="Outcome relationship already current"):
                publish(config, options, completed)
            assert not frozen.exists() and not result.exists()
        elif reject:
            waves.publication_intent(root, control, run, wave_id, drafts=completed, frozen=frozen, result=result)
        else:
            assert publish(config, options, completed)["edges"] == 2
            assert publish(config, options, completed)["status"] == "committed"
        if reject:
            waves.publication_failed(root, control, run, wave_id, error="test definite rejection",
                                     publisher_ended=True, no_commit=True)
        closed = waves.close(root, control, run, wave_id)
        assert waves.close(root, control, run, wave_id) == closed
        review = json.loads(Path(closed["closure"]["path"]).read_bytes())["outcome_review"]
        assert review["status"] == ("retry" if reject else status)
        release(control)
        return candidate

    failed = wave("unpublished", paths[0], "continue", 4, reject="unpublished")
    assert memory._rows("semantic") == []
    first = wave("first", paths[0], "continue", 4)
    edges_after_first = memory._rows("semantic")
    assert failed["id"] == first["id"] and failed["start_line"] == first["start_line"] == 1
    assert len(edges_after_first) == 2
    duplicate = wave("duplicate", paths[0], "exhausted", 7, reject="duplicate")
    assert duplicate["start_line"] == 5 and memory._rows("semantic") == edges_after_first
    second = wave("second", paths[1], "exhausted", 7)
    assert second["id"] == first["id"] and second["start_line"] == 5
    control, assessment, candidate = preflight("check-exhausted")
    assert candidate is None and not assessment["needs_semantic"] and "worker" not in assessment
    release(control)
    current_edges = memory._rows("semantic")
    assert len(current_edges) == 4
    assert {edge["id"] for edge in edges_after_first} <= {edge["id"] for edge in current_edges}
    for group in paths:
        for left, right in zip(group, group[1:]):
            edge, = [edge for edge in current_edges if (edge["in"], edge["out"]) == (versions[left], versions[right])]
            assert edge["type"] == "derived_from" and not edge["stale"] and not edge["retired"]
