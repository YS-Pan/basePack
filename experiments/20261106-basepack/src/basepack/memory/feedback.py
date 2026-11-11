"""Persistent, version-aware reports from memory use."""

from datetime import datetime, timezone
from uuid import uuid4

from .store import SqlResponseError, _record, _sql


def report(memory, *, kind, issue, target=None, observed_revision=None, query=None, source=None, reporter=None):
    if kind not in {"knowledge", "retrieval"}:
        raise ValueError("Feedback kind must be knowledge or retrieval")
    if not issue or not issue.strip():
        raise ValueError("Feedback requires an issue")
    if bool(target) != bool(observed_revision):
        raise ValueError("A target and its observed revision must be supplied together")
    if not target and not (query or source):
        raise ValueError("Feedback without a target requires a query or source clue")
    if target:
        record = _record(target)
        if record.table not in {"member", "node", "semantic"}:
            raise ValueError("Feedback target must be a member, node, or semantic edge")
        target = record
    identifier = _record(uuid4().hex, "feedback")
    content = {"kind": kind, "issue": issue, "observed_revision": observed_revision,
               "query": query, "source": source, "reporter": reporter or "unspecified",
               "reported_at": datetime.now(timezone.utc).isoformat(), "status": "pending"}
    if target:
        content["target"] = target
    # Store the target as a native record ID without re-reading its later revision.
    return memory._execute(f"CREATE {_sql(identifier)} CONTENT {_sql(content)} RETURN AFTER;")[0][0]


def pending(memory):
    return memory._execute("SELECT * FROM feedback WHERE status='pending' ORDER BY reported_at;")[0]


def list_reports(memory, *, all_reports=False):
    if not all_reports:
        return pending(memory)
    return memory._execute("SELECT * FROM feedback ORDER BY reported_at;")[0]


def resolve(memory, identifier, *, outcome, result, control, expected_revision=None):
    if outcome not in {"fixed", "invalid", "duplicate", "obsolete"}:
        raise ValueError("Invalid feedback outcome")
    if not result or not result.strip():
        raise ValueError("Feedback resolution requires a result")
    record = _record(identifier, "feedback")
    if record.table != "feedback":
        raise ValueError("Expected a feedback ID")
    ref = _sql(record)
    # Read the report to learn the target, then check its unchanged pending state
    # and target version within the transaction that closes it.
    rows = memory._execute(f"SELECT * FROM {ref};")[0]
    if not rows:
        raise ValueError("Feedback report does not exist")
    row = rows[0]
    target = row.get("target")
    if bool(target) != bool(expected_revision):
        raise ValueError("Targeted feedback requires the current expected revision; untargeted feedback does not")
    checks = [f"IF {ref}.status != 'pending' {{ THROW 'Feedback is no longer pending'; }};"]
    if target:
        target_ref = _sql(_record(target))
        checks.append(f"IF {target_ref}.id = NONE OR {target_ref}.knowledge_revision != {_sql(expected_revision)} "
                      "{ THROW 'Feedback target revision changed; read and reconsider'; };")
        checks.append(f"IF {ref}.target != {target_ref} {{ THROW 'Feedback target changed'; }};")
        # A read alone does not conflict with a concurrent target update under
        # snapshot isolation. A distinct write forces transaction arbitration.
        guard = "_guard_" + uuid4().hex
        checks.append(f"UPDATE {target_ref} SET {guard}=true RETURN NONE;")
        checks.append(f"UPDATE {target_ref} UNSET {guard} RETURN NONE;")
    resolved_at = datetime.now(timezone.utc).isoformat()
    sql = ("BEGIN;\n" + "\n".join(checks) +
           f"\nUPDATE {ref} SET status='resolved', outcome={_sql(outcome)}, result={_sql(result)}, "
           f"resolved_at={_sql(resolved_at)}, resolved_revision={_sql(expected_revision)} RETURN AFTER;\nCOMMIT;")
    from .owner import begin_publication, finish_publication
    publication = begin_publication(memory.config.memory_dir, control)
    try:
        response = memory._execute(sql)
    except SqlResponseError:
        # A database error response establishes that the transaction failed.
        finish_publication(memory.config.memory_dir, control, publication)
        raise
    finish_publication(memory.config.memory_dir, control, publication)
    return response[-2][0]
