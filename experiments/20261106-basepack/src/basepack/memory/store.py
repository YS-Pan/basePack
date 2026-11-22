"""Project memory actions over native SurrealDB records and transactions."""

from base64 import b64encode
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

from basepack.project.config import ProjectConfig
from basepack.runtime.activity import memory_operation
from basepack.runtime.http import managed_opener
from basepack.runtime.recovery import managed, raise_if_managed_refusal
from .content import (SourceContent, _check_collection_revision, _project_path, detect_changes,
                      numbered_text, read_source, reading_units, original_text, line_slices)
from .images import IMAGE_SUFFIXES, ImageSource, read_image, retain_image
from .privacy import derive_private, privacy_rules, rules_revision, source_private


_CANDIDATE_OMIT = "embedding,basis,raw_revision"
_MESSAGE_LIMIT = 2112 * 1024


@dataclass(frozen=True)
class _Record:
    table: str
    key: str | int


def _record(value: str | _Record, table: str = "member") -> _Record:
    """Keep bare string keys literal; decode native table-qualified IDs."""
    if isinstance(value, _Record):
        return value
    if ":" not in value:
        return _Record(table, value)
    table, value = value.split(":", 1)
    if value.startswith(("`", "⟨")):
        closing = "`" if value[0] == "`" else "⟩"
        if not value.endswith(closing):
            raise ValueError(f"Unterminated record ID: {table}:{value}")
        escapes = {"0": "\0", "r": "\r", "t": "\t", "n": "\n", "f": "\f", "\\": "\\", "`": "`", "⟩": "⟩"}

        def unescape(match):
            escaped = match[1]
            return chr(int(escaped[2:-1], 16)) if escaped.startswith("u{") else escapes[escaped]

        return _Record(table, re.sub(r"\\(u\{[0-9a-fA-F]+\}|.)", unescape, value[1:-1]))
    if re.fullmatch(r"-?[0-9]+", value) and -(2 ** 63) <= int(value) < 2 ** 63:
        return _Record(table, int(value))
    if value.startswith(("[", "{", "u'", 'u"')):
        raise ValueError("Memory record IDs require a string or integer key")
    return _Record(table, value)


def _sql(value) -> str:
    if isinstance(value, _Record):
        return f"type::record({_sql(value.table)}, {_sql(value.key)})"
    if isinstance(value, dict):
        return "{" + ",".join(f"{json.dumps(k)}:{_sql(v)}" for k, v in value.items()) + "}"
    if isinstance(value, list):
        return "[" + ",".join(map(_sql, value)) + "]"
    return json.dumps(value, ensure_ascii=False)


