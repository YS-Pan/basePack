"""Native WebSocket transaction regressions; use a disposable SurrealDB server."""

import json

import pytest
import websocket

from basepack.memory.store import PublicationOutcomeUnknown, SqlResponseError, _sql
from basepack.memory import owner
from test_memory_store import batch_for, deterministic_vector, EMBEDDING_IDENTITY, memory


class TracedConnection:
    def __init__(self, delegate, messages, commit_loss=None, before_commit=None):
        self.delegate = delegate
        self.messages = messages
        self.commit_loss = commit_loss
        self.before_commit = before_commit
        self.last_method = None

    def send(self, data):
        message = json.loads(data)
        self.messages.append((message, len(data.encode("utf-8"))))
        self.last_method = message["method"]
        if self.last_method == "commit" and self.before_commit:
            self.before_commit()
        if self.last_method == "commit" and self.commit_loss == "before_send":
            raise OSError("simulated lost commit request")
        return self.delegate.send(data)

    def recv(self):
        response = self.delegate.recv()
        if self.last_method == "commit" and self.commit_loss == "after_response":
            raise OSError("simulated lost commit response")
        return response

    def close(self):
        return self.delegate.close()


def trace(monkeypatch, *, commit_loss=None, before_commit=None):
    messages = []
    create_connection = websocket.create_connection
    monkeypatch.setattr(websocket, "create_connection", lambda *args, **kwargs:
                        TracedConnection(create_connection(*args, **kwargs), messages, commit_loss, before_commit))
    return messages


def test_http_transaction_statement_error_is_a_definite_rollback(memory):
    with pytest.raises(SqlResponseError, match="deliberate HTTP transaction failure"):
        memory._execute("BEGIN; CREATE change:http_failure SET value=1; "
                        "THROW 'deliberate HTTP transaction failure'; COMMIT;")
    assert memory._execute("SELECT * FROM ONLY change:http_failure;")[0] is None


def test_multiple_messages_publish_atomically(memory, monkeypatch):
    messages = trace(monkeypatch)
    value = "数" * 210_000
    memory._publish(["BEGIN;", *[f"CREATE change:item{i} SET payload='{value}';" for i in range(4)], "COMMIT;"])
    queries = [(msg, size) for msg, size in messages if msg["method"] == "query"]
    assert len(queries) >= 2
    assert all(size <= 2112 * 1024 for _, size in queries)
    assert sum(size for _, size in queries) > 2112 * 1024
    assert len({msg["txn"] for msg, _ in queries}) == 1
    rows = memory._execute("SELECT id, string::len(payload) AS size FROM change ORDER BY id;")[0]
    assert [(row["id"], row["size"]) for row in rows] == [
        (f"change:item{i}", len(value)) for i in range(4)]


def test_error_in_later_message_rolls_back_everything(memory, monkeypatch):
    messages = trace(monkeypatch)
    value = "数" * 210_000
    with pytest.raises(RuntimeError, match="deliberate transaction failure"):
        memory._publish(["BEGIN;", *[f"CREATE change:item{i} SET payload='{value}';" for i in range(4)],
                         "THROW 'deliberate transaction failure';", "COMMIT;"])
    assert sum(msg["method"] == "query" for msg, _ in messages) >= 2
    assert any(msg["method"] == "cancel" for msg, _ in messages)
    assert memory._execute("SELECT * FROM change;")[0] == []


def test_single_oversized_statement_is_rejected_before_connecting(memory, monkeypatch):
    messages = trace(monkeypatch)
    with pytest.raises(ValueError, match="One SQL statement exceeds"):
        memory._publish(["BEGIN;", f"CREATE change:large SET payload='{'数' * 740_000}';", "COMMIT;"])
    assert messages == []
    assert memory._execute("SELECT * FROM change;")[0] == []


