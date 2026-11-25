"""Exercise the ordinary dialogue-index entry against a disposable native database."""

from dataclasses import replace
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess

import pytest

from basepack.memory import codex, codex_index
from basepack.memory.cli import dispatch
from basepack.memory.collection import _write_receipt
from basepack.memory.codex_index_config import open_host
from basepack.memory.retrieval import render_retrieval_prompt
from basepack.memory.store import Memory

from test_memory_cli import _memory_args
from test_memory_codex_index_host import Host, NEW, OLD, TRIAL, item, text_part
from test_memory_store import DeterministicEmbeddingClient, EMBEDDING_IDENTITY, memory


EXTRA = "01a1c568-0e63-7a32-94a4-508ffc4e1159"
DIALOGUE_WRITE = 'UPSERT type::record("codex_thread",'


def _manifest(config):
    old_root = config.root / "old-root"
    old_root.mkdir()
    file = config.root / ".basepack" / "dialogue-allowlist.json"
    file.parent.mkdir(exist_ok=True)
    data = {
        "schema_version": 1,
        "bindings": {
            "old": {"root": str(old_root), "project_id": "old", "other_project_roots": [str(config.root)]},
            "new": {"root": ".", "project_id": "new", "other_project_roots": [str(old_root)]},
        },
        "threads": [_entry(OLD, "old", private=True), _entry(NEW, "new"), _entry(TRIAL, "new")],
        "excluded_thread_ids": [TRIAL],
    }
    config.raw["memory"].update(codex={"project_id": "new"}, source_scope=[],
                                chat_index={"manifest": ".basepack/dialogue-allowlist.json"})
    config.raw["ai"] = {
        "max_concurrent_subagents": 3, "concurrency_source": "test", "retrieval_level": 1,
        "levels": {str(level): {"model": "test", "reasoning_effort": "low"} for level in (1, 2)},
    }
    return file, data


def _entry(thread_id, binding, private=False):
    return {"thread_id": thread_id, "binding": binding, "path": f"dialogues/{binding}/{thread_id}",
            "private": private}


def _run(config, *args):
    result, status = dispatch(_memory_args(*args), config)
    assert status == 0
    return result


def _maintain(config, *, scope=None):
    limit = ("--scope", scope) if scope else ()
    launch = _run(config, "maintain-start", "--holder", "synthetic-parent", "--mode", "manual", *limit)
    prompt = launch["spawn_arguments"]["message"]
    assert "Do not run collect, collect-prompt" in prompt
    command = prompt.split("```text\n")[1].split("\n```")[0]
    assert "maintain" in command and "collect" not in command and "--retained" not in command
    attempt, control = launch["attempt_id"], launch["control"]
    result = _run(config, "maintain", "--holder", "synthetic-parent", "--attempt", attempt,
                  "--control", control, "--mode", "manual", *limit)
    _run(config, "stop", "--attempt", attempt)
    _run(config, "release", "--control", control)
    assert _run(config, "owner") == {"owner": None}
    return result


