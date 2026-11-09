"""Project memory actions over native SurrealDB records and transactions."""

from base64 import b64encode
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from hashlib import sha256
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

from basepack.project.config import ProjectConfig
from .content import SourceContent, detect_changes, numbered_text, read_member, read_source, reading_units
from .images import IMAGE_SUFFIXES, ImageSource, read_image, retain_image


@dataclass(frozen=True)
class _Record:
    table: str
    key: str


def _record(value: str, table: str = "member") -> _Record:
    if ":" in value:
        table, value = value.split(":", 1)
    return _Record(table, value.removeprefix("⟨").removesuffix("⟩"))


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


def _original(source: SourceContent, start: int, end: int) -> str:
    lines = source.text.splitlines(keepends=True)
    if not 1 <= start <= end <= len(lines):
        raise ValueError(f"Invalid line range {start}:{end} for {source.path}")
    return "".join(lines[start - 1:end])


class Memory:
    """Bind every action to one explicit project and its native database."""

    def __init__(self, config: ProjectConfig):
        self.config = config
        self.connection = config.raw["memory"]

    def _execute(self, sql: str, *, check_project: bool = True) -> list:
        connection = self.connection
        credential = f"{connection['username']}:{os.environ[connection['password_env']]}"
        if check_project:
            sql = (f"IF meta:project.project_id != {_sql(connection['project_id'])} "
                   "{ THROW 'Memory database belongs to another project or is not initialized'; };\n" + sql)
        request = Request(connection["endpoint"].rstrip("/") + "/sql", sql.encode("utf-8"), {
            "Authorization": "Basic " + b64encode(credential.encode()).decode(),
            "surreal-ns": connection["namespace"], "surreal-db": connection["database"],
            "Accept": "application/json", "Content-Type": "text/plain; charset=utf-8",
        })
        try:
            with urlopen(request, timeout=30) as response:
                statements = json.load(response)
        except HTTPError as error:
            error.add_note(error.read().decode("utf-8"))
            raise
        errors = [statement["result"] for statement in statements if statement["status"] != "OK"]
        if errors:
            raise RuntimeError("\n".join(str(error) for error in errors))
        return [statement["result"] for statement in statements][1 if check_project else 0:]

    def install_schema(self) -> dict:
        # Schema installation is idempotent; binding is a native transaction.
        namespace = "`" + self.connection["namespace"].replace("`", "\\`") + "`"
        database = "`" + self.connection["database"].replace("`", "\\`") + "`"
        self._execute(f"DEFINE NAMESPACE IF NOT EXISTS {namespace}; USE NS {namespace}; "
                      f"DEFINE DATABASE IF NOT EXISTS {database};", check_project=False)
        self._execute(Path(__file__).with_name("schema.surql").read_text(encoding="utf-8"), check_project=False)
        project_id = _sql(self.connection["project_id"])
        self._execute("BEGIN; "
                      f"IF meta:project.project_id != NONE AND meta:project.project_id != {project_id} "
                      "{ THROW 'Memory database belongs to another project'; }; "
                      f"UPSERT meta:project SET project_id={project_id}; COMMIT;", check_project=False)
        return {"namespace": self.connection["namespace"], "database": self.connection["database"]}

    def _rows(self, table: str) -> list[dict]:
        return self._execute(f"SELECT * OMIT embedding FROM {table};")[0]

    def _load_source(self, path: str, kind: str | None = None) -> SourceContent | ImageSource:
        if kind == "image" or Path(path).suffix.lower() in IMAGE_SUFFIXES:
            return read_image(self.config.root, path)
        return read_source(self.config.root, path)

    def prepare(self, paths: list[str]) -> dict:
        """Supply explicit new/old originals and existing knowledge for one reading."""
        known = {source["path"]: source for source in self._rows("source")}
        members = self._rows("member")
        prepared = []
        ids = []
        for path in paths:
            try:
                source = self._load_source(path)
            except FileNotFoundError:
                if Path(path).as_posix() not in known:
                    raise
                item = {"path": Path(path).as_posix(), "deleted": True}
            else:
                item = {"path": source.path, "revision": source.revision, "size": source.size,
                        "mtime_ns": source.mtime_ns}
                if isinstance(source, ImageSource):
                    item.update({"kind": "image", "image_path": str(self.config.root / source.path)})
                else:
                    item.update({"kind": "text", "numbered_text": numbered_text(source),
                                 "reading_units": [{"kind": unit.kind, "start_line": unit.start_line, "end_line": unit.end_line}
                                                   for unit in reading_units(source)]})
            item["members"] = [row for row in members if row["path"] == item["path"]]
            previous = known.get(item["path"])
            if previous:
                snapshot = self._execute(f"SELECT * FROM ONLY {_sql(_record(previous['version']))};")[0]
                item["id"] = previous["id"]
                if snapshot.get("kind") == "image":
                    item["previous"] = {"revision": previous["revision"], "kind": "image",
                                        "image_path": str(self.config.memory_dir / snapshot["asset"])}
                else:
                    old = SourceContent(item["path"], previous["revision"], previous["size"],
                                        previous["mtime_ns"], snapshot["text"])
                    item["previous"] = {"revision": old.revision, "numbered_text": numbered_text(old)}
            prepared.append(item)
            ids.extend(member["id"] for member in item["members"])
        edges = self._execute("SELECT * FROM semantic WHERE "
                              f"in IN {_sql([_record(i) for i in ids])} OR "
                              f"out IN {_sql([_record(i) for i in ids])} OR "
                              f"basis.*.member CONTAINSANY {_sql([_record(i) for i in ids])};")[0] if ids else []
        nodes = self._rows("node")
        expected = {row["id"]: row["knowledge_revision"] for row in
                    [member for item in prepared for member in item["members"]] + nodes + edges}
        return {"sources": prepared, "neighborhood": {"edges": edges,
                "nodes": nodes}, "expected": expected,
                "instruction": "Read originals together. Choose semantic boundaries, summaries, and evidenced relations in one batch; reading_units are structural hints only."}

    def _affected(self, current: dict[str, SourceContent | ImageSource | None], members: list[dict]) -> set[str]:
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
                    member["raw_revision"] != _digest(_original(source, member["start_line"], member["end_line"]))):
                affected.add(member["id"])
        return self._expand_affected(affected, members)

    @staticmethod
    def _expand_affected(affected: set[str], members: list[dict]) -> set[str]:
        # Containment and accepted summary evidence are both real dependencies.
        while True:
            expanded = affected | {member["id"] for member in members if any(
                basis["member"] in affected for basis in member.get("basis", []))}
            expanded |= {member["parent"] for member in members
                         if member["id"] in affected and member.get("parent")}
            if expanded == affected:
                return affected
            affected = expanded

    def _invalidate_sql(self, affected: set[str], operation: str, context: dict) -> list[str]:
        if not affected:
            return []
        refs = _sql([_record(value) for value in sorted(affected)])
        nodes = f"(SELECT VALUE id FROM node WHERE basis.*.member CONTAINSANY {refs})"
        audit = _sql(_Record("change", uuid4().hex))
        return [f"CREATE {audit} SET operation={_sql(operation)}, at=time::now(), context={_sql(context)}, "
                f"previous={{members:(SELECT * OMIT embedding FROM member WHERE id IN {refs}), "
                f"nodes:(SELECT * FROM node WHERE basis.*.member CONTAINSANY {refs}), "
                f"edges:(SELECT * FROM semantic WHERE basis.*.member CONTAINSANY {refs} OR in IN {refs} OR out IN {refs} OR in IN {nodes} OR out IN {nodes})}};",
                f"UPDATE member SET stale=true WHERE id IN {refs};",
                f"UPDATE node SET stale=true WHERE basis.*.member CONTAINSANY {refs};",
                f"UPDATE semantic SET stale=true WHERE basis.*.member CONTAINSANY {refs} OR in IN {refs} OR out IN {refs} OR in IN {nodes} OR out IN {nodes};"]

    def apply(self, batch: dict) -> dict:
        """Check exact source revisions, then accept one agent batch atomically.

        Unmentioned records and edges survive. Accepted chunk text comes from the
        original, never from generated prose. Corrections retain actual old data.
        """
        known = self._rows("source")
        by_path = {source["path"]: source for source in known}
        by_id = {source["id"]: source for source in known}
        before_members = self._rows("member")
        current = {}
        sources = {}
        versions = {}
        assets = {}
        statements = ["BEGIN;"]
        targets = {_record(item["id"], table) for table, key in
                   [("member", "members"), ("node", "nodes"), ("semantic", "edges")]
                   for item in batch.get(key, [])}
        targets.update(_record(value, table) for table, key in
                       [("member", "delete_members"), ("node", "delete_nodes"), ("semantic", "delete_edges")]
                       for value in batch.get(key, []))
        targets.update(_record(item["target"]) for item in batch.get("corrections", []))
        expected = {_record(key): value for key, value in batch.get("expected", {}).items()}
        for target in sorted(targets, key=lambda value: (value.table, value.key)):
            record = _sql(target)
            if target in expected:
                statements.append(f"IF {record}.knowledge_revision != {_sql(expected[target])} "
                                  "{ THROW 'Knowledge revision changed; prepare and read again'; };")
            else:
                statements.append(f"IF {record}.id != NONE "
                                  "{ THROW 'Existing knowledge requires expected revision; prepare and read again'; };")
        for expected in batch["sources"]:
            if expected.get("deleted"):
                previous = by_id[expected["id"]] if "id" in expected else by_path[expected["path"]]
                if expected["revision"] != previous["revision"]:
                    raise ValueError(f"Deleted source revision mismatch for {previous['path']}")
                if (self.config.root / previous["path"]).exists():
                    raise ValueError(f"Deleted source exists again: {previous['path']}")
                current[previous["path"]] = None
                record = _record(previous["id"])
                statements.append(f"IF {_sql(record)}.revision != {_sql(previous['revision'])} {{ THROW 'Concurrent source revision changed'; }};")
                statements.append(f"UPDATE {_sql(record)} SET deleted=true;")
                continue
            source = self._load_source(expected["path"], expected.get("kind"))
            if source.revision != expected["revision"]:
                raise ValueError(f"Source revision mismatch for {source.path}: expected {expected['revision']}, found {source.revision}")
            current[source.path] = source
            previous = by_id[expected["id"]] if "id" in expected else by_path.get(source.path)
            record = _record(previous["id"]) if previous else _Record("source", uuid4().hex)
            version = _Record("source_version", _digest(record.key + source.revision))
            sources[source.path], versions[source.path] = record, version
            if previous:
                statements.append(f"IF {_sql(record)}.revision != {_sql(previous['revision'])} {{ THROW 'Concurrent source revision changed'; }};")
            snapshot = {"source": record, "revision": source.revision}
            kind = "image" if isinstance(source, ImageSource) else "text"
            if kind == "image":
                assets[source.path] = retain_image(self.config.memory_dir, source)
                snapshot.update({"kind": kind, "asset": assets[source.path]})
            else:
                snapshot.update({"kind": kind, "text": source.text})
            statements.append(f"UPSERT {_sql(version)} CONTENT {_sql(snapshot)};")
            statements.append(f"UPSERT {_sql(record)} CONTENT {_sql({'path':source.path, 'kind':kind, 'revision':source.revision, 'size':source.size, 'mtime_ns':source.mtime_ns, 'version':version, 'deleted':False})};")
        existing = {_record(item["id"]).key: item for item in before_members}
        affected = self._affected(current, before_members)
        for item in batch.get("members", []):
            key = _record(item["id"]).key
            if key in existing and existing[key].get("description_revision", existing[key]["input_revision"]) != _input_revision(item.get("title", ""), item["text"]):
                affected.add(existing[key]["id"])
        affected.update(existing[_record(value).key]["id"] for value in batch.get("delete_members", []))
        affected = self._expand_affected(affected, before_members)
        context = batch.get("context", {})
        statements.extend(self._invalidate_sql(affected, "source_changed", context))
        # Rebind unchanged siblings without changing their representation input.
        accepted = {_record(value["id"]).key for value in batch.get("members", [])}
        for member in before_members:
            if member["path"] in current and member["id"] not in affected and _record(member["id"]).key not in accepted:
                statements.append(f"UPDATE {_sql(_record(member['id']))} SET source_revision={_sql(current[member['path']].revision)}, source_version={_sql(versions[member['path']])};")
                existing[_record(member["id"]).key] = {**member,
                    "source_revision": current[member["path"]].revision, "source_version": versions[member["path"]]}
        submitted = {}
        for item in batch.get("members", []):
            source = current[item["path"]]
            text = item["text"]
            title = item.get("title", "")
            value = {
                "source": sources[source.path], "path": source.path, "source_revision": source.revision,
                "source_version": versions[source.path], "kind": item["kind"],
                "parent": _record(item["parent"]) if item.get("parent") else None,
                "title": title, "text": text, "stale": False,
                "knowledge_revision": uuid4().hex,
                "mandatory": item.get("mandatory", False), "coverage_gaps": item.get("coverage_gaps", []),
            }
            if isinstance(source, ImageSource):
                if item["kind"] != "image":
                    raise ValueError(f"Image source requires image member: {item['id']}")
                value.update({"start_line": None, "end_line": None, "asset": assets[source.path],
                              "locator": item.get("locator", {}), "raw_revision": source.revision,
                              "input_revision": source.revision, "description_revision": _input_revision(title, text),
                              "embedding_kind": "image", "description_kind": "agent_visual_read"})
            else:
                raw = _original(source, item["start_line"], item["end_line"])
                lines = source.text.splitlines()
                outside = lines[:item["start_line"] - 1] + lines[item["end_line"]:]
                if item["kind"] == "file" and not item.get("coverage_gaps") and any(line.strip() for line in outside):
                    raise ValueError(f"Partial file summary requires explicit coverage_gaps: {item['id']}")
                if item["kind"] == "chunk":
                    if text != raw:
                        raise ValueError(f"Chunk {item['id']} text differs from its original range")
                elif item["kind"] not in {"file", "section"}:
                    raise ValueError(f"Unknown member kind: {item['kind']}")
                value.update({"start_line": item["start_line"], "end_line": item["end_line"],
                              "raw_revision": _digest(raw), "input_revision": _input_revision(title, text),
                              "embedding_kind": "text"})
            submitted[_record(item["id"]).key] = value
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
                        raise ValueError(f"Evidence source revision mismatch for {member['path']}")
                result.append({"member": _record(value), "input_revision": member["input_revision"],
                               "knowledge_revision": member["knowledge_revision"],
                               "description_revision": member.get("description_revision"),
                               "source_version": _record(member["source_version"]) if isinstance(member["source_version"], str) else member["source_version"],
                               "start_line": member["start_line"], "end_line": member["end_line"]})
            return result

        writes = []
        for item in batch.get("members", []):
            value = submitted[_record(item["id"]).key]
            value["basis"] = basis(item.get("evidence", []))
            writes.append((_record(item["id"]), value, "member"))
        for item in batch.get("nodes", []):
            if not item["evidence"]:
                raise ValueError(f"Knowledge node requires original evidence: {item['id']}")
            writes.append((_record(item["id"], "node"), {
                "kind": item["kind"], "text": item["text"], "basis": basis(item["evidence"]),
                "stale": False, "knowledge_revision": uuid4().hex}, "node"))
        for record, value, table in writes:
            statements.append(f"CREATE {_sql(_Record('change', uuid4().hex))} SET operation='accept', target={_sql(record)}, previous=(SELECT * OMIT embedding FROM ONLY {_sql(record)}), at=time::now(), context={_sql(context)};")
            if table == "node":
                statements.append(f"IF {_sql(record)}.text != {_sql(value['text'])} OR {_sql(record)}.kind != {_sql(value['kind'])} OR {_sql(record)}.basis != {_sql(value['basis'])} {{ "
                                  f"UPDATE semantic SET stale=true WHERE in={_sql(record)} OR out={_sql(record)}; }};")
            # MERGE preserves derived vectors; input_revision gates their validity.
            statements.append(f"UPSERT {_sql(record)} MERGE {_sql(value)} RETURN NONE;")
        for item in batch.get("edges", []):
            if not item["evidence"]:
                raise ValueError(f"Semantic relation requires original evidence: {item['id']}")
            record = _record(item["id"], "semantic")
            value = {"kind": item["kind"], "text": item["text"], "conditions": item.get("conditions", ""),
                     "basis": basis(item["evidence"]), "stale": False, "knowledge_revision": uuid4().hex}
            statements.append(f"CREATE {_sql(_Record('change', uuid4().hex))} SET operation='accept_edge', target={_sql(record)}, previous=(SELECT * FROM ONLY {_sql(record)}), at=time::now(), context={_sql(context)};")
            statements.append(f"RELATE ({_sql(_record(item['in']))})->({_sql(record)})->({_sql(_record(item['out']))}) CONTENT {_sql(value)};")
        for table, key in [("member", "delete_members"), ("node", "delete_nodes"), ("semantic", "delete_edges")]:
            for value in batch.get(key, []):
                record = _record(value, table)
                statements.append(f"CREATE {_sql(_Record('change', uuid4().hex))} SET operation='retire', target={_sql(record)}, previous=(SELECT * OMIT embedding FROM ONLY {_sql(record)}), at=time::now(), context={_sql(context)};")
                statements.append(f"UPDATE {_sql(record)} SET stale=true, retired=true, knowledge_revision={_sql(uuid4().hex)};")
                if table == "node":
                    statements.append(f"UPDATE semantic SET stale=true WHERE in={_sql(record)} OR out={_sql(record)};")
        for correction in batch.get("corrections", []):
            target = _record(correction["target"])
            # The snapshot precedes all accepts in the transaction.
            statements.insert(1, f"CREATE {_sql(_record(correction['id'], 'change'))} SET operation='correction', target={_sql(target)}, reason={_sql(correction['reason'])}, previous=(SELECT * OMIT embedding FROM ONLY {_sql(target)}), at=time::now(), context={_sql(context)};")
        statements.append("COMMIT;")
        self._execute("\n".join(statements))
        return {"sources": len(current), "members": len(submitted), "nodes": len(batch.get("nodes", [])),
                "edges": len(batch.get("edges", [])), "invalidated": sorted(affected)}

    def search(self, text: str, *, scope: str = "", limit: int = 10, literal: bool = False) -> list[dict]:
        if literal:
            match = (f"string::contains(string::lowercase(title + '\\n' + text), "
                     f"string::lowercase({_sql(text)}))")
            score = "0.0"
        else:
            match = f"(text @1@ {_sql(text)} OR title @2@ {_sql(text)})"
            score = "search::score(1) + search::score(2)"
        return self._execute(f"SELECT *, source_revision AS revision, {score} AS lexical_score OMIT embedding FROM member "
                             f"WHERE stale=false AND {match} "
                             f"AND string::starts_with(path, {_sql(scope)}) "
                             f"ORDER BY lexical_score DESC LIMIT {int(limit)};")[0]

    def read(self, member_id: str) -> dict:
        if _record(member_id).table != "member":
            raise ValueError("read requires a member ID; inspect node/edge evidence via neighbors")
        member = self._execute(f"SELECT * OMIT embedding FROM ONLY {_sql(_record(member_id))};")[0]
        if member["kind"] == "image":
            snapshot = self.config.memory_dir / member["asset"]
            if sha256(snapshot.read_bytes()).hexdigest() != member["source_revision"]:
                raise ValueError(f"Image snapshot revision mismatch for {member_id}")
            missing = False
            try:
                source = read_image(self.config.root, member["path"])
            except FileNotFoundError:
                missing = True
            else:
                if source.revision != member["source_revision"]:
                    raise ValueError(f"Image source revision mismatch for {member['path']}")
            return {"member": member, "original": {"path": member["path"], "revision": member["source_revision"],
                    "image_path": str(snapshot), "original_missing": missing, "locator": member["locator"]}}
        original = read_member(self.config.root, member["path"], member["source_revision"],
                               member["id"], member["start_line"], member["end_line"])
        return {"member": member, "original": asdict(original)}

    def neighbors(self, record_id: str, *, include_stale: bool = False) -> dict:
        record = _sql(_record(record_id))
        fresh = "" if include_stale else " AND stale=false"
        current, children, edges = self._execute(
            f"SELECT * OMIT embedding FROM ONLY {record}; SELECT * OMIT embedding FROM member WHERE parent={record}{fresh}; "
            f"SELECT * FROM semantic WHERE (in={record} OR out={record}){fresh};")
        parent = self._execute(f"SELECT * OMIT embedding FROM ONLY {_sql(_record(current['parent']))};")[0] if current and current.get("parent") else None
        if parent and parent["stale"] and not include_stale:
            parent = None
        return {"record": current, "parent": parent, "children": children, "edges": edges}

    def brief(self, task: str = "", *, limit: int = 6) -> dict:
        mandatory, stale, sources = self._execute(
            "SELECT * OMIT embedding FROM member WHERE mandatory=true; SELECT id,path,kind FROM member WHERE stale=true; SELECT id,path,revision,deleted FROM source;")
        clues = self.search(task, limit=limit) if task else self._execute(
            f"SELECT * OMIT embedding FROM member WHERE stale=false AND mandatory=false AND kind IN ['file','section'] LIMIT {int(limit)};")[0]
        mandatory_ids = {row["id"] for row in mandatory}
        return {"mandatory": mandatory, "clues": [row for row in clues if row["id"] not in mandatory_ids],
                "pending": stale, "sources": sources,
                "coverage_gaps": [{"id": row["id"], "gaps": row["coverage_gaps"]}
                                  for row in self._rows("member") if row.get("coverage_gaps")]}

    def changes(self, scope: list[str], *, deep: bool = False) -> list[dict]:
        known = self._rows("source")
        changes = detect_changes(self.config.root, [source for source in known if not source.get("deleted")], scope, deep=deep)
        current = {change.path: None if change.kind == "deleted" else self._load_source(change.path)
                   for change in changes if change.kind != "added"}
        affected = self._affected(current, self._rows("member"))
        statements = self._invalidate_sql(affected, "detected_change", {})
        if statements:
            self._execute("BEGIN;\n" + "\n".join(statements) + "\nCOMMIT;")
        return [asdict(change) for change in changes]

    def embed_members(self, ids: list[str] | None = None, *, timeout: float = 600) -> dict:
        from .vectors import embed_members
        return embed_members(self, ids, timeout=timeout)

    def vector_search(self, text: str, *, scope: str = "", limit: int = 12, timeout: float = 600) -> list[dict]:
        from .vectors import vector_search
        return vector_search(self, text, scope=scope, limit=limit, timeout=timeout)

    def hybrid_search(self, text: str, *, scope: str = "", limit: int = 12, timeout: float = 600,
                      literal: bool = False) -> list[dict]:
        from .vectors import hybrid_search
        return hybrid_search(self, text, scope=scope, limit=limit, timeout=timeout, literal=literal)
