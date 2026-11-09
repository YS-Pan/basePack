"""Encode accepted members using the existing shared service; query native SQL."""

from hashlib import sha256
from urllib.error import HTTPError

from basepack.embedding.client import EmbeddingClient
from basepack.embedding.admin import status
from basepack.embedding.qwen3_vl import MAX_REQUEST_INPUTS
from .content import read_source
from .images import read_image
from .store import _record, _sql


def embed_members(memory, ids=None, *, timeout=600) -> dict:
    identity = status(memory.config.machine)["model"]["embedding_identity"]
    selected = "" if ids is None else f" AND id IN {_sql([_record(value) for value in ids])}"
    members = memory._execute(f"SELECT * OMIT embedding FROM member WHERE stale=false{selected};")[0]
    reused, pending = [], []
    for member in members:
        if member.get("embedding_identity") == identity and member.get("embedded_revision") == member["input_revision"]:
            reused.append(member["id"])
        else:
            pending.append(member)
    client = EmbeddingClient(memory.config.machine)
    embedded = []
    def verify_source(member):
        source = (read_image if member["kind"] == "image" else read_source)(memory.config.root, member["path"])
        if source.revision != member["source_revision"]:
            raise ValueError(f"Embedding source revision mismatch for {member['path']}")

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
            verify_source(member)
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
            verify_source(member)
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
            "pending": memory._execute("SELECT VALUE id FROM member WHERE stale=true "
                         f"OR embedding_identity!={_sql(identity)} OR embedded_revision!=input_revision OR embedding=NONE;")[0]}


def vector_search(memory, text, *, scope="", limit=12, timeout=600) -> list[dict]:
    scope_filter = f"stale=false AND string::starts_with(path, {_sql(scope)})"
    if not memory._execute(f"SELECT VALUE id FROM member WHERE {scope_filter} LIMIT 1;")[0]:
        return []
    result = EmbeddingClient(memory.config.machine).embed([text], timeout=timeout)
    identity = result["embedding_identity"]
    vector = _sql(result["vectors"][0])
    eligible, candidates = memory._execute(
        f"SELECT VALUE id FROM member WHERE {scope_filter} AND embedding_identity={_sql(identity)} "
        "AND embedded_revision=input_revision AND embedding!=NONE LIMIT 1; "
        "SELECT *, source_revision AS revision, "
        f"vector::distance::cosine(embedding, {vector}) AS distance OMIT embedding FROM member "
        f"WHERE stale=false AND embedding_identity={_sql(identity)} "
        "AND embedded_revision=input_revision AND embedding!=NONE "
        f"AND string::starts_with(path, {_sql(scope)}) "
        f"ORDER BY distance ASC LIMIT {int(limit)};")
    if not eligible:
        raise ValueError("No compatible memory vectors in scope: not indexed, embedding_identity changed, "
                         "or embedded_revision differs from input_revision. Run memory embed or search --mode text. "
                         f"Query identity: {identity}")
    return candidates


def hybrid_search(memory, text, *, scope="", limit=12, timeout=600, literal=False) -> list[dict]:
    lexical = memory.search(text, scope=scope, limit=limit, literal=literal)
    semantic = vector_search(memory, text, scope=scope, limit=limit, timeout=timeout)
    combined = {}
    for name, candidates in [("lexical_rank", lexical), ("vector_rank", semantic)]:
        for rank, candidate in enumerate(candidates, 1):
            row = combined.setdefault(candidate["id"], {**candidate, "rrf_score": 0.0})
            row.update({key: value for key, value in candidate.items() if key in {"distance", "lexical_score"}})
            row[name] = rank
            row["rrf_score"] += 1 / (60 + rank)
    return sorted(combined.values(), key=lambda row: (-row["rrf_score"], row["id"]))[:limit]