@pytest.mark.parametrize("revoked", [NEW, OLD])
def test_maintenance_stops_before_next_dialogue_when_thread_or_ancestor_revoked(memory, monkeypatch, revoked):
    config = memory.config
    path, manifest = _manifest(config)
    manifest["threads"][1]["private"] = True
    _write_receipt(path, manifest)
    config.machine.raw["embedding"] = {"endpoint": "http://127.0.0.1:19191"}
    fake = Host()
    fake.close = lambda: None
    fake.metadata[NEW]["forkedFromId"] = OLD
    first, second = "First authorized synthetic message.", "Second synthetic message, revoked before access."
    fake.rows[OLD] = [item("first", "userMessage", content=[text_part(first)])]
    fake.rows[NEW] = [item("second", "userMessage", content=[text_part(second)])]
    seen_inputs = []

    class Encoder(DeterministicEmbeddingClient):
        def embed(self, inputs, *, timeout):
            seen_inputs.extend(inputs)
            return super().embed(inputs, timeout=timeout)

    monkeypatch.setattr(codex, "AppServer", lambda _: fake)
    monkeypatch.setattr(codex_index, "status", lambda _: {"model": {"embedding_identity": EMBEDDING_IDENTITY}})
    monkeypatch.setattr(codex_index, "EmbeddingClient", Encoder)
    publish = Memory._publish
    committed = []

    def revoke_after_first_commit(self, statements, **options):
        publish(self, statements, **options)
        if any(statement.startswith(DIALOGUE_WRITE) for statement in statements):
            committed.append(True)
            remaining = [row for row in manifest["threads"] if row["thread_id"] != revoked]
            _write_receipt(path, dict(manifest, threads=remaining))

    monkeypatch.setattr(Memory, "_publish", revoke_after_first_commit)
    with pytest.raises(RuntimeError, match="dialogue authorization changed"):
        _maintain(config)
    assert committed == [True]
    assert all(params["threadId"] == OLD for _, params in fake.calls)
    assert seen_inputs == [first]
    assert memory._execute("SELECT VALUE thread_id FROM codex_thread; SELECT VALUE thread_id FROM codex_part; "
                           "SELECT VALUE thread_id FROM codex_chunk;") == [[OLD], [OLD], [OLD]]
    assert _run(config, "owner") == {"owner": None}


@pytest.mark.parametrize("failure_only", [False, True], ids=["index", "failure-only"])
def test_maintenance_revocation_after_native_query_cancels_before_commit(memory, monkeypatch, failure_only):
    import websocket

    config = memory.config
    path, manifest = _manifest(config)
    _write_receipt(path, manifest)
    config.machine.raw["embedding"] = {"endpoint": "http://127.0.0.1:19191"}
    fake = Host()
    fake.close = lambda: None
    fake.rows[NEW] = [item("candidate", "userMessage", content=[text_part("Synthetic transaction boundary.")])]
    monkeypatch.setattr(codex, "AppServer", lambda _: fake)
    monkeypatch.setattr(codex_index, "status", lambda _: {"model": {"embedding_identity": EMBEDDING_IDENTITY}})
    monkeypatch.setattr(codex_index, "EmbeddingClient", DeterministicEmbeddingClient)
    tables = "SELECT * FROM codex_thread; SELECT * FROM codex_part; SELECT * FROM codex_chunk;"
    if failure_only:
        _maintain(config, scope="dialogues/new")
        before = memory._execute(tables)
        assert [len(rows) for rows in before] == [1, 1, 1]
        fake.metadata.pop(NEW)
    else:
        before = [[], [], []]
    create_connection = websocket.create_connection
    after_revocation = []
    revoked = False

    class RevokeAfterQuery:
        def __init__(self, *args, **kwargs):
            self.ws = create_connection(*args, **kwargs)
            self.dialogue_query = False

        def send(self, data):
            message = json.loads(data)
            if revoked:
                after_revocation.append(message["method"])
            target = "SET capture_failure=" if failure_only else DIALOGUE_WRITE
            self.dialogue_query = message["method"] == "query" and target in message["params"][0]
            return self.ws.send(data)

        def recv(self):
            nonlocal revoked
            data = self.ws.recv()
            if self.dialogue_query:
                _write_receipt(path, dict(manifest, excluded_thread_ids=[TRIAL, NEW]))
                revoked = True
            return data

        def close(self):
            self.ws.close()

    monkeypatch.setattr(websocket, "create_connection", RevokeAfterQuery)
    with pytest.raises(RuntimeError, match="dialogue authorization changed"):
        _maintain(config, scope="dialogues/new")
    assert revoked and after_revocation == ["cancel"]
    assert memory._execute(tables) == before
    assert _run(config, "owner") == {"owner": None}