def test_single_statement_larger_than_600_kib_is_accepted(memory, monkeypatch):
    messages = trace(monkeypatch)
    value = "数" * 210_000
    memory._publish(["BEGIN;", f"CREATE change:large SET payload='{value}';", "COMMIT;"])
    queries = [(msg, size) for msg, size in messages if msg["method"] == "query"]
    assert len(queries) == 1
    assert 600 * 1024 < queries[0][1] <= 2112 * 1024
    assert memory._execute("SELECT string::len(payload) AS size FROM ONLY change:large;")[0]["size"] == len(value)


def test_escaped_one_mib_sql_fits_transport(memory, monkeypatch):
    messages = trace(monkeypatch)
    value = "\\" * 480_000
    statement = f"CREATE change:escaped SET payload={_sql(value)};"
    assert 900 * 1024 < len(statement.encode("utf-8")) < 1024 * 1024
    memory._publish(["BEGIN;", statement, "COMMIT;"])
    queries = [(msg, size) for msg, size in messages if msg["method"] == "query"]
    assert len(queries) == 1
    assert len(statement.encode("utf-8")) * 1.9 < queries[0][1] < 2112 * 1024
    assert memory._execute("SELECT * FROM ONLY change:escaped;")[0]["payload"] == value


@pytest.mark.parametrize("source_count", [1, 2])
def test_public_apply_large_originals_and_vectors(memory, monkeypatch, source_count):
    originals = {f"large{i}.md": f"Line {i}\n" + "数" * 210_000 for i in range(source_count)}
    for path, text in originals.items():
        (memory.config.root / path).write_text(text, encoding="utf-8", newline="")
    prepared = memory.prepare(list(originals))
    members = [{"id": f"large{i}", "kind": "chunk", "path": path, "parent": None,
                "start_line": 1, "end_line": 1, "title": f"Title {i}"}
               for i, path in enumerate(originals)]
    batch = {"sources": [{"path": row["path"], "revision": row["revision"]}
                         for row in prepared["sources"]], "expected": prepared["expected"], "members": members}
    messages = trace(monkeypatch)
    result = memory.apply(batch)
    assert result["sources"] == result["members"] == source_count
    queries = [(msg, size) for msg, size in messages if msg["method"] == "query"]
    assert len(queries) == 1
    if source_count == 2:
        assert queries[0][1] > 1.2 * 1024 * 1024
    snapshots = memory._execute("SELECT path,text FROM source_version ORDER BY path;")[0]
    assert {row["path"]: row["text"] for row in snapshots} == originals
    for i in range(source_count):
        assert memory.read(f"large{i}")["original"]["text"] == f"Line {i}\n"
        member = memory._execute(f"SELECT * FROM ONLY member:large{i};")[0]
        assert member["embedding_identity"] == EMBEDDING_IDENTITY
        assert member["embedding"] == deterministic_vector(f"Title {i}\nLine {i}\n")
        assert member["embedded_revision"] == member["input_revision"]


def test_lost_commit_response_uses_committed_marker(memory, monkeypatch):
    messages = trace(monkeypatch, commit_loss="after_response")
    memory._publish(["BEGIN;", "CREATE change:confirmed SET value=1;", "COMMIT;"])
    assert sum(msg["method"] == "commit" for msg, _ in messages) == 1
    assert memory._execute("SELECT * FROM ONLY change:confirmed;")[0]["value"] == 1


def test_lost_commit_request_is_reported_unknown_without_replay(memory, monkeypatch):
    messages = trace(monkeypatch, commit_loss="before_send")
    with pytest.raises(PublicationOutcomeUnknown, match="outcome unknown"):
        memory._publish(["BEGIN;", "CREATE change:unknown SET value=1;", "COMMIT;"])
    assert sum(msg["method"] == "commit" for msg, _ in messages) == 1
    assert memory._execute("SELECT * FROM ONLY change:unknown;")[0] is None


