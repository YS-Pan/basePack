"""Match current knowledge to one exact provenance tuple at a time."""

import argparse
import json

import pytest

from basepack.memory import cli
from basepack.memory.draft import freeze
from basepack.memory.store import Memory, _record, _sql
from test_memory_history_access import memory


def anchor(member, knowledge_revision, source_version):
    return {"id": member, "knowledge_revision": knowledge_revision, "source_version": source_version}


def citation(item):
    return {"member": _record(item["id"]), "knowledge_revision": item["knowledge_revision"],
            "source_version": _record(item["source_version"], "source_version")}


@pytest.mark.parametrize("anchors", [{}, [None], [{"id": "member:a", "knowledge_revision": "v1"}],
                                       [anchor("node:a", "v1", "source_version:a")],
                                       [anchor("member:a", "v1", "source:a")]])
def test_basis_dependents_rejects_invalid_anchors_before_database_access(anchors):
    with pytest.raises(ValueError, match="Basis anchor|basis anchor"):
        Memory.__new__(Memory).basis_dependents(anchors)


def test_basis_dependents_accepts_empty_anchor_list_without_database_access():
    assert Memory.__new__(Memory).basis_dependents([]) == []


def test_basis_dependents_cli_matches_current_dependents_and_explicit_historical_evidence(memory, tmp_path):
    a = anchor("member:`a-input`", "a2", "source_version:a2")
    a_old = anchor(a["id"], "a1", "source_version:a1")
    b = anchor("member:b", "b1", "source_version:b1")
    wrong_source = {**a, "source_version": a_old["source_version"]}
    unrelated = anchor("member:c", a["knowledge_revision"], a["source_version"])
    live_a, historic_a, live_b = map(citation, (a, a_old, b))

    def create(record, basis, **fields):
        stored = {"stale": False, "retired": False, "knowledge_revision": "accepted", "basis": basis, **fields}
        return f"CREATE {record} CONTENT {_sql(stored)}; "

    def version(record, revision="accepted"):
        return f"fn::knowledge_id({_sql(_record(record))}, {_sql(revision)})"

    def relate(key, start, end, edge_type, *, owner, status="current", private=False, **fields):
        extra = ", ".join(f"{name}: {_sql(value)}" for name, value in fields.items())
        return (
            f"LET ${key}_state = fn::graph_state({owner}); "
            f"UPSERT ${key}_state SET status = {_sql(status)}; "
            f"INSERT RELATION INTO graph_edge {{id: graph_edge:{key}, in: {start}, out: {end}, "
            f"type: {_sql(edge_type)}, state: ${key}_state, private: {_sql(private)}, "
            f"scope_paths: []{', ' + extra if extra else ''}}}; "
        )

    repository_a = _sql(_record(a["id"]))
    exact_a, exact_a_old, exact_b, exact_c = (version(item["id"], item["knowledge_revision"])
                                              for item in (a, a_old, b, unrelated))
    summary = version("member:summary")
    split = version("member:split_basis")
    stale = version("member:stale")
    retired = version("member:retired")
    archived = version("member:archive_only")
    node = version("node:historical_basis")
    edge = "graph_edge:evidence"
    memory._execute(
        create(repository_a, [], knowledge_revision=a_old["knowledge_revision"], source_version=historic_a["source_version"])
        + f"UPDATE {repository_a} SET knowledge_revision='a2', source_version=source_version:a2; "
        + create("member:b", [], knowledge_revision=b["knowledge_revision"], source_version=live_b["source_version"])
        + create("member:c", [], knowledge_revision=unrelated["knowledge_revision"], source_version=live_a["source_version"])
        + create("member:summary", [live_a, live_b], private=True)
        + create("member:split_basis", [historic_a, citation(unrelated)])
        + create("member:legacy_basis", [{"member": live_a["member"], "source_version": live_a["source_version"]}])
        + create("member:wrong_source", [citation(wrong_source)], stale=True)
        + create("member:stale", [live_a], stale=True)
        + create("member:retired", [live_a], retired=True)
        + create("member:archive_only", [live_a])
        + "UPDATE member:archive_only SET knowledge_revision='replacement', basis=[]; "
        + create("node:historical_basis", [historic_a])
        + relate("summary_a", summary, exact_a, "has_basis", owner=summary, private=True)
        + relate("summary_b", summary, exact_b, "has_basis", owner=summary, private=True)
        + relate("split_a", split, exact_a_old, "has_basis", owner=split)
        + relate("split_c", split, exact_c, "has_basis", owner=split)
        + relate("stale_a", stale, exact_a, "has_basis", owner=stale, status="needs_review")
        + relate("retired_a", retired, exact_a, "has_basis", owner=retired, status="retired")
        + relate("archived_a", archived, exact_a, "has_basis", owner=archived, status="historical")
        + relate("node_a", node, exact_a_old, "has_basis", owner=node)
        + "CREATE semantic:evidence SET head=graph_edge:evidence, stale=false, retired=false, knowledge_revision='edge-v1'; "
        + relate("evidence", summary, exact_b, "supports", owner=edge, private=True, logical_id=_record("semantic:evidence"),
                 knowledge_revision="edge-v1", text="Fixture relation", conditions="")
        + relate("evidence_version", edge, "semantic:evidence", "version_of", owner=edge, private=True)
        + relate("evidence_a", edge, exact_a, "has_basis", owner=edge, private=True)
    )

    parser = argparse.ArgumentParser()
    cli.register_commands(parser.add_subparsers(dest="command", required=True))
    path = tmp_path / "anchors.json"
    requested = [b, a, a]
    path.write_text(json.dumps(requested), encoding="utf-8")
    args = parser.parse_args(["memory", "basis-dependents", "--anchors", str(path)])
    matches, status = cli.dispatch(args, memory.config)
    assert status == 0
    assert matches == memory.basis_dependents(requested)
    assert [(hit["record"]["id"], hit["record"]["record_type"], hit["matched_anchors"]) for hit in matches] == [
        ("member:summary", "member", [b, a]),
        ("semantic:evidence", "semantic", [a]),
    ]
    assert all(hit["record"]["private"] is True for hit in matches)
    assert all("text" not in hit["record"] and "embedding" not in hit["record"] for hit in matches)
    assert matches[0]["record"]["basis"][1]["member"] == b["id"]

    historical = memory.basis_dependents([a_old])
    assert {hit["record"]["id"] for hit in historical} == {"member:split_basis", "node:historical_basis"}
    assert all(hit["matched_anchors"] == [a_old] and "private" not in hit["record"] for hit in historical)
    assert memory.basis_dependents([wrong_source]) == []
    assert memory.basis_dependents([{**a, "knowledge_revision": "unseen"}]) == []