def test_dialogue_register_metadata_only_then_ordinary_maintenance(memory, monkeypatch):
    config = memory.config
    path, manifest = _manifest(config)
    path.write_text(json.dumps(manifest), encoding="utf-8")
    original = path.read_bytes()
    config.machine.raw["embedding"] = {"endpoint": "http://127.0.0.1:19191"}
    monkeypatch.setattr(codex_index, "status", lambda _: {"model": {"embedding_identity": EMBEDDING_IDENTITY}})
    monkeypatch.setattr(codex_index, "EmbeddingClient", DeterministicEmbeddingClient)
    fake = Host()
    fake.close = lambda: None
    monkeypatch.setattr(codex, "AppServer", lambda _: fake)

    trial = _run(config, "codex-trial", "begin")
    legacy = config.raw["memory"].pop("codex")
    with pytest.raises(RuntimeError, match="reservation is pending"):
        _run(config, "dialogue-register", EXTRA)
    assert not fake.calls and path.read_bytes() == original
    config.raw["memory"]["codex"] = legacy
    trial_only = "01a1c568-0e63-7a32-94a4-508ffc4e115a"
    _run(config, "codex-trial", "register", "--reservation", trial["pending_reservation"], "--thread", trial_only)
    del config.raw["memory"]["codex"]
    for excluded in (TRIAL, trial_only):
        with pytest.raises(PermissionError, match="Excluded"):
            _run(config, "dialogue-register", excluded)
    with pytest.raises(ValueError, match="current-project binding"):
        _run(config, "dialogue-register", EXTRA, "--binding", "old")
    with pytest.raises(ValueError, match="standard output"):
        _run(config, "dialogue-register", EXTRA, "--output", str(path))
    assert not fake.calls and path.read_bytes() == original

    with pytest.raises(ValueError, match="host_thread_unavailable"):
        _run(config, "dialogue-register", EXTRA)
    ordinary = {"id": EXTRA, "projectId": "new", "cwd": str(config.root), "source": "appServer"}
    rejected = [({"projectId": "other"}, "thread_binding_unverified"),
                ({"cwd": str(config.root.parent)}, "registration_cwd_unverified"),
                ({"forkedFromId": OLD}, "registration_requires_top_level_thread"),
                ({"parentThreadId": trial_only}, "registered_codex_trial"),
                ({"source": "exec"}, "registration_requires_ordinary_thread")]
    for attributes, reason in rejected:
        fake.metadata[EXTRA] = {**ordinary, **attributes}
        with pytest.raises(ValueError, match=reason):
            _run(config, "dialogue-register", EXTRA)
        assert path.read_bytes() == original
    metadata_call = ("thread/read", {"threadId": EXTRA, "includeTurns": False})
    assert fake.calls == [metadata_call] * (len(rejected) + 1)

    fake.metadata[EXTRA] = ordinary
    trial_config = replace(config, raw={**config.raw, "memory": {**config.raw["memory"], "codex": legacy}})
    pending, native_call = [], fake.call

    def reserve_while_verifying(method, params):
        reply = native_call(method, params)
        pending.append(_run(trial_config, "codex-trial", "begin")["pending_reservation"])
        return reply

    with monkeypatch.context() as scoped:
        scoped.setattr(fake, "call", reserve_while_verifying)
        with pytest.raises(RuntimeError, match="reservation is pending"):
            _run(config, "dialogue-register", EXTRA)
    assert fake.calls[-1] == metadata_call and path.read_bytes() == original
    _run(trial_config, "codex-trial", "cancel", "--reservation", pending[0])

    body = "New authorized private test conversation."
    fake.rows[EXTRA] = [item("registered-user", "userMessage", content=[text_part(body)])]
    registered = _run(config, "dialogue-register", EXTRA)
    scope = f"dialogues/current/{EXTRA}"
    row = {"thread_id": EXTRA, "binding": "new", "path": scope, "private": True}
    assert registered == {"status": "registered", "manifest": str(path), **row}
    after = path.read_bytes()
    assert json.loads(after) == dict(manifest, threads=[*manifest["threads"], row])
    assert fake.calls[-1] == metadata_call
    host_calls = len(fake.calls)
    assert _run(config, "dialogue-register", EXTRA, "--binding", "new") == dict(registered, status="already_registered")
    assert path.read_bytes() == after and len(fake.calls) == host_calls

    maintained = _maintain(config, scope=scope)
    assert [(row["thread_id"], row["private"], row["indexed_chunks"])
            for row in maintained["codex"]["threads"]] == [(EXTRA, True, 1)]
    assert body not in Path(maintained["receipt"]).read_text(encoding="utf-8")


