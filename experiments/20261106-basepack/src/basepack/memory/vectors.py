"""Encode accepted members using the existing shared service; query native SQL."""

from hashlib import sha256
from urllib.error import HTTPError

from basepack.embedding.client import EmbeddingClient
from basepack.embedding.admin import status
from basepack.embedding.qwen3_vl import MAX_REQUEST_INPUTS
from .dialogue_query import INDEX_VERSION_QUERY, _LOCATION_FIELDS, chunk_filter, legacy_path_tests
from .store import _CANDIDATE_OMIT, _record, _sql


def embed_members(memory, ids=None, *, timeout=600) -> dict:
    identity = status(memory.config.machine)["model"]["embedding_identity"]
    selected = "" if ids is None else f" AND id IN {_sql([_record(value) for value in ids])}"
    scope = f"stale=false AND retired!=true{selected}"
    members, compatible = memory._execute(
        f"SELECT * OMIT embedding FROM member WHERE {scope}; "
        f"SELECT VALUE id FROM member WHERE {scope} AND embedding_identity={_sql(identity)} "
        "AND embedded_revision=input_revision AND embedding!=NONE;")
    compatible_ids = set(compatible)
    reused, pending = [], []
    for member in members:
        if member["id"] in compatible_ids:
            reused.append(member["id"])
        else:
            pending.append(member)
    client = EmbeddingClient(memory.config.machine)
    embedded = []
    for start in range(0, len(pending), MAX_REQUEST_INPUTS):
        batch = pending[start:start + MAX_REQUEST_INPUTS]
        inputs = []
        for member in batch:
            if member["kind"] == "image":
                snapshot = memory.config.memory_dir / member["asset"]
                if sha256(snapshot.read_bytes()).hexdigest() != member["input_revision"]:
                    raise ValueError(f"Image snapshot revision mismatch for {member['id']}")
                inputs.append({"image": str(snapshot)})
            else:
                inputs.append(member["title"] + "\n" + member["text"])
        try:
            result = client.embed(inputs, timeout=timeout)
        except HTTPError as error:
            error.add_note(error.read().decode("utf-8"))
            error.add_note("Unindexed members in this batch: " + ", ".join(member["id"] for member in batch))
            raise
        if result["embedding_identity"] != identity:
            raise ValueError("Embedding service identity changed during member encoding")
        if len(result["vectors"]) != len(batch):
            raise ValueError("Embedding service returned a different number of vectors")
        statements = ["BEGIN;"]
        for member, vector in zip(batch, result["vectors"], strict=True):
            record = _sql(_record(member["id"]))
            statements.extend([
                f"IF {record}.input_revision != {_sql(member['input_revision'])} OR {record}.stale != false "
                "{ THROW 'Member changed while embedding'; };",
                f"UPDATE {record} SET embedding={_sql(vector)}, embedding_identity={_sql(identity)}, "
                f"embedded_revision={_sql(member['input_revision'])} RETURN NONE;",
            ])
        statements.append("COMMIT;")
        memory._execute("\n".join(statements))
        embedded.extend(member["id"] for member in batch)
    return {"embedding_identity": identity, "embedded": embedded, "reused": reused,
            "pending": memory._execute("SELECT VALUE id FROM member WHERE retired!=true AND (stale=true "
                         f"OR embedding_identity!={_sql(identity)} OR embedded_revision!=input_revision OR embedding=NONE);")[0]}


def _scope_filter(memory, scope, allow_private):
    privacy = "" if allow_private else " AND private=false"
    return " AND ".join([f"stale=false AND retired!=true AND string::starts_with(path, {_sql(scope)}){privacy}",
                         *legacy_path_tests(memory, "path")])


def vector_coverage(memory, identity, *, scope="", allow_private=True) -> dict:
    scope_filter = _scope_filter(memory, scope, allow_private)
    total, compatible = memory._execute(
        f"SELECT id,path FROM member WHERE {scope_filter}; "
        f"SELECT VALUE id FROM member WHERE {scope_filter} AND embedding_identity={_sql(identity)} "
        "AND embedded_revision=input_revision AND embedding!=NONE;")
    compatible_ids = set(compatible)
    missing = [row for row in total if row["id"] not in compatible_ids]
    return {"identity": identity, "total": len(total), "compatible": len(compatible),
            "pending": len(missing), "pending_members": missing}


