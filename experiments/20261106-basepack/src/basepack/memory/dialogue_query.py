"""Query published dialogue locations and verify originals in the Codex host."""

from hashlib import sha256
import json

from .query import normalize_scope
from .store import _record, _sql


DIALOGUE_KIND = "codex_thread"
INDEX_VERSION_QUERY = "SELECT VALUE version FROM ONLY meta:codex_index;"


def _authorized_threads(config):
    from .codex_index_config import visible_threads

    return visible_threads(config, allow_private=True)


def authorized_ancestry(config, thread_id, ancestor_thread_ids):
    """Require current authorization of the persisted complete lineage."""
    threads = _authorized_threads(config)
    thread = threads.get(thread_id)
    return (thread is not None and isinstance(ancestor_thread_ids, list)
            and all(isinstance(parent, str) and parent in threads and (thread['private'] or not threads[parent]['private'])
                    for parent in ancestor_thread_ids))


def authorization_fingerprint(config):
    from .codex_index_config import load_manifest

    manifest = load_manifest(config)
    if manifest is not None:
        canonical = json.dumps(manifest, sort_keys=True, ensure_ascii=False)
        return sha256(canonical.encode('utf-8')).hexdigest()
    return None


def _scoped_threads(threads, scope, allow_private):
    return {key: row for key, row in threads.items()
            if row['path'].startswith(scope) and (allow_private or not row['private'])}


def _lineage_test(marker, parents, threads, scoped):
    public = [key for key, row in threads.items() if not row['private']]
    public_here = [key for key, row in scoped.items() if not row['private']]
    private_here = [key for key, row in scoped.items() if row['private']]
    clauses = []
    for current, ancestors in ((public_here, public), (private_here, list(threads))):
        if current:
            clauses.append(f"({marker} IN {_sql(current)} AND "
                           f"array::len({parents}[WHERE !($this IN {_sql(ancestors)})])=0)")
    return f"({parents}!=NONE AND ({' OR '.join(clauses)}))" if clauses else "false"


def graph_dialogue_test(memory, field, scope="", allow_private=True):
    """Apply current project authorization to retained dialogue nodes."""
    prefix = f"{field}." if field else ""
    marker = f"({prefix}codex_thread_id ?? {prefix}record.codex_thread_id)"
    parents = f"({prefix}ancestor_thread_ids ?? {prefix}record.ancestor_thread_ids)"
    threads = _authorized_threads(memory.config)
    scoped = _scoped_threads(threads, scope, allow_private)
    lineage = _lineage_test(marker, parents, threads, scoped)
    current = _lineage_test(marker, f"{prefix}target.ancestor_thread_ids", threads, scoped)
    return f"({marker}=NONE OR ({lineage} AND ({prefix}target=NONE OR {current})))"


def legacy_path_tests(memory, path):
    from .codex_index_config import legacy_capture_prefixes

    return [f"!string::starts_with(string::lowercase(({path} ?? '')), {_sql(prefix)})"
            for prefix in legacy_capture_prefixes(memory.config)]


def require_original_path(memory, path):
    from .codex_index_config import legacy_capture_path

    if path and legacy_capture_path(memory.config, path):
        raise ValueError("Original unavailable through the retained snapshot in dialogue index mode")


def chunk_filter(memory, scope, allow_private):
    threads = _authorized_threads(memory.config)
    scoped = _scoped_threads(threads, scope, allow_private)
    if not scoped:
        return None
    lineage = _lineage_test("thread_id", "node.ancestor_thread_ids", threads, scoped)
    tests = [lineage, "node.stale=false", "node.retired!=true",
             "node.codex_thread_id=thread_id", f"node.kind={_sql(DIALOGUE_KIND)}", "node.path=path",
             f"string::starts_with(path, {_sql(scope)})"]
    if not allow_private:
        tests.extend(("private=false", "node.private=false"))
    return " AND ".join(tests)


_LOCATION_FIELDS = ("id AS dialogue_chunk, node AS id, node.knowledge_revision AS knowledge_revision, "
                    "thread_id, bookmark, revision, chunk_sha256, path, ordinal, "
                    "(private OR node.private) AS private")


def dialogue_locations(memory, record_id, *, knowledge_revision=None, scope="", allow_private=False,
                       limit=30, offset=0):
    """List published exact message positions of a visible dialogue node."""
    from .graph_query_store import get_vertex, resolve_seed

    scope = normalize_scope(scope)
    filters = chunk_filter(memory, scope, allow_private)
    if filters is None:
        raise ValueError("Dialogue node unavailable within the requested scope and visibility")
    target = _record(record_id, "node")
    if target.table not in {"node", "knowledge_version"}:
        raise ValueError("Dialogue locations require a node or exact knowledge_version ID")
    exact = resolve_seed(memory, target, knowledge_revision)
    vertex = get_vertex(memory, exact, scope=scope, allow_private=allow_private) if exact else None
    if vertex is None or vertex.get("kind") != DIALOGUE_KIND:
        raise ValueError("Dialogue node unavailable within the requested scope and visibility")
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("Dialogue location limit must be between 1 and 100")
    if type(offset) is not int or offset < 0:
        raise ValueError("Dialogue location offset must be a nonnegative integer")
    node = _sql(_record(vertex["id"]))
    revision = _sql(vertex["knowledge_revision"])
    rows, = memory._execute(
        f"SELECT {_LOCATION_FIELDS} FROM codex_chunk WHERE {filters} "
        f"AND node={node} AND node.knowledge_revision={revision} "
        f"ORDER BY ordinal ASC, id ASC LIMIT {limit + 1} START {offset};")
    return {"record": vertex, "locations": rows[:limit], "next_offset": offset + limit if len(rows) > limit else None}


def read_chunk(memory, chunk_id, *, host, scope="", allow_private=False, context=1):
    """Return an instant host read of a visible, version-pinned chunk."""
    scope = normalize_scope(scope)
    target = _record(chunk_id, "codex_chunk")
    if target.table != "codex_chunk":
        raise ValueError("Dialogue read requires a codex_chunk ID")
    filters = chunk_filter(memory, scope, allow_private)
    row = None
    if filters and memory._execute(INDEX_VERSION_QUERY)[0] is not None:
        row = memory._execute(f"SELECT {_LOCATION_FIELDS} FROM ONLY {_sql(target)} WHERE {filters};")[0]
    if row is None:
        raise ValueError("Dialogue chunk unavailable within the requested scope and visibility")
    original = host.read(row["bookmark"], context=context)
    if original["bookmark"] != row["bookmark"] or sha256(original["text"].encode("utf-8")).hexdigest() != row["chunk_sha256"]:
        raise ValueError("Dialogue read did not match the indexed location and content revision")
    return {"location": row, "original": original}