def test_ordinary_dialogue_index_and_exact_host_read(memory, monkeypatch):
    config = memory.config
    config.machine.raw["embedding"] = {"endpoint": "http://127.0.0.1:19191"}
    monkeypatch.setattr(codex_index, "status", lambda _: {"model": {"embedding_identity": EMBEDDING_IDENTITY}})
    monkeypatch.setattr(codex_index, "EmbeddingClient", DeterministicEmbeddingClient)
    manifest, data = _manifest(config)
    manifest.write_text(json.dumps(data), encoding="utf-8")
    fake = Host()
    fake.close = lambda: None
    fake.metadata[OLD]["archived"] = True
    fake.metadata[TRIAL] = {"id": TRIAL, "projectId": "new"}
    fake.metadata[EXTRA] = {"id": EXTRA, "projectId": "new"}
    first_text = "Synthetic newer measurement requirement 🧪"
    old_text = "Synthetic archived private dialogue."
    appended = "Synthetic continuation at the end."
    fake.rows[OLD] = [item("old-user", "userMessage", content=[text_part(old_text)])]
    fake.rows[NEW] = [item("new-user", "userMessage", content=[text_part(first_text)])]
    fake.rows[TRIAL] = [item("trial-user", "userMessage", content=[text_part("unavailable trial")])]
    fake.rows[EXTRA] = [item("extra-user", "userMessage", content=[text_part("new approved thread")])]
    monkeypatch.setattr(codex, "AppServer", lambda _: fake)
    legacy = config.memory_dir / "codex" / "legacy.txt"
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_text("not a legacy capture; should never be opened", encoding="utf-8")
    relative = legacy.relative_to(config.root).as_posix()
    for spelling in (relative, "./" + relative, relative.replace("/", "\\")):
        target = config.root / "not-prepared.json"
        with pytest.raises(ValueError, match="retained snapshot"):
            _run(config, "prepare", "--paths", spelling, "--output", str(target))
        assert not target.exists()
    note = config.root / ".basepack" / "allowed-note.md"
    note.write_text("Synthetic ordinary file prepared directly.", encoding="utf-8")
    assert _run(config, "prepare", "--paths", ".basepack/allowed-note.md")["sources"]

    with pytest.raises(ValueError, match="cannot use"):
        _run(config, "maintain-start", "--holder", "synthetic-parent", "--retained")
    with pytest.raises(ValueError, match="unavailable"):
        _run(config, "collect")
    initial = _maintain(config)
    assert initial["codex"]["authorized_threads"] == 2
    rows = {row["thread_id"]: row for row in initial["codex"]["threads"]}
    assert set(rows) == {OLD, NEW}
    assert all(row["covered_messages"] == 1 and row["status"] == "ready" for row in rows.values())
    assert all(params["threadId"] not in {TRIAL, EXTRA} for _, params in fake.calls)
    assert "capture_dir" not in json.loads(Path(initial["receipt"]).read_text(encoding="utf-8"))["codex"]

    coverage = _run(config, "dialogue-coverage")
    assert [row["thread_id"] for row in coverage["threads"]] == [NEW]
    assert len(_run(config, "dialogue-coverage", "--include-private")["threads"]) == 2
    for mode in ("vector", "hybrid"):
        search = _run(config, "search", "--text", first_text, "--mode", mode, "--public-only")
        assert search["dialogue_vector_coverage"]["compatible"] == 1
        assert search["matches"][0]["bookmark"]["thread_id"] == NEW
        assert first_text not in json.dumps(search)
    hit = search["matches"][0]
    node, chunk = hit["id"], hit["dialogue_chunk"]
    assert _run(config, "dialogue-locations", node)["locations"][0]["dialogue_chunk"] == chunk
    assert _run(config, "graph-query", "--seed", node)["seeds"][0]["id"] == node
    original = _run(config, "read", chunk, "--context", "0")
    assert original["original"]["text"] == first_text
    calls_before_denial = len(fake.calls)
    with pytest.raises(ValueError, match="unavailable"):
        _run(config, "read", chunk, "--scope", "unrelated")
    with pytest.raises(ValueError, match="standard output"):
        _run(config, "read", chunk, "--output", str(config.root / "not-written.json"))
    assert len(fake.calls) == calls_before_denial

    data["threads"].append(_entry(EXTRA, "new"))
    manifest.write_text(json.dumps(data), encoding="utf-8")
    fake.metadata[EXTRA]["forkedFromId"] = NEW
    fake.rows[NEW].append(item("continuation", "userMessage", turn="turn-2", content=[text_part(appended)]))
    updated = _maintain(config)
    current = {row["thread_id"]: row for row in updated["codex"]["threads"]}
    assert set(current) == {OLD, NEW, EXTRA} and current[NEW]["node"] == rows[NEW]["node"]
    assert current[NEW]["indexed_chunks"] == 2
    publication = current[NEW]["publication"]
    assert publication["index_statements"] > 0 and publication["index_sql_payload_bytes"] > 0
    repeated = _maintain(config)
    no_writes = {"index_statements": 0, "index_sql_payload_bytes": 0}
    assert repeated["codex"]["threads"] == [
        dict(row, publication=no_writes) for row in updated["codex"]["threads"]
    ]
    native = memory._execute(
        "SELECT * FROM codex_thread; SELECT * FROM codex_part; SELECT * OMIT embedding FROM codex_chunk; "
        "SELECT * FROM node; SELECT * FROM knowledge_version;")
    assert [len(native[index]) for index in (0, 1, 2, 3)] == [3, 4, 4, 3]
    assert all(text not in json.dumps(native, ensure_ascii=False) for text in (old_text, first_text, appended))
    assert list(config.memory_dir.rglob("*.txt")) == [legacy]
    persisted = "".join(path.read_text(encoding="utf-8") for path in config.memory_dir.rglob("*.json"))
    assert all(text not in persisted for text in (old_text, first_text, appended))

    child_query = _run(config, "search", "--text", "new approved thread", "--public-only")
    child = next(row for row in child_query["matches"] if row["bookmark"]["thread_id"] == EXTRA)
    for change in ("private", "removed", "excluded"):
        revised = dict(data, threads=[dict(row) for row in data["threads"]],
                       excluded_thread_ids=list(data["excluded_thread_ids"]))
        if change == "private":
            next(row for row in revised["threads"] if row["thread_id"] == NEW)["private"] = True
        elif change == "removed":
            revised["threads"] = [row for row in revised["threads"] if row["thread_id"] != NEW]
        else:
            revised["excluded_thread_ids"].append(NEW)
        manifest.write_text(json.dumps(revised), encoding="utf-8")
        visible = _run(config, "search", "--text", "new approved thread")
        assert not any(row["bookmark"]["thread_id"] == EXTRA for row in visible["matches"])
        assert _run(config, "graph-query", "--seed", child["id"], "--include-private")["seeds"] == []
        assert not any(row["thread_id"] == EXTRA
                       for row in _run(config, "dialogue-coverage", "--include-private")["threads"])
        before = len(fake.calls)
        with pytest.raises(ValueError, match="unavailable"):
            _run(config, "read", child["dialogue_chunk"], "--include-private")
        assert len(fake.calls) == before
    manifest.write_text(json.dumps(data), encoding="utf-8")

    request = config.root / "request.json"
    request.write_text(json.dumps({"question": "synthetic lookup"}), encoding="utf-8")
    prompt = render_retrieval_prompt(config, request)["prompt"]
    assert "dialogue-coverage" in prompt and "check-codex-capture" not in prompt
    assert "dialogue quotations and neighboring messages out of every saved file" in prompt
    del config.raw["memory"]["chat_index"]
    with pytest.raises(PermissionError, match="disabled"):
        _run(config, "read", chunk)
    assert _run(config, "graph-query", "--seed", node)["seeds"] == []


