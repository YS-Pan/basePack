from codecs import BOM_UTF8
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from basepack.memory import graph_review, owner, wave_cli, waves
from basepack.memory.privacy import privacy_rules, rules_revision


def _json(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


@pytest.fixture
def assignment(tmp_path):
    control = tmp_path / "control"
    run = owner.acquire(tmp_path, "project", "parent", control)["owner"]["run_id"]
    endpoints = [
        {"id": f"member:{key * 32}", "knowledge_revision": key + "-knowledge", "path": key + ".md",
         "source_version": "source_version:" + key, "source_revision": key * 64, "kind": "chunk",
         "start_line": 2, "end_line": 4}
        for key in ("a", "b")
    ]
    candidate = {"id": "pair:" + "c" * 64, "endpoints": endpoints, "signals": ["co_delivery"]}
    receipt = _json(tmp_path / "receipt.json", {
        "owner_run_id": run, "layout": {"organization": "finite-wave-v1"},
        "workset": {"included": [row["path"] for row in endpoints]}, "graph_candidates": [candidate],
    })
    return SimpleNamespace(root=tmp_path, control=control, run=run, receipt=receipt, candidate=candidate,
                           endpoints=endpoints, target={"id": "graph", "goal": "Read both", "paths": [],
                           "write_targets": [candidate["id"]], "outputs": ["draft"], "graph_candidate": candidate["id"]})


def _create(case, *other):
    return waves.create(case.root, case.control, case.run, case.receipt, [case.target, *other], ["reader"])


def _start(case, *other):
    state = _create(case, *other)
    args = case.root, case.control, case.run, state["wave_id"]
    waves.started(*args, "reader", "reader-host")
    waves.initialization_receipt(*args)
    waves.seal(*args)
    return args


def _finish(args):
    assert waves.claim(*args, "reader")["retired"]
    waves.notification_pending(*args, "reader")
    waves.notification_result(*args, "reader", accepted=True, result={"host": "accepted"})
    waves.finish(*args)


def _coverage(case, outcome):
    return _json(case.root / "coverage.json", {"graph_review": {
        "candidate": case.candidate["id"], "outcome": outcome,
        "reason": {"proposed": "Can retrieve the supporting passage for the claim.",
                   "nonpersistent": "The comparison only answers the question in this reading.",
                   "no_relation": "The two originals discuss different decisions."}[outcome],
        "read": [{field: row[field] for field in ("id", "knowledge_revision", "source_version")}
                 for row in case.endpoints],
    }})


def _proposal(case):
    endpoints = case.endpoints
    rules = privacy_rules()
    prepared = _json(case.root / "prepare.json", {
        "privacy_rules": rules, "privacy_rules_revision": rules_revision(rules),
        "sources": [{"path": row["path"], "kind": "text", "revision": row["source_revision"],
                     "members": [{**row, "retired": False, "stale": False, "private": False}]}
                    for row in endpoints],
        "expected": {row["id"]: row["knowledge_revision"] for row in endpoints},
        "neighborhood": {"members": [], "nodes": [], "edges": []},
    })
    return {"prepare": waves.fixed_reference(prepared), "sources": [], "edges": [{
        "in": endpoints[0]["id"], "out": endpoints[1]["id"], "type": "supports", "text": "Evidence-backed link",
        "evidence": [row["id"] for row in endpoints],
        "endpoint_versions": {side: {key: row[key] for key in ("id", "knowledge_revision")}
                              for side, row in zip(("in", "out"), endpoints)},
    }]}


def _submit(case, args, *, outcome, draft=None, failed=False):
    errors = _json(case.root / "errors.json", [])
    coverage = _coverage(case, outcome)
    return waves.submit(*args, "reader", "graph", drafts=[draft] if draft else [], coverage=coverage,
                        errors=errors, failed=failed)


def test_only_graph_task_can_claim_pair_and_uses_fixed_read_scope(assignment):
    case = assignment
    unauthorized = {key: value for key, value in case.target.items() if key != "graph_candidate"}
    target = case.target
    case.target = unauthorized
    with pytest.raises(PermissionError, match="pair write target"):
        _create(case)
    case.target = {**target, "graph_candidate": "pair:" + "d" * 64}
    with pytest.raises(PermissionError, match="outside the fixed scope"):
        _create(case)
    case.target = {**target, "read_paths": ["wrong.md"], "expected_revisions": {"wrong.md": "wrong"}}
    state = _create(case)
    assert state["tasks"][0]["read_paths"] == ["a.md", "b.md"]
    assert state["tasks"][0]["expected_revisions"] == {row["path"]: row["source_revision"] for row in case.endpoints}


@pytest.mark.parametrize(("change", "error", "message"), [
    ("node", PermissionError, "one new edge and no other writes"),
    ("retire", PermissionError, "one new edge and no other writes"),
    ("existing", PermissionError, "one new edge and no other writes"),
    ("version", ValueError, "endpoint versions"),
    ("evidence", ValueError, "Relationship evidence must belong to the fixed endpoints"),
    ("outside-basis", PermissionError, "basis must stay within the fixed endpoint versions and ranges"),
])
def test_graph_submission_cannot_write_beyond_its_pair(assignment, change, error, message):
    case = assignment
    args = _start(case)
    waves.claim(*args, "reader")
    draft = _proposal(case)
    edge = draft["edges"][0]
    if change == "node":
        draft["nodes"] = [{"text": "Unassigned node"}]
    elif change == "retire":
        draft["delete_members"] = [case.endpoints[0]["id"]]
    elif change == "existing":
        edge["id"] = "semantic:old"
    elif change == "version":
        edge["endpoint_versions"]["in"]["knowledge_revision"] = "other"
    elif change == "evidence":
        edge["evidence"][0] = "member:" + "f" * 32
    else:
        edge["basis"] = [{"source_version": case.endpoints[0]["source_version"], "start_line": 1, "end_line": 2}]
    with pytest.raises(error, match=message):
        _submit(case, args, outcome="proposed", draft=_json(case.root / "graph.json", draft))
    assert waves.inspect(*args)["tasks"][0]["status"] == "claimed"


@pytest.mark.parametrize("outcome", ["no_relation", "nonpersistent"])
def test_closed_review_without_publication_is_durable_and_failed_is_pending(assignment, outcome):
    case = assignment
    args = _start(case)
    waves.claim(*args, "reader")
    _submit(case, args, outcome=outcome, failed=True)
    _finish(args)
    pending = waves._read_reference(waves.close(*args, no_publication=True)["closure"])["graph_reviews"][0]
    assert pending["outcome"] == "pending" and graph_review.reviewed_pairs(case.root) == set()

    args = _start(case)
    waves.claim(*args, "reader")
    coverage = _coverage(case, outcome)
    wrong = json.loads(coverage.read_text(encoding="utf-8"))
    wrong["graph_review"]["read"][0]["source_version"] = "source_version:wrong"
    _json(coverage, wrong)
    with pytest.raises(ValueError, match="both exact endpoint versions"):
        waves.submit(*args, "reader", "graph", drafts=[], coverage=coverage, errors=case.root / "errors.json")
    _submit(case, args, outcome=outcome)
    assert graph_review.reviewed_pairs(case.root) == set()
    _finish(args)
    closure = waves._read_reference(waves.close(*args, no_publication=True)["closure"])
    assert closure["graph_reviews"][0]["outcome"] == outcome
    assert "edge" not in closure["graph_reviews"][0]
    assert graph_review.reviewed_pairs(case.root) == {case.candidate["id"]}
    with pytest.raises(PermissionError, match="already resolved"):
        _create(case)
    owner.stop_owned(case.root, case.control)
    owner.release(case.root, case.control)
    new_control = case.root / "new-control"
    new_run = owner.acquire(case.root, "project", "parent", new_control)["owner"]["run_id"]
    receipt = json.loads(case.receipt.read_text(encoding="utf-8"))
    new_receipt = _json(case.root / "second-receipt.json", {**receipt, "owner_run_id": new_run})
    with pytest.raises(PermissionError, match="already resolved"):
        waves.create(case.root, new_control, new_run, new_receipt, [case.target], ["reader"])


@pytest.mark.parametrize("citation", ["member", "snapshot"])
def test_review_reads_both_endpoints_and_cites_only_the_establishing_evidence(assignment, citation):
    case = assignment
    args = _start(case)
    waves.claim(*args, "reader")
    draft = _proposal(case)
    edge = draft["edges"][0]
    first, second = edge["evidence"]
    if citation == "member":
        edge["evidence"] = [first]
    else:
        del edge["evidence"]
        edge["basis"] = [{"source_version": case.endpoints[0]["source_version"], "start_line": 2, "end_line": 3}]
    submission = _submit(case, args, outcome="proposed", draft=_json(case.root / "graph.json", draft))
    assert submission["status"] == "submitted"
    coverage = waves._read_reference(submission["result"]["coverage"])
    assert [row["id"] for row in coverage["graph_review"]["read"]] == [first, second]


def _publish_options(case, args):
    return SimpleNamespace(control=args[1], run_id=args[2], wave_id=args[3], timeout=60,
                           frozen=case.root / "frozen.json", result=case.root / "publication.json")


def test_wave_cannot_publish_graph_against_member_rewritten_in_same_batch(assignment, monkeypatch):
    from basepack.memory import store

    case = assignment
    ordinary = {"id": "ordinary", "goal": "Revise member", "paths": ["a.md"], "write_targets": [], "outputs": ["draft"]}
    args = _start(case, ordinary)
    waves.claim(*args, "reader")
    graph = _submit(case, args, outcome="proposed", draft=_json(case.root / "graph.json", _proposal(case)))
    waves.claim(*args, "reader")
    rewrite = _json(case.root / "rewrite.json", {"sources": ["a.md"], "members": [case.endpoints[0]]})
    result = waves.submit(*args, "reader", "ordinary", drafts=[rewrite], coverage=_json(case.root / "ordinary.json", {}),
                          errors=case.root / "errors.json")
    _finish(args)
    selected = [{**row["result"]["drafts"][0], "assignment": row["id"]} for row in (graph, result)]
    monkeypatch.setattr(store, "Memory", lambda *args: pytest.fail("Unauthorized batch reached apply"))
    options = _publish_options(case, args)
    with pytest.raises(ValueError, match="supersede a nominated graph endpoint"):
        wave_cli.publish(SimpleNamespace(memory_dir=case.root), options, selected)
    assert not options.frozen.exists()
    assert not graph_review.reviewed_pairs(case.root)


def test_fixed_prepare_prevents_duplicate_from_earlier_ordinary_wave(assignment, monkeypatch):
    from basepack.memory import store

    case = assignment
    args = _start(case)
    waves.claim(*args, "reader")
    draft = _proposal(case)
    prepared_path = Path(draft["prepare"]["path"])
    prepared = json.loads(prepared_path.read_text(encoding="utf-8"))
    edge = draft["edges"][0]
    prepared["neighborhood"]["edges"] = [{
        key: edge[key] for key in ("in", "out", "type", "endpoint_versions")
    } | {
        "id": "semantic:existing", "stale": False, "retired": False,
        "basis": [{"member": row["id"], "knowledge_revision": row["knowledge_revision"],
                   "source_version": row["source_version"]} for row in case.endpoints],
    }]
    draft["prepare"] = waves.fixed_reference(_json(prepared_path, prepared))
    submitted = _submit(case, args, outcome="proposed", draft=_json(case.root / "graph.json", draft))
    _finish(args)
    selected = [{**submitted["result"]["drafts"][0], "assignment": "graph"}]
    monkeypatch.setattr(store, "Memory", lambda *args: pytest.fail("Duplicate batch reached apply"))
    options = _publish_options(case, args)
    with pytest.raises(ValueError, match="already contains this current graph edge"):
        wave_cli.publish(SimpleNamespace(memory_dir=case.root), options, selected)
    assert not options.frozen.exists()


@pytest.mark.parametrize("different", [{"type": "tests"}, {"conditions": {"fixture": "replay"}}, {}])
def test_mixed_wave_distinguishes_relationships_with_the_same_endpoints(assignment, monkeypatch, different):
    from basepack.memory import store

    case = assignment
    ordinary = {"id": "ordinary", "goal": "Record a relationship during ordinary reading", "paths": [],
                "write_targets": [], "outputs": ["draft"]}
    args = _start(case, ordinary)
    waves.claim(*args, "reader")
    graph_draft = _proposal(case)
    graph = _submit(case, args, outcome="proposed", draft=_json(case.root / "graph.json", graph_draft))
    waves.claim(*args, "reader")
    other_edge = {**graph_draft["edges"][0], **different}
    ordinary_draft = _json(case.root / "ordinary.json", {**graph_draft, "edges": [other_edge]})
    other = waves.submit(*args, "reader", "ordinary", drafts=[ordinary_draft],
                         coverage=_json(case.root / "ordinary-coverage.json", {}), errors=case.root / "errors.json")
    _finish(args)
    selected = [{**row["result"]["drafts"][0], "assignment": row["id"]} for row in (graph, other)]
    config = SimpleNamespace(memory_dir=case.root, raw={"memory": {}})
    options = _publish_options(case, args)
    applied = []

    def apply(batch, **kwargs):
        applied.extend(batch["edges"])
        return {"sources": 0, "members": 0, "nodes": 0, "edges": len(applied), "invalidated": [],
                "edge_versions": {edge["id"]: f"graph_edge:exact_{index}" for index, edge in enumerate(applied)}}

    monkeypatch.setattr(store, "Memory", lambda cfg: SimpleNamespace(config=cfg, apply=apply))
    if different:
        wave_cli.publish(config, options, selected)
        state = waves.close(*args)
        [review] = waves._read_reference(state["closure"])["graph_reviews"]
        assert review["outcome"] == "accepted" and review["edge"] == "graph_edge:exact_0"
        assert len(applied) == 2
    else:
        with pytest.raises(ValueError, match="must contain one new edge"):
            wave_cli.publish(config, options, selected)
        assert applied == []


@pytest.mark.parametrize('bom', [False, True])
def test_frozen_graph_retry_and_committed_pair_are_exact(assignment, monkeypatch, bom):
    from basepack.memory import store

    case = assignment
    args = _start(case)
    waves.claim(*args, "reader")
    draft = _json(case.root / "graph.json", _proposal(case))
    if bom:
        draft.write_bytes(BOM_UTF8 + draft.read_bytes())
    submitted = _submit(case, args, outcome="proposed", draft=draft)
    _finish(args)
    selected = [{**submitted["result"]["drafts"][0], "assignment": "graph"}]
    config = SimpleNamespace(memory_dir=case.root, raw={"memory": {}})
    options = _publish_options(case, args)
    batches = []

    def apply(batch, **kwargs):
        batches.append(batch["batch_id"])
        if len(batches) == 1:
            raise OSError("simulated result unknown")
        return {"sources": 0, "members": 0, "nodes": 0, "edges": 1, "invalidated": [],
                "edge_versions": {batch["edges"][0]["id"]: "graph_edge:exact_retry"}}

    monkeypatch.setattr(store, "Memory", lambda cfg: SimpleNamespace(config=cfg, apply=apply))
    with pytest.raises(OSError, match="result unknown"):
        wave_cli.publish(config, options, selected)
    frozen = json.loads(options.frozen.read_text(encoding="utf-8"))
    assert waves.inspect(*args)["publication"]["status"] == "intent"
    assert not graph_review.reviewed_pairs(case.root)
    (case.root / "prepare.json").unlink()
    for change in ({"text": "Unreviewed wording"},
                   {"basis": [{"source_version": "source_version:unreviewed", "start_line": 1, "end_line": 1}]}):
        _json(options.frozen, {**frozen, "edges": [{**frozen["edges"][0], **change}]})
        with pytest.raises(ValueError, match="Frozen relationship text or evidence changed"):
            wave_cli.publish(config, options, selected)
    _json(options.frozen, frozen)
    assert wave_cli.publish(config, options, selected)["batch_id"] == frozen["batch_id"]
    assert batches == [frozen["batch_id"]] * 2
    state = waves.close(*args)
    review = waves._read_reference(state["closure"])["graph_reviews"][0]
    assert review["outcome"] == "accepted" and review["edge"] == "graph_edge:exact_retry"
    assert graph_review.reviewed_pairs(case.root) == {case.candidate["id"]}
    with pytest.raises(PermissionError, match="already resolved"):
        _create(case)
    owner.stop_owned(case.root, case.control)
    owner.release(case.root, case.control)
    new_control = case.root / "fresh-control"
    new_run = owner.acquire(case.root, "project", "parent", new_control)["owner"]["run_id"]
    receipt = json.loads(case.receipt.read_text(encoding="utf-8"))
    fresh_receipt = _json(case.root / "fresh-receipt.json", {**receipt, "owner_run_id": new_run})
    with pytest.raises(PermissionError, match="already resolved"):
        waves.create(case.root, new_control, new_run, fresh_receipt, [case.target], ["reader"])


@pytest.mark.parametrize("resume", [False, True])
def test_publish_validator_receives_the_batch_applied(assignment, resume):
    from basepack.memory.draft import freeze_file
    from basepack.memory.publish import publish

    case = assignment
    draft = _proposal(case)
    original = _json(case.root / "proposal.json", draft)
    frozen = case.root / "frozen.json"
    config = SimpleNamespace(raw={"memory": {}})
    if resume:
        freeze_file([draft], frozen, config=config)
        arguments = {"frozen": frozen}
    else:
        arguments = {"completed": [{**waves.fixed_reference(original), "assignment": "graph"}], "output": frozen}
    checked = []

    def apply(batch, **kwargs):
        assert checked[0] is batch
        assert len(checked) == 1
        return {"sources": 0, "members": 0, "nodes": 0, "edges": 1, "invalidated": []}

    memory = SimpleNamespace(config=config, apply=apply)
    assert publish(memory, control=case.control, result=case.root / "result.json", batch_validator=checked.append,
                   **arguments)["edges"] == 1


def test_guarded_publication_rejects_changed_fresh_frozen_bytes(assignment, monkeypatch):
    from importlib import import_module

    case = assignment
    publish = import_module("basepack.memory.publish")
    original = _json(case.root / "proposal.json", _proposal(case))
    original_freeze = publish.freeze_file

    def replace_saved_batch(drafts, path, **kwargs):
        compiled = original_freeze(drafts, path, **kwargs)
        _json(path, {**compiled, "edges": []})
        return compiled

    monkeypatch.setattr(publish, "freeze_file", replace_saved_batch)
    config = SimpleNamespace(raw={"memory": {}})
    memory = SimpleNamespace(config=config, apply=lambda *args, **kwargs: pytest.fail("Changed batch reached apply"))
    with pytest.raises(ValueError, match="Frozen batch changed after compilation"):
        publish.publish(memory, completed=[{**waves.fixed_reference(original), "assignment": "graph"}],
                        output=case.root / "frozen.json", control=case.control, result=case.root / "result.json",
                        batch_validator=lambda batch: pytest.fail("Changed batch reached validator"))
