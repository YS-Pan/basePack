"""Access weights for exact versions delivered by a host."""

from hashlib import sha256

from .maintenance import _locked
from .store import PublicationOutcomeUnknown, SqlResponseError, _record, _sql


def _manifest(memory, items, *, verify=True):
    unique = {}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise ValueError("Each delivered item requires an ID and knowledge_revision")
        revision = item.get("knowledge_revision")
        if not isinstance(revision, str) or not revision:
            raise ValueError("Each delivered item requires an ID and knowledge_revision")
        target = _record(item["id"])
        if target.table not in {"member", "node", "semantic"}:
            raise ValueError("Delivered items must be member, node or semantic records")
        if verify:
            # Delivery must resolve the observed version, never the current one.
            version = memory.knowledge(item["id"], knowledge_revision=revision)
            target = _record(version["id"])
            record_id = version["id"]
        else:
            # A hint describes a supplied identity; it does not prove existence.
            record_id = item["id"]
        unique[(target, revision)] = {"id": record_id, "knowledge_revision": revision}
    return [unique[key] for key in sorted(unique, key=lambda key: (_sql(key[0]), key[1]))]


def _state_id(target, revision):
    # Derive the key inside SurrealDB so escaped/native IDs have one identity.
    return ("type::record('access_state', crypto::sha256(<string>"
            f"{_sql(target)} + '\\n' + {_sql(revision)}))")


def _delivery_id(delivery_id):
    return _sql(_record("delivery:" + sha256(delivery_id.encode("utf-8")).hexdigest()))


def _receipt(row, manifest, duplicate):
    if row["items"] != manifest:
        raise ValueError("Delivery ID already exists with a different manifest")
    return {"delivery_id": row["delivery_id"], "event": row["event"],
            "items": row["items"], "context": row.get("context"), "duplicate": duplicate}


def record_delivery(memory, delivery_id, items, context=None):
    """Record one host-confirmed delivery, idempotently by its stable ID."""
    if not isinstance(delivery_id, str) or not delivery_id.strip():
        raise ValueError("delivery_id must be a nonempty string")
    manifest = _manifest(memory, items)
    record = _delivery_id(delivery_id)
    # This lock only serializes local delivery writers. The database transaction
    # also detects conflicting writers that do not share this project directory.
    with _locked(memory.config.memory_dir / "access.lock", timeout=30):
        existing = memory._execute(f"SELECT * FROM ONLY {record};")[0]
        if existing is not None:
            return _receipt(existing, manifest, True)
        statements = ["BEGIN;", f"IF {record}.id != NONE {{ THROW 'Delivery already exists'; }};"]
        if manifest:
            statements.extend(["UPSERT meta:access SET sequence=(sequence ?? 0) + 1;",
                               "LET $event = meta:access.sequence;"])
            for item in manifest:
                target = _record(item["id"])
                revision = item["knowledge_revision"]
                state = _state_id(target, revision)
                statements.append(f"UPSERT {state} SET target={_sql(target)}, "
                                  f"knowledge_revision={_sql(revision)}, "
                                  "hits=(hits ?? 0) + 1, event=$event;")
        else:
            statements.append("LET $event = meta:access.sequence ?? 0;")
        statements.extend([f"CREATE {record} SET delivery_id={_sql(delivery_id)}, "
                           f"items={_sql(manifest)}, context={_sql(context)}, event=$event;", "COMMIT;"])
        try:
            memory._execute("\n".join(statements))
        except Exception as error:
            # A dropped response can follow a committed transaction. Check the
            # stable receipt before allowing the caller to repeat the action.
            try:
                existing = memory._execute(f"SELECT * FROM ONLY {record};")[0]
            except Exception as verification_error:
                unknown = PublicationOutcomeUnknown(
                    f"Delivery outcome unknown; inspect delivery_id {delivery_id!r} before retry")
                unknown.add_note(f"Receipt verification failed: {verification_error!r}")
                raise unknown from error
            if existing is None:
                if isinstance(error, SqlResponseError):
                    raise
                raise PublicationOutcomeUnknown(
                    f"Delivery outcome unknown; inspect delivery_id {delivery_id!r} before retry") from error
            return _receipt(existing, manifest, True)
        try:
            committed = memory._execute(f"SELECT * FROM ONLY {record};")[0]
            if committed is None:
                raise RuntimeError("Committed delivery receipt was not found")
        except Exception as error:
            raise PublicationOutcomeUnknown(
                f"Delivery committed but receipt unavailable; retry with the same delivery_id {delivery_id!r}") from error
        return _receipt(committed, manifest, False)


def access_hints(memory, items):
    """Return each item with the lazily evaluated access state of its version."""
    # Keep caller order and all candidate fields; only normalize for lookup.
    manifest = _manifest(memory, items, verify=False)
    if not manifest:
        return []
    statements = ["BEGIN;", "SELECT * FROM ONLY meta:access;"]
    for item in manifest:
        target = _record(item["id"])
        revision = item["knowledge_revision"]
        statements.extend([f"SELECT * FROM ONLY {_state_id(target, revision)};",
                           f"SELECT born_event FROM knowledge_version WHERE target={_sql(target)} "
                           f"AND knowledge_revision={_sql(revision)} LIMIT 1;"])
    statements.append("COMMIT;")
    results = memory._execute("\n".join(statements))
    current = (results[1] or {}).get("sequence", 0)
    hints = {}
    for index, item in enumerate(manifest):
        state, versions = results[2 + 2 * index:4 + 2 * index]
        born = versions[0].get("born_event", 0) if versions else 0
        hits = state["hits"] if state else 0
        event = state["event"] if state else born
        stability = 8 * (1 + hits)
        hints[(_record(item["id"]), item["knowledge_revision"])] = {
            "record_type": _record(item["id"]).table,
            "access_weight": 1 / (1 + (current - event) / stability),
            "access_hits": hits, "access_event": event,
            "access_stability": stability, "access_current_event": current,
        }
    return [{**item, **hints[(_record(item["id"]), item["knowledge_revision"])]} for item in items]