@pytest.mark.parametrize('spaces', [16_383, 40_000])
def test_registered_dialogue_indexes_whole_part_with_over_limit_whitespace_tail(memory, monkeypatch, spaces):
    config = memory.config
    manifest, data = _manifest(config)
    _write_receipt(manifest, data)
    config.machine.raw["embedding"] = {"endpoint": "http://127.0.0.1:19191"}
    body = "x" + " " * spaces + "\n"
    size = len(body.encode("utf-8"))
    inputs_seen = []

    class RecordingEncoder(DeterministicEmbeddingClient):
        def embed(self, inputs, *, timeout):
            inputs_seen.extend(inputs)
            return super().embed(inputs, timeout=timeout)

    fake = Host()
    fake.close = lambda: None
    fake.metadata[EXTRA] = {"id": EXTRA, "projectId": "new", "cwd": str(config.root), "source": "appServer"}
    fake.rows[EXTRA] = [item("soft-tail", "userMessage", content=[text_part(body)])]
    monkeypatch.setattr(codex, "AppServer", lambda _: fake)
    monkeypatch.setattr(codex_index, "status", lambda _: {"model": {"embedding_identity": EMBEDDING_IDENTITY}})
    monkeypatch.setattr(codex_index, "EmbeddingClient", RecordingEncoder)

    registered = _run(config, "dialogue-register", EXTRA)
    assert registered["status"] == "registered"
    scope = registered["path"]
    maintenance = _maintain(config, scope=scope)
    maintained, = maintenance["codex"]["threads"]
    covered, = _run(config, "dialogue-coverage", "--scope", scope, "--include-private")["threads"]
    for report in (maintained, covered):
        assert report["thread_id"] == EXTRA and report["status"] == "ready"
        assert report["byte_coverage"] == {"observed": size, "nonempty": size, "indexed": size,
                                           "unindexed_content": 0, "whitespace_not_applicable": 0}
        assert report["covered_parts"] == report["covered_messages"] == report["indexed_chunks"] == 1
    assert inputs_seen == [body]

    location, = _run(config, "dialogue-locations", maintained["node"], "--scope", scope,
                     "--include-private")["locations"]
    bookmark = location["bookmark"]
    assert (bookmark["byte_start"], bookmark["byte_end"]) == (0, size)
    assert bookmark["part_sha256"] == sha256(body.encode("utf-8")).hexdigest()
    exact = _run(config, "read", location["dialogue_chunk"], "--scope", scope, "--include-private", "--context", "0")
    assert exact["original"]["text"] == body

    native = memory._execute(
        "SELECT * FROM codex_thread; SELECT * FROM codex_part; SELECT * OMIT embedding FROM codex_chunk; "
        "SELECT * FROM node; SELECT * FROM knowledge_version;")
    original_prefix = body[:256]
    assert original_prefix not in json.dumps([maintained, covered, native])
    assert original_prefix not in Path(maintenance["receipt"]).read_text(encoding="utf-8")
    for path in config.memory_dir.rglob("*.json"):
        assert original_prefix not in path.read_text(encoding="utf-8")