def test_marker_verification_failure_retains_both_errors(memory, monkeypatch):
    trace(monkeypatch, commit_loss="before_send")
    original_execute = memory._execute
    verification_error = OSError("verification endpoint unavailable")

    def execute(sql, **kwargs):
        if "publication_" in sql:
            raise verification_error
        return original_execute(sql, **kwargs)

    monkeypatch.setattr(memory, "_execute", execute)
    with pytest.raises(PublicationOutcomeUnknown) as raised:
        memory._publish(["BEGIN;", "CREATE change:unconfirmed SET value=1;", "COMMIT;"])
    assert raised.value.verification_error is verification_error
    assert "lost commit request" in str(raised.value.__cause__)


def test_parent_must_exist_and_requires_current_revision(memory):
    text = "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n"
    batch = batch_for(memory, text)
    batch["members"][1]["parent"] = "missing"
    with pytest.raises(RuntimeError, match="Parent member does not exist"):
        memory.apply(batch)
    assert memory._rows("member") == []

    batch = batch_for(memory, text)
    memory.apply(batch)
    prepared = memory.prepare(["guide.md"])
    replacement = dict(batch["members"][2], id="new_child", parent="guide")
    without_parent_revision = dict(prepared["expected"])
    del without_parent_revision["member:guide"]
    with pytest.raises(RuntimeError, match="requires expected revision"):
        memory.apply({"sources": batch["sources"], "expected": without_parent_revision,
                      "members": [replacement]})
    assert all(row["id"] != "member:new_child" for row in memory._rows("member"))
    memory.apply({"sources": batch["sources"], "expected": prepared["expected"],
                  "members": [replacement]})
    assert memory.neighbors("new_child")["parent"]["id"] == "member:guide"


def test_concurrent_parent_change_prevents_child_publication(memory, monkeypatch):
    text = "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n"
    batch = batch_for(memory, text)
    memory.apply(batch)
    prepared = memory.prepare(["guide.md"])
    replacement = dict(batch["members"][2], id="concurrent_child", parent="guide")
    messages = trace(monkeypatch, before_commit=lambda: memory._execute(
        "UPDATE member:guide SET knowledge_revision='concurrent-update';"))
    with pytest.raises(RuntimeError, match="Transaction conflict"):
        memory.apply({"sources": batch["sources"], "expected": prepared["expected"],
                      "members": [replacement]})
    assert sum(msg["method"] == "commit" for msg, _ in messages) == 1
    assert memory._execute("SELECT * FROM ONLY member:concurrent_child;")[0] is None
    assert memory._execute("SELECT * FROM ONLY member:guide;")[0]["knowledge_revision"] == "concurrent-update"


def test_apply_retains_uncertain_publication_owner_and_marker_id(memory, monkeypatch):
    text = "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n"
    batch = batch_for(memory, text)
    memory.apply(batch)
    assert owner.status(memory.config.memory_dir) is None

    prepared = memory.prepare(["guide.md"])
    child = dict(batch["members"][2], id="uncertain_child", parent="guide")
    next_batch = {"sources": batch["sources"], "expected": prepared["expected"], "members": [child]}
    messages = trace(monkeypatch, commit_loss="before_send")
    with pytest.raises(PublicationOutcomeUnknown, match="outcome unknown") as caught:
        memory.apply(next_batch)
    retained = owner.status(memory.config.memory_dir)
    assert retained["stopped"] is True
    assert len(retained["publications"]) == 1
    publication = retained["publications"][0]
    assert f'publication_{publication}' in str(caught.value)
    assert any(f'publication_{publication}' in msg["params"][0]
               for msg, _ in messages if msg["method"] == "query")
    assert memory._execute(f'SELECT * FROM ONLY type::record("meta", "publication_{publication}");')[0] is None
    assert memory._execute("SELECT * FROM ONLY member:uncertain_child;")[0] is None
    assert sum(msg["method"] == "commit" for msg, _ in messages) == 1
    with pytest.raises(RuntimeError, match="already owned"):
        memory.apply(next_batch)
    assert sum(msg["method"] == "commit" for msg, _ in messages) == 1