def _digest(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _input_revision(title: str, text: str) -> str:
    return _digest(title + "\n" + text)


def _query_wire_size(sql: str) -> int:
    """Measure the actual escaped query envelope, reserving the RPC identity."""
    return len(json.dumps({"id": 999999, "method": "query", "txn": "0" * 36,
                           "params": [sql]}, ensure_ascii=False).encode("utf-8"))


def _publication_groups(statements: list[str], limit: int) -> list[str]:
    envelope = _query_wire_size("")
    separator = _query_wire_size("\n") - envelope
    groups, group = [], []
    size = envelope
    for statement in statements:
        wire_size = _query_wire_size(statement)
        if wire_size > limit:
            raise ValueError(f"One SQL statement exceeds the {limit}-byte WebSocket message limit "
                             f"({wire_size} encoded bytes)")
        payload = wire_size - envelope
        if group and size + separator + payload > limit:
            groups.append("\n".join(group))
            group, size = [], envelope
        size += payload + (separator if group else 0)
        group.append(statement)
    if group:
        groups.append("\n".join(group))
    return groups


def _snapshot_sql(version: _Record, snapshot: dict) -> list[str]:
    """Keep one complete stored original while transporting bounded SQL pieces."""
    statement = f"UPSERT {_sql(version)} CONTENT {_sql(snapshot)} RETURN NONE;"
    if _query_wire_size(statement) <= _MESSAGE_LIMIT or snapshot["kind"] != "text":
        return [statement]
    text = snapshot["text"]
    statements = [f"UPSERT {_sql(version)} CONTENT {_sql({**snapshot, 'text': ''})} RETURN NONE;"]
    offset = 0
    while offset < len(text):
        def append(end):
            return f"UPDATE {_sql(version)} SET text += {_sql(text[offset:end])} RETURN NONE;"
        low, high = offset + 1, len(text)
        while low <= high:
            end = (low + high) // 2
            if _query_wire_size(append(end)) <= _MESSAGE_LIMIT:
                low = end + 1
            else:
                high = end - 1
        if high < offset + 1:
            raise ValueError(f"Source snapshot statement exceeds the {_MESSAGE_LIMIT}-byte WebSocket message limit")
        statements.append(append(high))
        offset = high
    return statements


def _original(source: SourceContent, start: int, end: int, locator=None) -> str:
    return original_text(source, start, end, locator)


def _read_original(config, snapshot, path, version, start_line, end_line, locator, *, member_id=None):
    revision = snapshot["revision"]
    original = {"path": path, "revision": revision, "private": snapshot.get("private", source_private(path)),
                "source_version": version, "locator": locator}
    if snapshot["kind"] == "image":
        asset = config.memory_dir / snapshot["asset"]
        if sha256(asset.read_bytes()).hexdigest() != revision:
            raise ValueError(f"Image snapshot revision mismatch for {member_id or version}")
        return {**original, "image_path": str(asset)}
    text = snapshot["text"]
    if sha256(text.encode("utf-8")).hexdigest() != revision:
        raise ValueError(f"Text snapshot revision mismatch for {member_id or version}")
    content = SourceContent(path, revision, len(text.encode("utf-8")), 0, text)
    original.update(start_line=start_line, end_line=end_line, text=_original(content, start_line, end_line, locator))
    if member_id is not None:
        original["member_id"] = member_id
    if (config.root / path).resolve().parent == (config.memory_dir / "codex").resolve():
        from .codex_locator import message_locations
        original["chat_locations"] = message_locations(text, start_line, end_line)
    return original


def _matches_original(source: SourceContent, member: dict) -> bool:
    try:
        return _digest(_original(source, member["start_line"], member["end_line"], member.get("locator"))) == member["raw_revision"]
    except ValueError:
        # A valid previous location can disappear after a source change.
        return False


class SqlResponseError(RuntimeError):
    """A SQL request returned a definite server-side statement error."""


class _RpcError(RuntimeError):
    pass


class PublicationOutcomeUnknown(RuntimeError):
    """The commit response was lost and the transaction could not be confirmed."""


class Memory:
    """Bind every action to one explicit project and its native database."""

    def __init__(self, config: ProjectConfig):
        self.config = config
        self.connection = config.raw["memory"]
        self._database_contact_attempted = False
        self._password = config.memory_password_file.read_bytes().decode("utf-8-sig")
        credential = f"{self.connection['username']}:{self._password}"
        self._authorization = "Basic " + b64encode(credential.encode("utf-8")).decode("ascii")

    def _project_guard(self):
        return (f"IF meta:project.project_id != {_sql(self.connection['project_id'])} "
                "{ THROW 'Memory database belongs to another project or is not initialized'; };\n"
                "IF meta:project.member_identity_version = NONE OR meta:project.member_identity_version != 2 "
                "{ THROW 'Memory member identity migration required'; };\n"
                "IF meta:project.memory_schema_version = NONE OR meta:project.memory_schema_version != 4 "
                "{ THROW 'Memory graph schema 4 offline migration required'; };")

    def verify_project(self) -> None:
        """Confirm the connected project and current schema before a protected operation."""
        # SurrealDB executes later statements after a failed IF, so finish the gate separately.
        self._execute(self._project_guard(), check_project=False)

    def _execute(self, sql: str, *, check_project: bool = True) -> list:
        with memory_operation(self.config) as lease:
            if check_project:
                self.verify_project()
            endpoint = self.connection["endpoint"] if lease is None else lease.endpoint
            return self._execute_admitted(sql, endpoint, recover_start=lease is None)

    def _execute_admitted(self, sql: str, endpoint: str, *, recover_start: bool) -> list:
        connection = self.connection
        body = sql.encode("utf-8")
        request = Request(endpoint.rstrip("/") + "/sql", body, {
            "Authorization": self._authorization,
            "surreal-ns": connection["namespace"], "surreal-db": connection["database"],
            "Accept": "application/json", "Content-Type": "text/plain; charset=utf-8",
        })
        first_request = not self._database_contact_attempted
        self._database_contact_attempted = True
        open_sql = managed_opener().open if managed(self.config, "memory") else urlopen
        try:
            response = open_sql(request, timeout=30)
        except HTTPError as error:
            error.add_note(error.read().decode("utf-8"))
            if error.code == 413:
                error.add_note(f"SQL request body: {len(body)} bytes; server capacity is unknown.")
            raise
        except OSError as error:
            if first_request and recover_start:
                raise_if_managed_refusal(error, "memory", self.config)
            raise
        with response as stream:
            statements = json.load(stream)
        errors = [statement["result"] for statement in statements if statement["status"] != "OK"]
        if errors:
            raise SqlResponseError("\n".join(str(error) for error in errors))
        return [statement["result"] for statement in statements]

    def _publish(self, statements: list[str], *, control: str | None = None) -> None:
        """Send complete SQL statements in bounded messages in one native transaction."""
        with memory_operation(self.config) as lease:
            self._publish_admitted(statements, control, lease)

    def _publish_admitted(self, statements, control, lease) -> None:
        from websocket import create_connection

        limit = _MESSAGE_LIMIT
        marker = _Record("meta", "publication_" + uuid4().hex)
        project_check = self._project_guard()
        statements = [project_check, *statements[1:-1],
                      f"CREATE {_sql(marker)} SET committed=true RETURN NONE;"]
        groups = _publication_groups(statements, limit)

        publication = None
        if control:
            from .owner import begin_publication, finish_publication
            publication = begin_publication(self.config.memory_dir, control, marker.key.removeprefix("publication_"))
        finished = False
        held = False
        ws = None
        transaction = None
        committing = False
        try:
            url_base = self.connection["endpoint"] if lease is None else lease.endpoint
            endpoint = urlsplit(url_base.rstrip("/"))
            url = urlunsplit(("wss" if endpoint.scheme == "https" else "ws", endpoint.netloc,
                              endpoint.path + "/rpc", "", ""))
            self._database_contact_attempted = True
            options = {} if lease is None else {"origin": lease.origin, "http_no_proxy": [endpoint.hostname],
                                                "redirect_limit": 0}
            ws = create_connection(url, subprotocols=["json"], timeout=30, **options)
            sequence = 0
            def rpc(method, params=None, txn=None):
                nonlocal sequence
                sequence += 1
                message = {"id": sequence, "method": method}
                if params is not None:
                    message["params"] = params
                if txn is not None:
                    message["txn"] = txn
                ws.send(json.dumps(message, ensure_ascii=False))
                response = json.loads(ws.recv())
                if "error" in response:
                    raise _RpcError(str(response["error"]))
                return response["result"]
            rpc("signin", [{"user": self.connection["username"], "pass": self._password}])
            rpc("use", [self.connection["namespace"], self.connection["database"]])
            transaction = rpc("begin")
            for group in groups:
                results = rpc("query", [group], transaction)
                errors = [result["result"] for result in results if result["status"] != "OK"]
                if errors:
                    raise RuntimeError("\n".join(map(str, errors)))
            if lease is not None and publication is None:
                # A disconnected client can leave an unconfirmed commit even without a maintenance owner.
                lease.hold(marker.key)
                held = True
            committing = True
            try:
                rpc("commit", [transaction])
            except Exception as error:
                if isinstance(error, _RpcError) and "TransactionConflict" in str(error):
                    finished = True
                    raise
                # A lost or otherwise ambiguous response does not establish
                # failure. Only the transactional marker confirms publication.
                try:
                    committed = self._execute(f"SELECT * FROM ONLY {_sql(marker)};")[0]
                except Exception as verification_error:
                    unknown = PublicationOutcomeUnknown(
                        f"Publication outcome unknown; inspect {_sql(marker)} before any retry")
                    unknown.add_note(f"Marker verification failed: {verification_error!r}")
                    unknown.verification_error = verification_error
                    raise unknown from error
                if not committed:
                    raise PublicationOutcomeUnknown(
                        f"Publication outcome unknown; inspect {_sql(marker)} before any retry") from error
            finished = True
        except Exception:
            if not committing:
                if transaction is None:
                    finished = True
                elif ws is not None:
                    try:
                        rpc("cancel", [transaction])
                        finished = True
                    except Exception:
                        pass
            raise
        finally:
            if ws is not None:
                ws.close()
            if publication is not None and finished:
                finish_publication(self.config.memory_dir, control, publication)
            elif held and finished:
                publication_error = sys.exception()
                try:
                    lease.clear(marker.key)
                except (ConnectionError, TimeoutError) as error:
                    note = f"Publication {marker.key} has a confirmed outcome; idle guard release failed: {error}"
                    if publication_error is None:
                        error.add_note(note)
                        raise
                    publication_error.add_note(note)

    def install_schema(self) -> dict:
        # Install the schema and bind its project in one native transaction.
        with memory_operation(self.config):
            return self._install_schema()

    def _install_schema(self) -> dict:
        namespace = "`" + self.connection["namespace"].replace("`", "\\`") + "`"
        database = "`" + self.connection["database"].replace("`", "\\`") + "`"
        self._execute(f"DEFINE NAMESPACE IF NOT EXISTS {namespace}; USE NS {namespace}; "
                      f"DEFINE DATABASE IF NOT EXISTS {database}; DEFINE TABLE IF NOT EXISTS meta SCHEMALESS;",
                      check_project=False)
        schema = Path(__file__).with_name("schema.surql").read_text(encoding="utf-8")
        project_id = _sql(self.connection["project_id"])
        gates = (f"IF meta:project.project_id != NONE AND meta:project.project_id != {project_id} "
                 "{ THROW 'Memory database belongs to another project'; }; "
                 "IF meta:project.project_id != NONE AND (meta:project.member_identity_version = NONE OR "
                 "meta:project.member_identity_version != 2) "
                 "{ THROW 'Memory member identity migration required'; }; "
                 "IF meta:project.project_id != NONE AND (meta:project.memory_schema_version = NONE OR "
                 "meta:project.memory_schema_version != 4) "
                 "{ THROW 'Memory graph schema 4 offline migration required'; }; ")
        if self._execute("SELECT * FROM ONLY meta:project;", check_project=False)[0] is None:
            tables = self._execute("INFO FOR DB;", check_project=False)[0]["tables"]
            if set(tables) - {"meta"}:
                raise ValueError("Memory graph schema 4 requires an empty database or an offline migration")
        self._execute(gates, check_project=False)
        self._execute("BEGIN;\n" + gates + schema + "\n"
                      "IF meta:delivery.id = NONE { CREATE meta:delivery SET j=0; };\n"
                      f"UPSERT meta:project SET project_id={project_id}, member_identity_version=2, "
                      "memory_schema_version=4; COMMIT;", check_project=False)
        return {"namespace": self.connection["namespace"], "database": self.connection["database"]}

    def _rows(self, table: str) -> list[dict]:
        if table == "semantic":
            from .history import semantic_rows
            return semantic_rows(self)
        return self._execute(f"SELECT * OMIT embedding FROM {table};")[0]

    def knowledge(self, record_id: str, *, knowledge_revision: str | None = None) -> dict:
        from .history import knowledge
        row = knowledge(self, record_id, knowledge_revision=knowledge_revision)
        return self.access_hints([row])[0] if _record(row["id"]).table in {"member", "node", "semantic"} else row

    def history(self, record_id: str) -> dict:
        from .history import history
        result = history(self, record_id)
        result["versions"] = self.access_hints(result["versions"])
        return result

    def access_hints(self, items: list[dict]) -> list[dict]:
        from .access import access_hints
        return access_hints(self, items)

    def record_delivery(self, delivery_id: str, items: list[dict], *, context: dict | None = None) -> dict:
        from .access import record_delivery
        return record_delivery(self, delivery_id, items, context=context)

    def behavior_candidates(self, anchors, limit=20, *, scope=""):
        from .behavior_projection import behavior_candidates
        return behavior_candidates(self, anchors, limit=limit, scope=scope)

    def train_behavior(self, rank=8, epsilon=0.001, beta=0.2, strength=8.0):
        from .behavior_projection import train_behavior
        return train_behavior(self, rank=rank, epsilon=epsilon, beta=beta, strength=strength)

    def compile_behavior(self):
        from .behavior_projection import compile_behavior
        return compile_behavior(self)

    def _load_source(self, path: str, kind: str | None = None, *,
                     expected_revision: str | None = None) -> SourceContent | ImageSource:
        try:
            if kind == "image" or Path(path).suffix.lower() in IMAGE_SUFFIXES:
                source = read_image(self.config.root, path)
                _check_collection_revision(path, expected_revision, source.revision)
                return source
            return read_source(self.config.root, path, expected_revision=expected_revision)
        except FileNotFoundError:
            _check_collection_revision(path, expected_revision, None)
            raise

    def prepare(self, paths: list[str], *, historical_versions: list[dict] | None = None,
                expected_revisions: dict[str, str | None] | None = None) -> dict:
        """Supply explicit new/old originals and existing knowledge for one reading."""
        for path in paths:
            if _project_path(self.config.root.resolve(), path).is_dir():
                raise ValueError(f"prepare --paths accepts files, not directories: {path}. "
                                 "Enumerate and select files first (PowerShell: Get-ChildItem -File); "
                                 "pass their project-relative paths to --paths.")
        rules = privacy_rules(self.config)
        rules_hash = rules_revision(rules)
        if expected_revisions is not None and (
            not isinstance(expected_revisions, dict) or set(expected_revisions) != set(paths)
        ):
            raise ValueError("Expected revisions must cover exactly the paths being prepared")
        known = {source["path"]: source for source in self._rows("source")}
        members = self._rows("member")
        prepared = []
        ids = []
        snapshot_ids = set()
        for path in paths:
            expected = expected_revisions[path] if expected_revisions is not None else None
            try:
                source = self._load_source(path) if expected is None else self._load_source(path, expected_revision=expected)
            except FileNotFoundError:
                if Path(path).as_posix() not in known:
                    raise
                item = {"path": Path(path).as_posix(), "deleted": True}
                item["private"] = known[item["path"]].get("private", source_private(item["path"]))
            else:
                if expected_revisions is not None and expected is None:
                    raise ValueError(f"Expected missing original now exists: {path}")
                item = {"path": source.path, "revision": source.revision, "size": source.size,
                        "private": source_private(source.path, rules['private_scope']),
                        "mtime_ns": source.mtime_ns}
                if isinstance(source, ImageSource):
                    item.update({"kind": "image", "image_path": str(self.config.root / source.path)})
                else:
                    preview = {"source": _Record("source", "0" * 32), "revision": source.revision,
                               "path": source.path, "kind": "text", "text": source.text,
                               "private": item['private'], "privacy_rules_revision": rules_hash}
                    version = _Record("source_version", "0" * 64)
                    sql = f"UPSERT {_sql(version)} CONTENT {_sql(preview)} RETURN NONE;"
                    try:
                        pieces = _snapshot_sql(version, preview)
                    except ValueError as error:
                        error.add_note(f"Source {source.path}: {source.size} original bytes; "
                                       f"{_query_wire_size(sql)} encoded snapshot bytes")
                        raise
                    item.update({"kind": "text", "numbered_text": numbered_text(source),
                                 "snapshot_transport": {"original_bytes": source.size,
                                                        "encoded_snapshot_bytes": _query_wire_size(sql),
                                                        "statement_count": len(pieces),
                                                        "message_limit_bytes": _MESSAGE_LIMIT},
                                 "line_slices": line_slices(source),
                                 "reading_units": [{"kind": unit.kind, "start_line": unit.start_line, "end_line": unit.end_line}
                                                   for unit in reading_units(source)]})
            item["members"] = [row for row in members if row["path"] == item["path"]]
            previous = known.get(item["path"])
            if previous:
                snapshot = self._execute(f"SELECT * FROM ONLY {_sql(_record(previous['version']))};")[0]
                snapshot_ids.add(_record(snapshot["id"]))
                item["id"] = previous["id"]
                if snapshot.get("kind") == "image":
                    item["previous"] = {"revision": previous["revision"], "kind": "image",
                                        "image_path": str(self.config.memory_dir / snapshot["asset"])}
                else:
                    old = SourceContent(item["path"], previous["revision"], previous["size"],
                                        previous["mtime_ns"], snapshot["text"])
                    item["previous"] = {"revision": old.revision, "numbered_text": numbered_text(old)}
                item["previous"].update({key: snapshot[key] for key in ("dispositions", "deferred_refinement", "unavailable_gaps")
                                         if key in snapshot})
                item["previous"]["private"] = snapshot.get("private", source_private(snapshot.get("path", previous["path"])))
                item["previous"]["source_version"] = snapshot["id"]
            prepared.append(item)
            ids.extend(member["id"] for member in item["members"])
        selected = set(ids)
        from .history import knowledge, semantic_rows
        edges = semantic_rows(self, members=ids) if ids else []
        nodes = self._rows("node")
        related = set(selected)
        related.update(value for edge in edges for value in (edge["in"], edge["out"])
                       if _record(value).table == "member")
        node_ids = {value for edge in edges for value in (edge["in"], edge["out"])
                    if _record(value).table == "node"}
        related_nodes = [node for node in nodes if node["id"] in node_ids or any(
            basis["member"] in selected for basis in node.get("basis", []))]
        selected_members = [member for member in members if member["id"] in selected]
        related.update(basis["member"] for row in selected_members + related_nodes + edges
                       for basis in row.get("basis", []))
        # Keep current revisions for optimistic checks, but traverse accepted
        # provenance by exact version. Rebinding a historical pin to today's
        # member would change the evidence the author actually selected.
        current = {_record(row["id"]): row for row in [*members, *nodes, *edges]}
        explicit = [knowledge(self, item["id"], knowledge_revision=item["knowledge_revision"])
                    for item in historical_versions or []]
        if any(row.get("legacy_history_only") for row in explicit):
            raise ValueError("A history-only relationship cannot be prepared as a graph endpoint")
        explicit_keys = {(_record(row["id"]), row["knowledge_revision"]) for row in explicit}
        historical = {}
        versions = {(identity, row["knowledge_revision"]): row for identity, row in current.items()}
        versions.update({(_record(row["id"]), row["knowledge_revision"]): row for row in explicit})
        eligible = [*selected_members, *related_nodes, *edges,
                    *(current[_record(identifier)] for identifier in related if _record(identifier) in current)]
        pending = [row for row in eligible if not row.get("stale") and not row.get("retired")]
        pending.extend(explicit)
        seen = set()
        while pending:
            row = pending.pop()
            identity = _record(row["id"])
            revision = row["knowledge_revision"]
            key = (identity, revision)
            if key in seen:
                continue
            seen.add(key)
            if identity not in current:
                current[identity] = knowledge(self, identity)
            if identity.table == "member":
                related.add(current[identity]["id"])
            if current[identity]["knowledge_revision"] != revision or key in explicit_keys:
                historical[key] = row
            refs = [(entry["member"], entry["knowledge_revision"]) for entry in row.get("basis", [])]
            refs.extend((entry["id"], entry["knowledge_revision"])
                        for entry in row.get("direct_basis", []) if "id" in entry)
            if row.get("parent_version"):
                parent = row["parent_version"]
                refs.append((parent["id"], parent["knowledge_revision"]))
            refs.extend((endpoint["id"], endpoint["knowledge_revision"])
                        for endpoint in row.get("endpoint_versions", {}).values())
            for identifier, pinned_revision in refs:
                dependency = _record(identifier)
                if dependency not in current:
                    current[dependency] = knowledge(self, dependency)
                latest = current[dependency]
                pinned_key = (dependency, pinned_revision)
                if pinned_key not in versions:
                    versions[pinned_key] = (latest if latest["knowledge_revision"] == pinned_revision else
                                            knowledge(self, identifier, knowledge_revision=pinned_revision))
                related.add(latest["id"])
                pending.append(versions[pinned_key])
        neighborhood_members = [row for identity, row in current.items()
                                if identity.table == "member" and row["id"] in related - selected]
        expected = {row["id"]: row["knowledge_revision"] for row in
                    [member for item in prepared for member in item["members"]] + neighborhood_members + nodes + edges}
        # Explicit graph history can name a current endpoint outside the initial
        # neighborhood; its current head is still guarded during publication.
        visited_ids = {identity for identity, _ in seen}
        expected.update({row["id"]: row["knowledge_revision"] for identity, row in current.items()
                         if identity in visited_ids})
        neighborhood_edges = {_record(row["id"]): row for row in edges}
        neighborhood_edges.update({identity: row for identity, row in current.items()
                                   if identity.table == "semantic" and identity in visited_ids})
        historical = list(historical.values())
        from .graph_write import knowledge_ids
        version_rows = [*selected_members, *neighborhood_members, *nodes, *historical]
        revisions = {(_record(row["id"]), row["knowledge_revision"]) for row in version_rows
                     if "exact_id" not in row}
        exact_ids = knowledge_ids(self, revisions)
        for row in version_rows:
            if "exact_id" not in row:
                exact = exact_ids[(_record(row["id"]), row["knowledge_revision"])]
                row["exact_id"] = f"{exact.table}:{exact.key}"
            if row.get("source_version"):
                snapshot_ids.add(_record(row["source_version"]))
        for row in neighborhood_edges.values():
            snapshot_ids.update(_record(entry["source_version"]) for entry in row.get("direct_basis", [])
                                if "source_version" in entry)
        snapshots = self._execute(
            f"SELECT id,private,kind,path,revision FROM source_version WHERE id IN "
            f"{_sql(sorted(snapshot_ids, key=_sql))};")[0] if snapshot_ids else []
        return {"sources": prepared, "historical_versions": historical,
                "snapshots": snapshots,
                "privacy_rules": rules, "privacy_rules_revision": rules_hash,
                "neighborhood": {"members": neighborhood_members, "edges": list(neighborhood_edges.values()),
                "nodes": nodes}, "expected": expected,
                "instruction": "Read originals together. Choose semantic boundaries, summaries, and evidenced relations in one batch; reading_units are structural hints only."}

    def _affected(self, current: dict[str, SourceContent | ImageSource | None], members: list[dict]) -> set[str]:
        members = [member for member in members if not member["retired"]]
        affected = set()
        # An insertion just beyond an old summary range can expand its scope
        # while leaving every old covered line byte-for-byte unchanged.
        changed_sections = [member for member in members if member["kind"] == "section"
                            and member["path"] in current and current[member["path"]] is not None
                            and member["source_revision"] != current[member["path"]].revision]
        snapshots = {}
        if changed_sections:
            versions = list({_record(member["source_version"]) for member in changed_sections})
            snapshots = {row["id"]: row["text"] for row in self._execute(
                f"SELECT id,text FROM source_version WHERE id IN {_sql(versions)};")[0]}
        insertions = {}
        for member in members:
            if member["path"] not in current:
                continue
            source = current[member["path"]]
            if member["kind"] == "image":
                if source is None or source.revision != member["raw_revision"]:
                    affected.add(member["id"])
                continue
            if source is not None and member["source_revision"] != source.revision:
                if member["kind"] == "file":
                    affected.add(member["id"])
                elif member["kind"] == "section":
                    key = (member["source_version"], source.revision)
                    if key not in insertions:
                        before = snapshots[member["source_version"]].splitlines(keepends=True)
                        after = source.text.splitlines(keepends=True)
                        insertions[key] = [start for operation, start, end, _, _ in
                                           SequenceMatcher(None, before, after, autojunk=False).get_opcodes()
                                           if operation == "insert"]
                    if any(member["start_line"] - 1 <= position <= member["end_line"]
                           for position in insertions[key]):
                        affected.add(member["id"])
            if source is None or member["end_line"] > len(source.text.splitlines()) or (
                    not _matches_original(source, member)):
                affected.add(member["id"])
        return self._expand_affected(affected, members)

    @staticmethod
    def _expand_affected(affected: set[str], members: list[dict]) -> set[str]:
        # Containment and accepted summary evidence are both real dependencies.
        members = [member for member in members if not member["retired"]]
        current_ids = {member["id"] for member in members}
        while True:
            expanded = affected | {member["id"] for member in members if any(
                basis["member"] in affected for basis in member.get("basis", []))}
            expanded |= {member["parent"] for member in members
                         if member["id"] in affected and member.get("parent") in current_ids}
            if expanded == affected:
                return affected
            affected = expanded

    def _invalidate_sql(self, affected: set[str], operation: str, context: dict) -> list[str]:
        if not affected:
            return []
        refs = _sql([_record(value) for value in sorted(affected)])
        from .graph_write import invalidate, knowledge_ids
        members, nodes = self._execute(
            f"SELECT id,knowledge_revision FROM member WHERE id IN {refs}; "
            f"SELECT id,knowledge_revision FROM node WHERE basis.*.member CONTAINSANY {refs};")
        versions = knowledge_ids(self, ((_record(row["id"]), row["knowledge_revision"]) for row in members + nodes))
        audit = _sql(_Record("change", uuid4().hex))
        return [f"CREATE {audit} SET operation={_sql(operation)}, at=time::now(), context={_sql(context)}, "
                f"previous={{members:(SELECT * OMIT embedding FROM member WHERE id IN {refs}), "
                f"nodes:(SELECT * FROM node WHERE basis.*.member CONTAINSANY {refs})}};",
                f"UPDATE member SET stale=true WHERE id IN {refs};",
                f"UPDATE node SET stale=true WHERE basis.*.member CONTAINSANY {refs};",
                *invalidate(self, versions.values(), "needs_review")]

    def apply(self, batch: dict, *, control: str | None = None, timeout: float = 600) -> dict:
        self.config.memory_search_mode
        with memory_operation(self.config):
            return self._apply_with_control(batch, control=control, timeout=timeout)

    def _apply_with_control(self, batch: dict, *, control: str | None, timeout: float) -> dict:
        if control:
            return self._apply(batch, control=control, timeout=timeout)
        from .owner import acquire, release, stop_owned
        control = str(self.config.memory_dir / "maintenance" / f"manual-{uuid4().hex}.control")
        result = acquire(self.config.memory_dir, self.connection["project_id"], "Python apply", control)
        if not result["acquired"]:
            raise RuntimeError(f"Memory maintenance already owned: {result['owner']}")
        try:
            return self._apply(batch, control=control, timeout=timeout)
        finally:
            original = sys.exception()
            try:
                stop_owned(self.config.memory_dir, control)
                # An uncertain publication remains in flight and release refuses it.
                release(self.config.memory_dir, control)
            except Exception as cleanup_error:
                if original is None:
                    raise
                original.add_note(f"Maintenance owner retained: {cleanup_error}")

    def _apply(self, batch: dict, *, control: str | None = None, timeout: float = 600) -> dict:
        """Check exact source revisions, then accept one agent batch atomically.

        Unmentioned records and edges survive. Accepted chunk text comes from the
        original, never from generated prose. Corrections retain actual old data.
        """
        self.config.memory_search_mode
        from .draft import validate_batch
        from .graph_write import Publication, invalidate, knowledge_ids, set_state
        from .history import knowledge as read_knowledge
        validate_batch(batch)
        if control:
            from .maintenance import check
            check(control)
        batch_hash = _digest(json.dumps(batch, ensure_ascii=False, sort_keys=True, separators=(',', ':')))
        receipt = _Record('meta', 'batch_' + batch['batch_id'])
        prior = self._execute(f"SELECT * FROM ONLY {_sql(receipt)};")[0]
        if prior:
            if prior['batch_hash'] != batch_hash:
                raise ValueError('Frozen batch ID already used with different content')
            return prior['result']
        rules = privacy_rules(self.config)
        rules_hash = rules_revision(rules)
        legacy_rules = 'privacy_rules' not in batch and 'privacy_rules_revision' not in batch
        if legacy_rules and rules['private_scope']:
            raise ValueError('Legacy frozen batch uses root-private classification; private_scope rules changed; '
                             'freeze again with the project configuration')
        if not legacy_rules and (batch.get('privacy_rules') != rules or batch.get('privacy_rules_revision') != rules_hash):
            raise ValueError('Private classification rules changed or were not frozen for this project; '
                             'freeze again with the project configuration')
        for source in batch['sources']:
            if (not legacy_rules and not source.get('deleted')
                    and source.get('private') != source_private(source['path'], rules['private_scope'])):
                raise ValueError(f"Frozen private classification mismatch for {source['path']}; freeze again")
        for field in ("dispositions", "deferred_refinement", "unavailable_gaps"):
            if field in batch:
                raise ValueError(f"{field} must be inside the relevant sources[] entry, not at batch root")
        for index, item in enumerate(batch.get("members", [])):
            if item["kind"] in {"file", "section", "chunk"}:
                missing = [field for field in ("start_line", "end_line") if field not in item]
                if missing:
                    raise ValueError(f"members[{index}] ({item['id']}) missing required fields: {', '.join(missing)}")
        known = self._rows("source")
        by_path = {source["path"]: source for source in known}
        by_id = {source["id"]: source for source in known}
        resolved_sources = []
        for source in batch['sources']:
            previous = by_id[source['id']] if 'id' in source else by_path.get(source['path'])
            if previous:
                resolved_sources.append(_record(previous['id']))
        if len(resolved_sources) != len(set(resolved_sources)):
            raise ValueError('Duplicate source identity in batch')
        before_members = self._rows("member")
        current = {}
        sources = {}
        versions = {}
        snapshots = {}
        assets = {}
        statements = ["BEGIN;"]
        targets = {_record(item["id"], table) for table, key in
                   [("member", "members"), ("node", "nodes"), ("semantic", "edges")]
                   for item in batch.get(key, [])}
        targets.update(_record(value, table) for table, key in
                       [("member", "delete_members"), ("node", "delete_nodes"), ("semantic", "delete_edges")]
                       for value in batch.get(key, []))
        targets.update(_record(item["target"]) for item in batch.get("corrections", []))
        dependencies = {_record(value) for key in ("members", "nodes", "edges")
                        for item in batch.get(key, []) for value in item.get("evidence", [])}
        dependencies.update(target for item in batch.get("edges", [])
                            for target in (_record(item["in"]), _record(item["out"]),
                                           *(_record(ref["id"]) for ref in item.get("basis", []) if "id" in ref))
                            if target.table in {"member", "node", "semantic"})
        parents = {_record(item["parent"]) for item in batch.get("members", []) if item.get("parent")}
        if any(parent.table != "member" for parent in parents):
            raise ValueError("Parent must reference a member")
        dependencies.update(parents)
        dependencies.update(_record(value) for value in batch.get("dependency_closure", []))
        expected_heads = {_record(key): value for key, value in batch.get("expected", {}).items()}
        expected_status = {_record(key): active for key, active in batch.get("expected_status", {}).items()}
        from .reviewed import dependencies as review_dependencies
        dependencies.update(review_dependencies(self, batch, before_members, targets, expected_heads))
        missing = dependencies - targets - expected_heads.keys()
        if missing:
            raise ValueError('Existing dependencies require prepare UUID and expected revision: ' +
                             ', '.join(sorted(_sql(value) for value in missing)))
        for target in sorted(targets | dependencies, key=lambda value: (value.table, _sql(value.key))):
            record = _sql(target)
            if target in expected_heads:
                statements.append(f"IF {record}.knowledge_revision != {_sql(expected_heads[target])} "
                                  "{ THROW 'Knowledge revision changed; prepare and read again'; };")
                if target in expected_status or target in dependencies - targets:
                    active = expected_status.get(target, True)
                    statements.append(f"IF ({record}.stale = false AND {record}.retired = false) != {_sql(active)} "
                                      "{ THROW 'Knowledge revision changed; prepare and read again (availability changed)'; };")
            else:
                statements.append(f"IF {record}.id != NONE "
                                  "{ THROW 'Existing knowledge requires expected revision; prepare and read again'; };")
            # Force a write conflict when a checked dependency changes before
            # commit; SurrealDB snapshot reads alone permit write skew.
            if target in dependencies:
                guard = "_guard_" + uuid4().hex
                statements.append(f"UPDATE {record} SET {guard}=true RETURN NONE;")
                statements.append(f"UPDATE {record} UNSET {guard} RETURN NONE;")
        for expected in batch["sources"]:
            if expected.get("deleted"):
                previous = by_id[expected["id"]] if "id" in expected else by_path[expected["path"]]
                if expected["revision"] != previous["revision"]:
                    raise ValueError(f"Deleted source revision mismatch for {previous['path']}")
                if (self.config.root / previous["path"]).exists():
                    raise ValueError(f"Deleted source exists again: {previous['path']}")
                current[previous["path"]] = None
                record = _record(previous["id"])
                statements.append(f"IF {_sql(record)}.version != {_sql(_record(previous['version']))} {{ THROW 'Concurrent source version changed'; }};")
                statements.append(f"UPDATE {_sql(record)} SET deleted=true;")
                retired_versions = self._execute(f"SELECT VALUE id FROM source_version WHERE source={_sql(record)};")[0]
                refs = [_record(ref) for ref in retired_versions]
                statements.extend(invalidate(self, refs, "needs_review"))
                statements.extend(set_state(ref, "retired") for ref in refs)
                continue
            source = self._load_source(expected["path"], expected.get("kind"))
            if source.revision != expected["revision"]:
                raise ValueError(f"Source revision mismatch for {source.path}: expected {expected['revision']}, found {source.revision}")
            current[source.path] = source
            previous = by_id[expected["id"]] if "id" in expected else by_path.get(source.path)
            record = _record(previous["id"]) if previous else _Record("source", uuid4().hex)
            marker = source_private(source.path) if legacy_rules else expected['private']
            if previous:
                statements.append(f"IF {_sql(record)}.version != {_sql(_record(previous['version']))} {{ THROW 'Concurrent source version changed'; }};")
            snapshot = {"source": record, "revision": source.revision, "path": source.path,
                        "private": marker, "privacy_rules_revision": rules_hash}
            if previous and previous['revision'] == source.revision and previous['path'] == source.path:
                old_snapshot = self._execute(f"SELECT * FROM ONLY {_sql(_record(previous['version']))};")[0]
                if (old_snapshot.get('private') is not False and marker is False
                        and old_snapshot.get('unavailable_gaps') and 'unavailable_gaps' not in expected):
                    raise ValueError('Public source requires explicit review of private unavailable gaps')
                snapshot.update({key: old_snapshot[key] for key in ("dispositions", "deferred_refinement", "unavailable_gaps")
                                 if key in old_snapshot})
            snapshot.update({key: expected[key] for key in ("dispositions", "deferred_refinement", "unavailable_gaps")
                             if key in expected})
            kind = "image" if isinstance(source, ImageSource) else "text"
            if kind == "image":
                assets[source.path] = retain_image(self.config.memory_dir, source)
                snapshot.update({"kind": kind, "asset": assets[source.path]})
            else:
                snapshot.update({"kind": kind, "text": source.text})
            # The original hash, path and decisions together identify one immutable snapshot.
            metadata = {key: value for key, value in snapshot.items() if key not in {"source", "text"}}
            identity = json.dumps({"source": _sql(record), **metadata}, ensure_ascii=False, sort_keys=True,
                                  separators=(",", ":"))
            version = _Record("source_version", _digest(identity))
            sources[source.path], versions[source.path] = record, version
            try:
                present = self._execute(f"SELECT VALUE id FROM ONLY {_sql(version)};")[0]
                source_statements = [] if present else _snapshot_sql(version, snapshot)
                for statement in source_statements:
                    if _query_wire_size(statement) > _MESSAGE_LIMIT:
                        raise ValueError(f"One SQL statement exceeds the {_MESSAGE_LIMIT}-byte WebSocket message limit "
                                         f"({_query_wire_size(statement)} encoded bytes)")
            except ValueError as error:
                error.add_note(f"Source {source.path}: {source.size} original bytes; "
                               f"{_query_wire_size(f'UPSERT {_sql(version)} CONTENT {_sql(snapshot)} RETURN NONE;')} "
                               "encoded snapshot bytes")
                raise
            statements.extend(source_statements)
            snapshots[version] = snapshot
            statements.append(f"UPSERT {_sql(record)} CONTENT {_sql({'path':source.path, 'kind':kind, 'revision':source.revision, 'size':source.size, 'mtime_ns':source.mtime_ns, 'version':version, 'deleted':False, 'private':snapshot['private'], 'privacy_rules_revision':rules_hash})};")
        existing = {_record(item["id"]).key: item for item in before_members}
        affected = self._affected(current, before_members)
        for item in batch.get("members", []):
            key = _record(item["id"]).key
            intended_text = (_original(current[item["path"]], item["start_line"], item["end_line"], item.get("locator"))
                             if item["kind"] == "chunk" else item["text"])
            if key in existing and existing[key].get("description_revision", existing[key]["input_revision"]) != _input_revision(item.get("title", ""), intended_text):
                affected.add(existing[key]["id"])
        affected.update(existing[_record(value).key]["id"] for value in batch.get("delete_members", []))
        affected = self._expand_affected(affected, before_members)
        context = batch.get("context", {})
        # Source changes alone do not withdraw published knowledge. Explicit
        # retirement does invalidate active knowledge that depends on it.
        retired = self._affected({path: source for path, source in current.items() if source is None}, before_members)
        retired.update(existing[_record(value).key]["id"] for value in batch.get("delete_members", []))
        retired = self._expand_affected(retired, before_members)
        statements.extend(self._invalidate_sql(retired, "retired", context))
        for path, source in current.items():
            if source is None:
                statements.append(f"UPDATE member SET retired=true "
                                  f"WHERE source={_sql(_record(by_path[path]['id']))};")
        submitted = {}
        for item in batch.get("members", []):
            source = current[item["path"]]
            text = item["text"] if item["kind"] != "chunk" else None
            title = item.get("title", "")
            value = {
                "source": sources[source.path], "path": source.path, "source_revision": source.revision,
                "source_version": versions[source.path], "kind": item["kind"],
                "parent": _record(item["parent"]) if item.get("parent") else None,
                "title": title, "text": text, "stale": False, "retired": False,
                "knowledge_revision": uuid4().hex,
                "mandatory": item.get("mandatory", False), "coverage_gaps": item.get("coverage_gaps", []),
                "conditions": item.get("conditions", ""), "claim_type": item.get("claim_type", ""),
            }
            if isinstance(source, ImageSource):
                if item["kind"] != "image":
                    raise ValueError(f"Image source requires image member: {item['id']}")
                value.update({"start_line": None, "end_line": None, "asset": assets[source.path],
                              "locator": item.get("locator", {}), "raw_revision": source.revision,
                              "input_revision": source.revision, "description_revision": _input_revision(title, text),
                              "embedding_kind": "image", "description_kind": "agent_visual_read"})
            else:
                raw = _original(source, item["start_line"], item["end_line"], item.get("locator"))
                lines = source.text.splitlines()
                outside = lines[:item["start_line"] - 1] + lines[item["end_line"]:]
                locator = item.get("locator")
                if locator:
                    raw_lines = source.text.splitlines(keepends=True)
                    outside += [raw_lines[item["start_line"] - 1][:locator["start_col"]],
                                raw_lines[item["end_line"] - 1][locator["end_col"]:]]
                if item["kind"] == "file" and not item.get("coverage_gaps") and any(line.strip() for line in outside):
                    raise ValueError(f"Partial file summary requires explicit coverage_gaps: {item['id']}")
                if item["kind"] == "chunk":
                    if "text" in item and item["text"] != raw:
                        raise ValueError(f"Chunk {item['id']} text differs from its original range")
                    text = raw
                elif item["kind"] not in {"file", "section"}:
                    raise ValueError(f"Unknown member kind: {item['kind']}")
                value.update({"text": text, "start_line": item["start_line"], "end_line": item["end_line"],
                              "locator": item.get("locator"), "raw_revision": _digest(raw), "input_revision": _input_revision(title, text),
                              "embedding_kind": "text"})
            submitted[_record(item["id"]).key] = value
        if submitted:
            from .candidate_vectors import encode_candidates
            records = [_record(item["id"]) for item in batch.get("members", [])]
            old_vectors = self._execute(f"SELECT * FROM member WHERE id IN {_sql(records)};")[0]
            encode_candidates(self, submitted, {_record(row["id"]).key: row for row in old_vectors},
                              timeout=timeout, control=control)
        def basis(ids):
            result = []
            for value in ids:
                key = _record(value).key
                member = submitted[key] if key in submitted else existing[key]
                if key not in submitted:
                    if member["stale"] or member["id"] in affected:
                        raise ValueError(f"Evidence must be reread and accepted: {member['id']}")
                    source = self._load_source(member["path"], member["kind"])
                    if source.revision != member["source_revision"]:
                        unchanged = (not isinstance(source, ImageSource) and
                                     _matches_original(source, member))
                        if not unchanged:
                            raise ValueError(f"Evidence source revision mismatch for {member['path']}")
                result.append({"member": _record(value), "input_revision": member["input_revision"],
                               "knowledge_revision": member["knowledge_revision"],
                               "description_revision": member.get("description_revision"),
                               "source_version": _record(member["source_version"]) if isinstance(member["source_version"], str) else member["source_version"],
                               "start_line": member["start_line"], "end_line": member["end_line"],
                               "locator": member.get("locator")})
            return result

        writes = []
        for item in batch.get("members", []):
            value = submitted[_record(item["id"]).key]
            value["basis"] = basis(item.get("evidence", []))
            if item.get("parent"):
                parent_key = _record(item["parent"]).key
                parent = submitted.get(parent_key) or existing.get(parent_key)
                value["parent_version"] = {"id": _record(item["parent"]),
                                           "knowledge_revision": parent["knowledge_revision"] if parent else None}
            else:
                value["parent_version"] = None
            writes.append((_record(item["id"]), value, "member"))
        for item in batch.get("nodes", []):
            if not item["evidence"]:
                raise ValueError(f"Knowledge node requires original evidence: {item['id']}")
            writes.append((_record(item["id"], "node"), {
                "kind": item["kind"], "text": item["text"], "basis": basis(item["evidence"]),
                "conditions": item.get("conditions", ""), "claim_type": item.get("claim_type", ""),
                "stale": False, "retired": False, "knowledge_revision": uuid4().hex}, "node"))
        accepted = {(record, value["knowledge_revision"]): value for record, value, _ in writes}

        def source_version(version):
            record = _record(version, "source_version")
            if record not in snapshots:
                snapshots[record] = self._execute(f"SELECT * FROM ONLY {_sql(record)};")[0]
            return snapshots[record]

        def knowledge_version(record, revision):
            target = _record(record)
            key = (target, revision)
            if key not in accepted:
                accepted[key] = read_knowledge(self, target, knowledge_revision=revision)
            return {**accepted[key], "id": target}

        frozen_private = batch.get("compiled_private")
        if "prepare_packages" in batch:
            if not isinstance(frozen_private, dict):
                raise ValueError("Frozen author batch requires compiled_private")
            expected_private_ids = {_record(item["id"], table) for table, field in
                                    (("member", "members"), ("node", "nodes"), ("semantic", "edges"))
                                    for item in batch.get(field, [])}
            frozen_private = {_record(identity): marker for identity, marker in frozen_private.items()}
            if set(frozen_private) != expected_private_ids or any(type(marker) is not bool for marker in frozen_private.values()):
                raise ValueError("Frozen private markers must cover exactly the written records")

        def mark_private(record, value):
            marker = derive_private(value, source_version=source_version, knowledge_version=knowledge_version)
            if marker is None:
                raise ValueError("Private marker requires retained version-pinned provenance")
            if frozen_private is not None and frozen_private[record] != marker:
                raise ValueError(f"Frozen private marker changed for {record}")
            value["private"] = marker

        for record, value, _ in writes:
            mark_private(record, value)
        graph = Publication(self, writes, versions, source_version, knowledge_version)
        for version in versions.values():
            source = snapshots[version]["source"]
            previous = by_id.get(f"{source.table}:{source.key}")
            statements.extend(graph.source(version, snapshots[version], previous["version"] if previous else None))
        for record, value, _ in writes:
            statements.append(f"CREATE {_sql(_Record('change', uuid4().hex))} SET operation='accept', target={_sql(record)}, previous=(SELECT * OMIT embedding FROM ONLY {_sql(record)}), at=time::now(), context={_sql(context)};")
            # MERGE preserves derived vectors; input_revision gates their validity.
            statements.append(f"UPSERT {_sql(record)} MERGE {_sql(value)} RETURN NONE;")
        for record, value, _ in writes:
            statements.extend(graph.knowledge_facts(record, value, expected_heads.get(record)))

        edge_ids = [_record(item["id"], "semantic") for item in batch.get("edges", [])]
        if edge_ids:
            edge_rows, edge_names = self._execute(
                f"SELECT * FROM semantic WHERE id IN {_sql(edge_ids)}; "
                f"RETURN [{', '.join(f'<string>{_sql(record)}' for record in edge_ids)}];")
            previous_edges = {_record(row["id"]): row for row in edge_rows}
        else:
            edge_names, previous_edges = [], {}
        for record in edge_ids:
            statements.append(f"CREATE {_sql(_Record('change', uuid4().hex))} SET operation='accept_edge', target={_sql(record)}, previous=(SELECT * FROM ONLY {_sql(record)}), at=time::now(), context={_sql(context)};")
        statements.extend(graph.business(batch.get("edges", []), basis, previous_edges, frozen_private))

        def previous_exact(record):
            if record.table == "semantic":
                row = self._execute(f"SELECT * FROM ONLY {_sql(record)};")[0]
                return _record(row["head"])
            return graph.version(record, expected_heads[record]).record

        for table, key in [("member", "delete_members"), ("node", "delete_nodes"), ("semantic", "delete_edges")]:
            for value in batch.get(key, []):
                record = _record(value, table)
                exact = previous_exact(record)
                statements.append(f"CREATE {_sql(_Record('change', uuid4().hex))} SET operation='retire', target={_sql(record)}, previous=(SELECT * OMIT embedding FROM ONLY {_sql(record)}), at=time::now(), context={_sql(context)};")
                statements.extend(invalidate(self, [exact], "needs_review"))
                statements.append(set_state(exact, "retired"))
                statements.append(f"UPDATE {_sql(record)} SET stale=true, retired=true;")
        for correction in batch.get("corrections", []):
            target = _record(correction["target"])
            # The snapshot precedes all accepts in the transaction.
            statements.insert(1, f"CREATE {_sql(_record(correction['id'], 'change'))} SET operation='correction', target={_sql(target)}, reason={_sql(correction['reason'])}, previous=(SELECT * OMIT embedding FROM ONLY {_sql(target)}), at=time::now(), context={_sql(context)};")
        # A correction without a replacement marks the known error unavailable.
        for correction in batch.get("corrections", []):
            target = _record(correction["target"])
            if target in expected_heads:
                statements.extend(invalidate(self, [previous_exact(target)], "needs_review"))
            if target in {_record(item["id"], table) for table, key in
                          [("member", "members"), ("node", "nodes"), ("semantic", "edges")]
                          for item in batch.get(key, [])}:
                continue
            if target.table == "member":
                correction_affected = self._expand_affected({existing[target.key]["id"]}, before_members)
                statements.extend(self._invalidate_sql(correction_affected, "correction", context))
                retired.update(correction_affected)
            else:
                statements.append(f"UPDATE {_sql(target)} SET stale=true;")
        for parent in parents:
            record = _sql(parent)
            statements.append(f"IF {record}.id = NONE OR {record}.retired = true "
                              "{ THROW 'Parent member does not exist or is retired'; };")
        statements.extend(graph.availability_guards())
        result = {"sources": len(current), "members": len(submitted), "nodes": len(batch.get("nodes", [])),
                  "edges": len(batch.get("edges", [])), "invalidated": sorted(retired)}
        if graph.relationships:
            result["edge_versions"] = {
                name: f"graph_edge:{graph.relationships[record].record.key}"
                for record, name in zip(edge_ids, edge_names, strict=True)}
        statements.append(f"CREATE {_sql(receipt)} CONTENT {_sql({'batch_hash': batch_hash, 'result': result})};")
        statements.append("COMMIT;")
        # Encoding may take time; never publish a candidate from a changed original.
        from basepack.project.config import load_project_config
        current_config = load_project_config(self.config.path) if self.config.path.is_file() else self.config
        if privacy_rules(current_config) != rules:
            raise ValueError('Private classification rules changed during publication; freeze again')
        for expected in batch["sources"]:
            if expected.get("deleted"):
                previous = by_id[expected["id"]] if "id" in expected else by_path[expected["path"]]
                if (self.config.root / previous["path"]).exists():
                    raise ValueError(f"Deleted source exists again: {previous['path']}")
            else:
                source = self._load_source(expected["path"], expected.get("kind"))
                if source.revision != expected["revision"]:
                    raise ValueError(f"Source revision mismatch for {source.path}: expected {expected['revision']}, found {source.revision}")
        self._publish(statements, control=control)
        return result

    def search(self, text: str, *, scope: str = "", limit: int = 10, literal: bool = False,
               allow_private: bool = True, access: bool = True) -> list[dict]:
        """Return lexical candidates for hybrid retrieval."""
        from .query import normalize_scope
        scope = normalize_scope(scope)
        if literal:
            match = (f"string::contains(string::lowercase(path + '\\n' + title + '\\n' + text), "
                     f"string::lowercase({_sql(text)}))")
            score = "0.0"
        else:
            match = f"(text @1@ {_sql(text)} OR title @2@ {_sql(text)})"
            score = "search::score(1) + search::score(2)"
        privacy = "" if allow_private else "AND private=false "
        rows = self._execute(f"SELECT *, source_revision AS revision, {score} AS lexical_score OMIT {_CANDIDATE_OMIT} FROM member "
                             f"WHERE stale=false AND retired!=true AND {match} "
                             f"AND string::starts_with(path, {_sql(scope)}) {privacy}"
                             f"ORDER BY lexical_score DESC, id ASC LIMIT {int(limit)};")[0]
        return self.access_hints(rows) if access else rows

    def read(self, member_id: str, *, source_version: str | None = None,
             start_line: int | None = None, end_line: int | None = None,
             locator: dict | None = None, knowledge_revision: str | None = None) -> dict:
        if _record(member_id).table != "member":
            raise ValueError("read requires a member ID; inspect node/edge evidence via neighbors")
        if knowledge_revision is None:
            member = self._execute(f"SELECT * OMIT embedding FROM ONLY {_sql(_record(member_id))};")[0]
            if member is None:
                raise ValueError(f"Member not found: {member_id}")
        else:
            member = self.knowledge(member_id, knowledge_revision=knowledge_revision)
        version = source_version or member["source_version"]
        snapshot = self._execute(f"SELECT * FROM ONLY {_sql(_record(version, 'source_version'))};")[0]
        if snapshot is None:
            raise ValueError(f"Source snapshot not found: {version}")
        same_source = _record(snapshot["source"]) == _record(member["source"])
        history = []
        if source_version is not None and (not same_source or "path" not in snapshot):
            direct, nested = self._execute(
                f"SELECT previous.path AS path, previous.source_version AS source_version FROM change "
                f"WHERE target={_sql(_record(member_id))} AND previous.source={_sql(_record(snapshot['source']))}; "
                f"SELECT VALUE previous.members[WHERE id={_sql(_record(member_id))} "
                f"AND source={_sql(_record(snapshot['source']))}] FROM change "
                f"WHERE previous.members.*.id CONTAINS {_sql(_record(member_id))};")
            history = direct + [record for group in nested for record in group]
        if not same_source and not history:
            raise ValueError(f"Source snapshot does not belong to member {member_id}: {version}")
        source = self._execute(f"SELECT * FROM ONLY {_sql(_record(snapshot['source']))};")[0]
        if source is None:
            raise ValueError(f"Snapshot source not found: {snapshot['source']}")
        if "path" in snapshot:
            path = snapshot["path"]
        else:
            accepted = history + ([member] if same_source else [])
            exact = [record for record in accepted if
                     _record(record["source_version"]) == _record(version, "source_version")]
            accepted_paths = {record["path"] for record in exact or accepted}
            if len(accepted_paths) != 1:
                raise ValueError(f"Source snapshot has ambiguous historical paths for member {member_id}: {version}")
            path = accepted_paths.pop()
        if snapshot["kind"] == "image":
            if locator is None and source_version is None:
                locator = member.get("locator")
        elif source_version is None:
            start_line, end_line = member["start_line"], member["end_line"]
            if locator is None:
                locator = member.get("locator")
        elif start_line is None or end_line is None:
            raise ValueError("Reading an explicit source version requires start_line and end_line")
        original = _read_original(self.config, snapshot, path, version, start_line, end_line, locator,
                                  member_id=member["id"])
        return {"member": self.access_hints([member])[0], "original": original}

    def neighbors(self, record_id: str, *, include_stale: bool = False,
                  knowledge_revision: str | None = None, direction: str = "both",
                  types=(), scope: str = "", allow_private: bool = True, conditions: dict | None = None) -> dict:
        from .graph_query_store import neighbors
        return neighbors(self, record_id, include_stale=include_stale, knowledge_revision=knowledge_revision,
                         direction=direction, types=types, scope=scope, allow_private=allow_private,
                         conditions=conditions)

    def basis_dependents(self, anchors: list[dict], *, scope: str = "", allow_private: bool = True) -> list[dict]:
        """Find current knowledge that explicitly cites observed member and source versions."""
        fields = ("id", "knowledge_revision", "source_version")
        if not isinstance(anchors, list):
            raise ValueError("Basis anchors must be a JSON array")
        observed = {}
        for anchor in anchors:
            if not isinstance(anchor, dict) or any(not isinstance(anchor.get(field), str) or not anchor[field]
                                                  for field in fields):
                raise ValueError("Each basis anchor requires id, knowledge_revision and source_version strings")
            member = _record(anchor["id"])
            source = _record(anchor["source_version"], "source_version")
            if member.table != "member" or source.table != "source_version":
                raise ValueError("Basis anchors require a member ID and a source_version ID")
            observed.setdefault((member, anchor["knowledge_revision"], source), {field: anchor[field] for field in fields})
        if not observed:
            return []
        from .graph_query_store import basis_dependents
        return basis_dependents(self, observed, scope=scope, allow_private=allow_private)

    def brief(self, task: str = "", *, limit: int = 6) -> dict:
        """Read published startup material without searching or inspecting originals."""
        sources = self.sources()
        mandatory, stale_members, stale_nodes, stale_edges, gaps, overview, overview_nodes = self._execute(
            "SELECT * OMIT embedding FROM member WHERE mandatory=true AND retired!=true; "
            "SELECT id,path,kind,private FROM member WHERE stale=true AND retired!=true; "
            "SELECT id,kind,private FROM node WHERE stale=true AND retired!=true; "
            "SELECT id,head.type AS kind,head.private AS private FROM semantic WHERE stale=true AND retired!=true; "
            "SELECT id,path,private,coverage_gaps AS gaps FROM member WHERE retired!=true AND array::len(coverage_gaps)>0; "
            "SELECT * OMIT embedding FROM member WHERE stale=false AND retired!=true AND mandatory=false AND kind IN ['file','section','image']; "
            "SELECT * FROM node WHERE stale=false AND retired!=true;")
        registered = {_record(row["id"]): row for row in sources}
        basis_versions = {_record(basis["source_version"], "source_version")
                          for row in mandatory for basis in row.get("basis", [])}
        snapshots = self._execute(
            f"SELECT id,source,revision FROM source_version WHERE id IN {_sql(list(basis_versions))};")[0] if basis_versions else []
        snapshots = {_record(row["id"]): row for row in snapshots}
        for row in mandatory:
            source = registered.get(_record(row["source"]))
            mismatches = []
            for basis in row.get("basis", []):
                snapshot = snapshots.get(_record(basis["source_version"], "source_version"))
                evidence_source = registered.get(_record(snapshot["source"])) if snapshot else None
                if evidence_source and (evidence_source["revision"] != snapshot["revision"] or evidence_source["deleted"]):
                    mismatches.append({"id": basis["member"], "source_version": basis["source_version"],
                                       "accepted_source_revision": snapshot["revision"],
                                       "registered_source_revision": evidence_source["revision"],
                                       "registered_source_deleted": evidence_source["deleted"]})
            row["known_unsynced"] = bool(mismatches or source and (
                source["revision"] != row["source_revision"] or source["deleted"]))
            row["sync_evidence"] = {"accepted_source_revision": row["source_revision"],
                                    "registered_source_revision": source["revision"] if source else None,
                                    "basis_mismatches": mismatches,
                                    "note": "Registered source metadata only; originals not checked."}
        stale = stale_members + stale_nodes + stale_edges
        from datetime import datetime, timezone
        from .query import overview_working_set, startup_overview
        chat_prefix = (self.config.memory_dir / "codex").resolve().relative_to(self.config.root.resolve()).as_posix()
        rotation = datetime.now(timezone.utc).date().isoformat()
        workset = overview_working_set(overview, overview_nodes, limit, chat_prefix=chat_prefix, rotation=rotation)
        candidates = self.access_hints(workset) if workset else []
        maps = startup_overview(overview, overview_nodes, sources, limit, mandatory=mandatory,
                                chat_prefix=chat_prefix, candidates=candidates)
        clues = maps["clues"]
        fields = {"id", "kind", "title", "text", "path", "source_revision", "source_version", "start_line", "end_line",
                  "parent", "parent_version", "stale", "retired", "coverage_gaps", "locator", "clue_role", "knowledge_revision",
                  "conditions", "claim_type", "known_unsynced", "sync_evidence", "private", "record_type", "text_truncated",
                  "access_interval", "access_status", "access_model", "access_compiled_j", "access_fact_j",
                  "access_support", "access_prior"}
        def startup_item(row):
            item = {key: value for key, value in row.items() if key in fields}
            if row.get("record_type") == "node" and "basis" in row:
                item["basis"] = row["basis"]
            return item
        detail_limit = max(20, limit)
        codex = self.connection.get("codex", {})
        project_id = codex.get("project_id")
        codex_collection = {"project_id": project_id,
                            "status": ("not_checked" if project_id and codex.get("registry_complete") else
                                       "registry_incomplete" if project_id else "unavailable"),
                            "note": "Brief does not collect chats. Discovery and collection do not mean semantic acceptance or vector coverage."}
        return {"mandatory": [startup_item(row) for row in mandatory],
                "mandatory_pending_count": sum(row["stale"] for row in mandatory),
                "mandatory_known_unsynced_count": sum(row["known_unsynced"] for row in mandatory),
                "clues": [startup_item(row) for row in clues],
                "overview_groups": maps["overview_groups"], "overview_count": maps["overview_count"],
                "overview_sampling": {"candidates": len(workset), "rotation_utc_date": rotation},
                "clues_omitted_count": maps["clues_omitted_count"], "unmapped_sources": maps["unmapped_sources"],
                "unmapped_count": maps["unmapped_count"], "unmapped_omitted_count": maps["unmapped_omitted_count"],
                "pending": stale[:detail_limit], "pending_count": len(stale),
                "sources": [{key: row[key] for key in ("id", "path", "kind", "deleted", "private") if key in row}
                            for row in sources[:detail_limit]],
                "source_count": len(sources),
                "coverage_gaps": gaps[:detail_limit], "coverage_gaps_count": len(gaps),
                "coverage_gaps_omitted_count": max(0, len(gaps) - detail_limit),
                "vector_coverage": {"status": "not_checked"},
                "codex_collection": codex_collection,
                "discovery_scope": self.connection.get("source_scope", []),
                "change_check": "not checked by brief. Use memory check-file-changes to compare files."}

    def sources(self) -> list[dict]:
        """List source metadata for explicit inventory or deep-maintenance sampling."""
        return self._execute("SELECT id,path,revision,size,mtime_ns,deleted,kind,private,privacy_rules_revision FROM source ORDER BY path;")[0]

    def changes(self, scope: list[str], *, deep: bool = False) -> list[dict]:
        return self._check_changes(self.sources(), scope, deep=deep)

    def maintain(self, scope: list[str], *, include_registered: bool = False, control: str | None = None,
                 timeout: float = 600, expected_snapshots: dict[str, str] | None = None,
                 discover_graph: bool = False) -> dict:
        """Run deterministic maintenance and retain the semantic handoff."""
        from .maintenance import maintain
        from .owner import check_owned
        if not control:
            raise ValueError("Maintenance requires the project owner's control")
        check_owned(self.config.memory_dir, control)
        return maintain(self, scope, include_registered=include_registered, control=control, timeout=timeout,
                        expected_snapshots=expected_snapshots, discover_graph=discover_graph)

    def _check_changes(self, known: list[dict], scope: list[str], *, deep: bool,
                       expected_snapshots: dict[str, str] | None = None) -> list[dict]:
        expected_snapshots = expected_snapshots or {}
        changes = detect_changes(self.config.root, [source for source in known if not source.get("deleted")], scope,
                                 deep=deep, expected_snapshots=expected_snapshots)
        changes = {change.path: asdict(change) for change in changes}
        rules = privacy_rules(self.config)
        selected = [_project_path(self.config.root.resolve(), path) for path in scope]
        for source in known:
            path = _project_path(self.config.root.resolve(), source['path'])
            if (source.get('deleted') or not path.is_file() or
                    not any(path == prefix or path.is_relative_to(prefix) for prefix in selected)):
                continue
            previous = source.get('private', source_private(source['path']))
            if previous != source_private(source['path'], rules['private_scope']):
                if source['path'] not in changes:
                    current = self._load_source(source['path'], source.get('kind'),
                                                expected_revision=expected_snapshots.get(source['path']))
                    changes[source['path']] = {'path': current.path, 'kind': 'modified',
                                               'revision': current.revision, 'size': current.size,
                                               'mtime_ns': current.mtime_ns}
                changes[source['path']]['privacy_changed'] = True
        return [changes[path] for path in sorted(changes)]

    def embed_members(self, ids: list[str] | None = None, *, timeout: float = 600) -> dict:
        from .vectors import embed_members
        return embed_members(self, ids, timeout=timeout)

    def vector_search(self, text: str, *, scope: str = "", limit: int = 12, timeout: float = 600,
                      allow_private: bool = True, access: bool = True):
        from .vectors import vector_search
        from .query import normalize_scope
        result = vector_search(self, text, scope=normalize_scope(scope), limit=limit, timeout=timeout,
                               allow_private=allow_private)
        if access:
            result["matches"] = self.access_hints(result["matches"])
        return result

    def hybrid_search(self, text: str, *, scope: str = "", limit: int = 12, timeout: float = 600,
                      literal: bool = False, allow_private: bool = True, access: bool = True):
        from .vectors import hybrid_search
        from .query import normalize_scope
        result = hybrid_search(self, text, scope=normalize_scope(scope), limit=limit, timeout=timeout, literal=literal,
                               allow_private=allow_private)
        if access:
            result["matches"] = self.access_hints(result["matches"])
        return result