def test_ordinary_dialogue_coverage_reports_native_failure_and_recovers(memory, monkeypatch):
    config = memory.config
    manifest, data = _manifest(config)
    data["threads"].append(_entry(EXTRA, "new"))
    manifest.write_text(json.dumps(data), encoding="utf-8")
    config.machine.raw["embedding"] = {"endpoint": "http://127.0.0.1:19191"}
    monkeypatch.setattr(codex_index, "status", lambda _: {"model": {"embedding_identity": EMBEDDING_IDENTITY}})
    calls = []

    class CountingEncoder(DeterministicEmbeddingClient):
        def embed(self, inputs, *, timeout):
            calls.extend(inputs)
            return super().embed(inputs, timeout=timeout)

    monkeypatch.setattr(codex_index, "EmbeddingClient", CountingEncoder)
    fake = Host()
    fake.close = lambda: None
    body = "Private fixture phrase on the original host."
    fake.rows[NEW] = [item("original", "userMessage", content=[text_part(body)])]
    monkeypatch.setattr(codex, "AppServer", lambda _: fake)

    def rows():
        return {row["thread_id"]: row for row in _run(config, "dialogue-coverage")["threads"]}

    first = _maintain(config, scope="dialogues/new")
    ready = rows()[NEW]
    assert ready["status"] == "ready" and ready["capture_complete"]
    assert ready["cutoff"] == ready["last_successful_cutoff"] == {"turn_id": "turn-1", "item_id": "original"}
    assert rows()[EXTRA] == {"thread_id": EXTRA, "status": "not_indexed"}
    assert not any(row["thread_id"] == EXTRA and row["publication"]["index_statements"]
                   for row in first["codex"]["threads"])
    chunks, = memory._execute("SELECT * FROM codex_chunk;")
    memory._execute("UPDATE codex_thread UNSET coverage.last_successful_cutoff, coverage.message_census; "
                    "UPDATE codex_part SET segment_version=1;")

    metadata = fake.metadata.pop(NEW)
    fake.calls.clear()
    attempt = _maintain(config, scope="dialogues/new")
    unavailable = rows()[NEW]
    assert unavailable["status"] == "capture_unavailable" and not unavailable["capture_complete"]
    assert unavailable["cutoff"] is None and unavailable["parts"] == []
    assert unavailable["message_census"]["host_message_count"] is None
    assert unavailable["capture_failure"]["observed_at"].endswith("+00:00")
    gap = unavailable["capture_gaps"][0]
    assert (gap["reason"], gap["method"]) == ("host_thread_unavailable", "thread/read")
    assert unavailable["last_successful_cutoff"] == ready["cutoff"]
    assert unavailable["retained_index_coverage"]["indexed_chunks"] == 1
    assert unavailable["ancestor_thread_ids"] == ready["ancestor_thread_ids"] == []
    assert rows()[EXTRA]["status"] == "not_indexed"
    assert all(method == "thread/read" for method, _ in fake.calls)
    assert body not in Path(attempt["receipt"]).read_text(encoding="utf-8")
    assert body not in json.dumps(unavailable) and "synthetic missing host thread" not in json.dumps(unavailable)
    assert memory._execute("SELECT * FROM codex_chunk;")[0] == chunks

    fake.metadata[NEW] = metadata
    _maintain(config, scope="dialogues/new")
    assert rows()[NEW] == ready
    assert calls == [body]
    assert memory._execute("SELECT * FROM codex_chunk;")[0] == chunks