def test_published_basis_dependents_respect_private_provenance_and_anchor_scope(memory, tmp_path):
    sources = {
        "docs/public.md": "Public rule.\nPublic test.\n",
        "elsewhere/public.md": "Additional public evidence.\n",
        "private/basis.md": "Restricted evidence.\n",
    }
    for path, text in sources.items():
        original = memory.config.root / path
        original.parent.mkdir()
        original.write_bytes(text.encode("utf-8"))
    prepared = memory.prepare(list(sources))
    batch = freeze([{
        "sources": [{key: source[key] for key in ("path", "revision")} for source in prepared["sources"]],
        "expected": prepared["expected"],
        "members": [
            {"kind": "chunk", "path": "docs/public.md", "title": "Rule", "start_line": 1, "end_line": 1},
            {"kind": "chunk", "path": "docs/public.md", "title": "Test", "start_line": 2, "end_line": 2},
            {"kind": "chunk", "path": "elsewhere/public.md", "title": "Public evidence", "start_line": 1, "end_line": 1},
        ],
        "edges": [
            {"id": "public_control", "type": "supports", "in": {"member": 1}, "out": {"member": 0},
             "text": "Public test supports the rule.", "evidence": [{"member": 0}, {"member": 2}]},
            {"id": "private_support", "type": "supports", "in": {"member": 1}, "out": {"member": 0},
             "text": "The rule also has restricted supporting evidence.", "evidence": [{"member": 0}],
             "basis": [{"path": "private/basis.md", "start_line": 1, "end_line": 1}]},
        ],
    }])
    memory.apply(batch)
    published = [memory.knowledge(row["id"]) for row in batch["members"]]
    assert all(row["private"] is False for row in published)
    public, outside = [anchor(*(published[index][field] for field in ("id", "knowledge_revision", "source_version")))
                       for index in (0, 2)]
    anchors = [public, outside]

    unrestricted = {hit["record"]["id"]: hit for hit in memory.basis_dependents(anchors)}
    assert set(unrestricted) == {"semantic:public_control", "semantic:private_support"}
    assert unrestricted["semantic:private_support"]["record"]["private"] is True
    assert unrestricted["semantic:private_support"]["matched_anchors"] == [public]
    visible = memory.basis_dependents(anchors, scope="", allow_private=False)
    assert visible == [unrestricted["semantic:public_control"]]
    assert visible[0]["record"]["private"] is False

    parser = argparse.ArgumentParser()
    cli.register_commands(parser.add_subparsers(dest="command", required=True))
    path = tmp_path / "anchors.json"
    path.write_text(json.dumps(anchors), encoding="utf-8")
    options = ["memory", "basis-dependents", "--anchors", str(path), "--public-only"]
    assert cli.dispatch(parser.parse_args(options), memory.config) == (visible, 0)

    scoped = memory.basis_dependents(anchors, scope="docs/", allow_private=False)
    assert len(scoped) == 1
    assert scoped[0]["record"]["id"] == "semantic:public_control"
    assert scoped[0]["matched_anchors"] == [public]
    assert [entry["member"] for entry in scoped[0]["record"]["basis"]] == [public["id"]]
    assert len(scoped[0]["basis_edges"]) == 1
    assert memory.basis_dependents([outside], scope="docs/", allow_private=False) == []
    assert cli.dispatch(parser.parse_args([*options, "--scope", "docs/"]), memory.config) == (scoped, 0)