def vector_search(memory, text, *, scope="", limit=12, timeout=600, allow_private=True):
    limit = int(limit)
    scope_filter = _scope_filter(memory, scope, allow_private)
    dialogues = chunk_filter(memory, scope, allow_private)
    existence = f"SELECT VALUE id FROM member WHERE {scope_filter} LIMIT 1;"
    if dialogues:
        existence += " " + INDEX_VERSION_QUERY
    files, *index_versions = memory._execute(existence)
    if dialogues and index_versions[0] is None:
        dialogues = None
    if not files and not (dialogues and memory._execute(f"SELECT VALUE id FROM codex_chunk WHERE {dialogues} LIMIT 1;")[0]):
        return {"matches": [], "vector_coverage": {"identity": None, "total": 0, "compatible": 0,
                                                   "pending": 0, "pending_members": []}}
    result = EmbeddingClient(memory.config.machine).embed([text], timeout=timeout)
    identity = result["embedding_identity"]
    vector = _sql(result["vectors"][0])
    coverage = vector_coverage(memory, identity, scope=scope, allow_private=allow_private)
    dialogue_coverage = None
    distance = f"vector::distance::cosine(embedding, {vector}) AS distance"
    compatible = f"embedding_identity={_sql(identity)} AND embedding!=NONE"
    candidates = []
    if dialogues:
        totals, indexed, chunks = memory._execute(
            f"SELECT count() AS count FROM codex_chunk WHERE {dialogues} GROUP ALL; "
            f"SELECT count() AS count FROM codex_chunk WHERE {dialogues} AND {compatible} GROUP ALL; "
            f"SELECT {_LOCATION_FIELDS}, {distance}, kind AS segment_kind, node.kind AS kind, 'node' AS record_type, "
            "node.title AS title FROM codex_chunk "
            f"WHERE {dialogues} AND {compatible} ORDER BY distance ASC, dialogue_chunk ASC LIMIT {limit};")
        total = totals[0]["count"] if totals else 0
        active = indexed[0]["count"] if indexed else 0
        dialogue_coverage = {"identity": identity, "total": total, "compatible": active, "pending": total - active}
        candidates.extend(chunks)
    if not coverage["compatible"] and not (dialogue_coverage and dialogue_coverage["compatible"]):
        pending = coverage["pending"] + (dialogue_coverage["pending"] if dialogue_coverage else 0)
        raise ValueError("No compatible memory vectors in scope: not indexed, embedding_identity changed, "
                         "or embedded_revision differs from input_revision. Run memory embed to rebuild them. "
                         f"Query identity: {identity}; pending: {pending}")
    if coverage["compatible"]:
        candidates.extend(memory._execute(
            f"SELECT *, source_revision AS revision, {distance} OMIT {_CANDIDATE_OMIT} FROM member "
            f"WHERE {scope_filter} AND {compatible} AND embedded_revision=input_revision "
            f"ORDER BY distance ASC, id ASC LIMIT {limit};")[0])
    if dialogues:
        candidates.sort(key=lambda row: (row["distance"], _candidate_id(row)))
    result = {"matches": candidates[:limit], "vector_coverage": coverage}
    if dialogue_coverage is not None:
        result["dialogue_vector_coverage"] = dialogue_coverage
    return result


def _candidate_id(candidate):
    return candidate.get("dialogue_chunk", candidate["id"])


def hybrid_search(memory, text, *, scope="", limit=12, timeout=600, literal=False, allow_private=True):
    lexical = memory.search(text, scope=scope, limit=limit, literal=literal, allow_private=allow_private, access=False)
    result = vector_search(memory, text, scope=scope, limit=limit, timeout=timeout, allow_private=allow_private)
    combined = {}
    for name, candidates in [("lexical_rank", lexical), ("vector_rank", result["matches"])]:
        for rank, candidate in enumerate(candidates, 1):
            row = combined.setdefault(_candidate_id(candidate), {**candidate, "rrf_score": 0.0})
            row.update({key: value for key, value in candidate.items() if key in {"distance", "lexical_score"}})
            row[name] = rank
            row["rrf_score"] += 1 / (60 + rank)
    matches = sorted(combined.values(), key=lambda row: (literal and "lexical_rank" not in row,
                                                        -row["rrf_score"], _candidate_id(row)))[:limit]
    return {**result, "matches": matches}
