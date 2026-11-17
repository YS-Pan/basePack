"""Confirmed immutable delivery facts and access projection entry points."""

from hashlib import sha256
from math import isclose, isfinite

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
        record_id = memory.knowledge(item["id"], knowledge_revision=revision)["id"] if verify else item["id"]
        target = _record(record_id)
        unique[(target, revision)] = {"id": record_id, "knowledge_revision": revision}
    return [unique[key] for key in sorted(unique, key=lambda key: (_sql(key[0]), key[1]))]


def _delivery_id(delivery_id):
    return _sql(_record("delivery:" + sha256(delivery_id.encode("utf-8")).hexdigest()))


def _context(memory, context):
    required = {"anchors", "knowledge_cutoff", "query", "episode", "candidates", "budget", "policy", "model"}
    if not isinstance(context, dict) or not required <= context.keys():
        raise ValueError(f"Delivery context requires {', '.join(sorted(required))}")
    anchors = context["anchors"]
    if not isinstance(anchors, list) or not isinstance(context["candidates"], list):
        raise ValueError("Delivery anchors and candidates must be lists")
    identities = set()
    total = 0.0
    for anchor in anchors:
        if not isinstance(anchor, dict) or "base_quality" not in anchor or "alpha" not in anchor:
            raise ValueError("Each anchor requires identity, alpha and base_quality")
        _manifest(memory, [anchor])
        target = _record(anchor["id"])
        if target in identities:
            raise ValueError("Anchor logical IDs must be unique")
        identities.add(target)
        alpha, quality = anchor["alpha"], anchor["base_quality"]
        if (isinstance(alpha, bool) or not isinstance(alpha, (int, float)) or not isfinite(alpha) or alpha < 0
                or isinstance(quality, bool) or not isinstance(quality, (int, float)) or not isfinite(quality)):
            raise ValueError("Anchor alpha and base_quality must be finite; alpha must be nonnegative")
        total += alpha
    if anchors and (not isclose(total, 1.0, abs_tol=1e-12) or any(
            not isclose(a["alpha"], 1 / len(anchors), abs_tol=1e-12) for a in anchors)):
        raise ValueError("Anchors must have equal shares summing to one")
    return context


def _receipt(row, manifest, context, duplicate):
    if row["items"] != manifest or row.get("context") != context:
        raise ValueError("Delivery ID already exists with different content")
    return {"delivery_id": row["delivery_id"], "j": row["j"],
            "items": row["items"], "context": row["context"], "duplicate": duplicate}


def _completed(memory, row, manifest, context, duplicate):
    receipt = _receipt(row, manifest, context, duplicate)
    from .behavior_projection import compile_behavior
    receipt["projection"] = compile_behavior(memory)
    return receipt


def record_delivery(memory, delivery_id, items, context=None):
    """Append one host-confirmed delivery; projection is a separate operation."""
    if not isinstance(delivery_id, str) or not delivery_id.strip():
        raise ValueError("delivery_id must be a nonempty string")
    manifest = _manifest(memory, items)
    context = _context(memory, context)
    record = _delivery_id(delivery_id)
    with _locked(memory.config.memory_dir / "access.lock", timeout=30):
        existing = memory._execute(f"SELECT * FROM ONLY {record};")[0]
        if existing is not None:
            return _completed(memory, existing, manifest, context, True)
        sql = ("BEGIN; "
               f"IF {record}.id != NONE {{ THROW 'Delivery already exists'; }}; "
               "UPSERT meta:delivery SET j=(j ?? 0) + 1; LET $j = meta:delivery.j; "
               f"CREATE {record} SET delivery_id={_sql(delivery_id)}, items={_sql(manifest)}, "
               f"context={_sql(context)}, j=$j; COMMIT;")
        try:
            memory._execute(sql)
        except Exception as error:
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
            return _completed(memory, existing, manifest, context, True)
        try:
            committed = memory._execute(f"SELECT * FROM ONLY {record};")[0]
            if committed is None:
                raise RuntimeError("Committed delivery receipt was not found")
        except Exception as error:
            raise PublicationOutcomeUnknown(
                f"Delivery committed but receipt unavailable; retry with the same delivery_id {delivery_id!r}") from error
        return _completed(memory, committed, manifest, context, False)


def access_hints(memory, items):
    from .behavior_projection import access_hints as hints
    return hints(memory, items)