def test_maintenance_does_not_record_failure_for_already_revoked_ancestry(memory, monkeypatch):
    config = memory.config
    path, manifest = _manifest(config)
    manifest["threads"][1]["private"] = True
    _write_receipt(path, manifest)
    config.machine.raw["embedding"] = {"endpoint": "http://127.0.0.1:19191"}
    fake = Host()
    fake.close = lambda: None
    fake.metadata[NEW]["forkedFromId"] = OLD
    fake.rows[NEW] = [item("retained", "userMessage", content=[text_part("Authorized synthetic child.")])]
    monkeypatch.setattr(codex, "AppServer", lambda _: fake)
    monkeypatch.setattr(codex_index, "status", lambda _: {"model": {"embedding_identity": EMBEDDING_IDENTITY}})
    monkeypatch.setattr(codex_index, "EmbeddingClient", DeterministicEmbeddingClient)

    indexed, = _maintain(config, scope="dialogues/new")["codex"]["threads"]
    assert indexed["ancestor_thread_ids"] == [OLD]
    saved = memory._execute("SELECT * FROM codex_thread;")
    fake.metadata.pop(NEW)
    remaining = [row for row in manifest["threads"] if row["thread_id"] != OLD]
    _write_receipt(path, dict(manifest, threads=remaining))
    current, = _maintain(config, scope="dialogues/new")["codex"]["threads"]
    assert current["status"] == "capture_unavailable" and current["publication"]["index_statements"] == 0
    assert memory._execute("SELECT * FROM codex_thread;") == saved
    assert not any(row["thread_id"] == NEW for row in _run(config, "dialogue-coverage", "--include-private")["threads"])


