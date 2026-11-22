"""Convert a schema 3 native export in isolated Windows SurrealKV stores."""

import argparse
from contextlib import contextmanager
from hashlib import file_digest, sha256
import json
import os
from pathlib import Path
import re
from secrets import token_hex
from shutil import copyfile
import subprocess
import sys
from tempfile import TemporaryDirectory
from uuid import UUID

from ..project.config import DYNAMIC_MEMORY_ENDPOINT, MachineConfig, ProjectConfig
from ..runtime.backup import _claim_restore_target, _native_export, _native_import
from ..runtime.launcher import _wait_owned_ready
from ..runtime.surreal_process import launch_surreal
from .store import Memory


def _file_sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def _json_bytes(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


@contextmanager
def _local_requests():
    previous = {name: os.environ.get(name) for name in ("NO_PROXY", "no_proxy")}
    try:
        for name in previous:
            os.environ[name] = "127.0.0.1"
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


@contextmanager
def _store(executable, path, *, project_id, namespace, database):
    path.mkdir()
    user, password = "migration", token_hex(24)
    key = path / "password.txt"
    key.write_text(password, encoding="utf-8")
    environment = {name: value for name, value in os.environ.items() if not name.upper().startswith("SURREAL_")}
    environment.update(SURREAL_USER=user, SURREAL_PASS=password, SURREAL_NO_DEFAULTS="true")
    args = [str(executable), "start", "--bind", "127.0.0.1:0",
            "surrealkv://" + (path / "store").as_posix()]
    log_path = path / "start.log"
    with log_path.open("w", encoding="utf-8") as log:
        process = launch_surreal(args, env=environment, log=log)
        try:
            try:
                endpoint = _wait_owned_ready(DYNAMIC_MEMORY_ENDPOINT, process)
            except (RuntimeError, TimeoutError) as error:
                error.add_note(log_path.read_text(encoding="utf-8", errors="replace")[-4096:])
                raise
            config = ProjectConfig(path / "project.toml", Path(sys.executable), path,
                                   {"memory": {"data_dir": ".basepack/memory", "search_mode": "vector",
                                               "project_id": project_id, "endpoint": endpoint, "username": user,
                                               "password_file": str(key), "namespace": namespace, "database": database}},
                                   MachineConfig(path / "machine.toml", {}))
            yield Memory(config)
        finally:
            if process.poll() is None:
                process.terminate()
            process.wait(timeout=10)


def _restore(memory, path):
    _claim_restore_target(memory)
    _native_import(memory.connection["endpoint"], memory, path)


def _fingerprint(memory):
    memory.verify_project()
    info = memory._execute("INFO FOR DB;", check_project=False)[0]
    evidence = {}
    for name in sorted(info["tables"]):
        table = "`" + name.replace("\\", "\\\\").replace("`", "\\`") + "`"
        definition = memory._execute(f"INFO FOR TABLE {table};", check_project=False)[0]
        # Native import resets which fields SurrealDB has verified against
        # all stored rows. The schema, migration history and rows still match.
        if "migrations" in definition:
            definition["migrations"].pop("guaranteed", None)
        count, digest = 0, sha256()
        while True:
            rows = memory._execute(
                f"SELECT * FROM {table} ORDER BY id LIMIT 64 START {count};", check_project=False)[0]
            for row in rows:
                digest.update(_json_bytes(row) + b"\n")
            count += len(rows)
            if len(rows) < 64:
                break
        evidence[name] = {"count": count, "sha256": digest.hexdigest(),
                          "schema_sha256": sha256(_json_bytes(definition)).hexdigest()}
    return {"schema_sha256": sha256(_json_bytes(info)).hexdigest(), "tables": evidence}


def _verify_restore(expected, restored):
    changes = [table for table in sorted(expected["tables"].keys() | restored["tables"].keys())
               if expected["tables"].get(table) != restored["tables"].get(table)]
    if expected["schema_sha256"] != restored["schema_sha256"]:
        changes.insert(0, "database schema")
    if changes:
        raise ValueError("Independent schema 4 restore differs in " + ", ".join(changes))


def _copy_assets(memory, assets, behavior_assets, expected, bundle):
    references = {}
    for row in memory._execute("SELECT asset, revision FROM source_version WHERE kind='image';")[0]:
        asset, revision = row["asset"], row["revision"]
        if references.setdefault(asset, revision) != revision:
            raise ValueError(f"Image asset has inconsistent snapshot revisions: {asset}")
    for artifact in memory._execute("SELECT VALUE artifact FROM behavior_model;")[0]:
        references[f"behavior/{artifact}.json"] = artifact
    if set(references) != set(expected):
        raise ValueError("Asset references differ from the migration report")
    sources = {"assets": assets, "behavior": behavior_assets}
    for asset, revision in sorted(references.items()):
        relative = Path(asset)
        if (len(relative.parts) != 2 or relative.parts[0] not in sources
                or relative.name in ("", ".", "..")):
            raise ValueError(f"Invalid snapshot asset path: {asset}")
        directory = sources[relative.parts[0]]
        if directory is None:
            raise ValueError(f"Missing schema 3 {relative.parts[0]} directory")
        source = (directory / relative.name).resolve(strict=True)
        if not source.is_relative_to(directory):
            raise ValueError(f"Asset is outside the supplied directory: {asset}")
        output = bundle / relative
        output.parent.mkdir(exist_ok=True)
        copyfile(source, output)
        if _file_sha256(output) != revision:
            raise ValueError(f"Asset checksum differs from its snapshot: {asset}")


def migrate(*, surreal, source_export, source_sha256, project_id, namespace, database,
            output, assets=None, behavior_assets=None, relations=None):
    """Stage a conversion and publish its bundle after independent native restore."""
    from .graph_upgrade import upgrade

    UUID(project_id)
    source_sha256 = source_sha256.lower()
    if not re.fullmatch(r"[0-9a-f]{64}", source_sha256):
        raise ValueError("Source SHA-256 must contain 64 hexadecimal digits")
    source_export = source_export.resolve(strict=True)
    if assets is not None:
        assets = assets.resolve(strict=True)
        if not assets.is_dir():
            raise ValueError("Expected a schema 3 assets directory")
    if behavior_assets is not None:
        behavior_assets = behavior_assets.resolve(strict=True)
        if not behavior_assets.is_dir():
            raise ValueError("Expected a schema 3 behavior artifacts directory")
    if not output.name or output.name in (".", ".."):
        raise ValueError("Specify a new output directory")
    output = output.parent.resolve(strict=True) / output.name
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"Migration output already exists: {output}")
    surreal = surreal.resolve(strict=True)
    version = subprocess.check_output([str(surreal), "version"], text=True,
                                      creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).strip()
    if not version.startswith("4."):
        raise ValueError(f"Expected SurrealDB 4, found {version}")
    decisions_data = relations.read_bytes() if relations is not None else None
    decisions = json.loads(decisions_data) if decisions_data is not None else []
    target = {"project_id": project_id, "namespace": namespace, "database": database}
    with _local_requests(), TemporaryDirectory(prefix=".graph-migration-", dir=output.parent) as staging:
        stage = Path(staging)
        bundle = stage / "bundle"
        bundle.mkdir()
        migrated = bundle / "schema4.surql"
        with TemporaryDirectory(dir=stage) as databases:
            work = Path(databases)
            fixed_source = work / "schema3.surql"
            copyfile(source_export, fixed_source)
            if _file_sha256(fixed_source) != source_sha256:
                raise ValueError("Schema 3 export does not match the expected SHA-256")
            with _store(surreal, work / "convert", **target) as memory:
                _restore(memory, fixed_source)
                report = upgrade(memory, source_sha256=source_sha256, assets=assets,
                                 behavior_assets=behavior_assets, relations=decisions)
                expected = _fingerprint(memory)
                _copy_assets(memory, assets, behavior_assets, report["assets"], bundle)
                _native_export(str(surreal), memory.connection["endpoint"], memory, migrated)
            with _store(surreal, work / "restore", **target) as memory:
                _restore(memory, migrated)
                restored = _fingerprint(memory)
                _verify_restore(expected, restored)
        if _file_sha256(source_export) != source_sha256:
            raise ValueError("Schema 3 export changed during conversion")
        report.update(surreal_version=version, schema4_sha256=_file_sha256(migrated),
                      native_restore=restored)
        if decisions_data is not None:
            report["relations_sha256"] = sha256(decisions_data).hexdigest()
        (bundle / "migration.json").write_text(
            json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"Migration output already exists: {output}")
        bundle.rename(output)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--surreal", required=True, type=Path)
    parser.add_argument("--source-export", required=True, type=Path)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--namespace", required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--assets", type=Path)
    parser.add_argument("--behavior-assets", type=Path)
    parser.add_argument("--relations", type=Path)
    args = parser.parse_args()
    migrate(**vars(args))
    print(args.output.resolve())


if __name__ == "__main__":
    main()