def test_ordinary_dialogue_coverage_retains_unreadable_native_message_in_census(memory, monkeypatch):
    config = memory.config
    manifest, data = _manifest(config)
    manifest.write_text(json.dumps(data), encoding="utf-8")
    config.machine.raw["embedding"] = {"endpoint": "http://127.0.0.1:19191"}
    monkeypatch.setattr(codex_index, "status", lambda _: {"model": {"embedding_identity": EMBEDDING_IDENTITY}})
    monkeypatch.setattr(codex_index, "EmbeddingClient", DeterministicEmbeddingClient)
    fake = Host()
    fake.close = lambda: None
    fake.rows[NEW] = [item("first", "userMessage", content=[text_part("known original")]),
                      item("second", "agentMessage", text="known reply"),
                      item("third", "agentMessage", truncated=True)]
    monkeypatch.setattr(codex, "AppServer", lambda _: fake)

    maintained = _maintain(config, scope="dialogues/new")["codex"]["threads"][0]
    observed, = _run(config, "dialogue-coverage")["threads"]
    assert maintained["message_census"] == observed["message_census"]
    census = observed["message_census"]
    assert (census["host_message_count"], census["known_nonempty_messages"], census["unknown_messages"]) == (3, 2, 1)
    assert observed["status"] == "gaps" and observed["nonempty_messages"] == observed["covered_messages"] == 2
    assert observed["last_successful_cutoff"] is None
    assert observed["capture_gaps"][0]["reason"] == "host_text_incomplete"
    assert census["items"][-1] == {"turn_id": "turn-1", "item_id": "third", "role": "assistant",
                                    "readability": "unreadable", "text_status": "unknown", "non_text_parts": 0}
    assert all(body not in json.dumps(observed) for body in ("known original", "known reply"))


def test_prepare_rejects_link_into_retained_codex_root(memory):
    config = memory.config
    manifest, data = _manifest(config)
    manifest.write_text(json.dumps(data), encoding="utf-8")
    directory = config.memory_dir / "codex"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "body.txt").write_text("Synthetic legacy data", encoding="utf-8")
    link = config.root / "other-path"
    try:
        link.symlink_to(directory, target_is_directory=True)
    except OSError as error:
        if getattr(error, "winerror", None) != 1314:
            raise
        created = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
             "$ErrorActionPreference='Stop'; "
             "$null=New-Item -ItemType Junction -Path $env:BASEPACK_TEST_LINK "
             "-Target $env:BASEPACK_TEST_LINK_TARGET"],
            env=os.environ | {"BASEPACK_TEST_LINK": str(link), "BASEPACK_TEST_LINK_TARGET": str(directory)},
            capture_output=True)
        if created.returncode:
            pytest.skip("Windows caller cannot create either test link or junction")
    assert link.resolve() == directory.resolve()
    output = config.root / "not-prepared.json"
    with pytest.raises(ValueError, match="retained snapshot"):
        _run(config, "prepare", "--paths", "other-path/body.txt", "--output", str(output))
    assert not output.exists()


def test_manifest_host_rejects_public_child_of_private_parent(memory, monkeypatch):
    config = memory.config
    manifest, data = _manifest(config)
    manifest.write_text(json.dumps(data), encoding="utf-8")
    fake = Host()
    fake.close = lambda: None
    fake.metadata[NEW]["forkedFromId"] = OLD
    fake.rows[NEW] = [item("child-user", "userMessage", content=[text_part("never opened")])]
    monkeypatch.setattr(codex, "AppServer", lambda _: fake)
    with open_host(config) as host:
        denied = host.capture(NEW)
    assert denied["gaps"][0]["reason"] == "private_ancestry"
    assert all(method == "thread/read" for method, _ in fake.calls)

    data["threads"][1]["private"] = True
    manifest.write_text(json.dumps(data), encoding="utf-8")
    with open_host(config) as host:
        allowed = host.capture(NEW)
    assert allowed["parts"][0]["text"] == "never opened"
