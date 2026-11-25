"""Run the explicit dialogue workset through ordinary maintenance ownership."""

from .codex_index_config import load_manifest, open_host
from .maintenance import check
from .query import normalize_scope


def index_workset(memory, *, scope, control, timeout):
    from .codex_index import index_thread
    from .codex_index_host import CodexDialogueError

    manifest = load_manifest(memory.config)
    prefixes = tuple(normalize_scope(path).rstrip("/") for path in scope or ("",))
    excluded = set(manifest["excluded_thread_ids"])
    entries = [row for row in manifest["threads"].values() if row["thread_id"] not in excluded
               and any(not prefix or row["path"] == prefix or row["path"].startswith(prefix + "/")
                       for prefix in prefixes)]
    report = {"status": "indexed", "authorized_threads": len(entries), "threads": [],
              "excluded_threads": len(excluded)}
    if not entries:
        return report

    def checkpoint():
        check(control)
        if load_manifest(memory.config) != manifest:
            raise RuntimeError("Codex dialogue authorization changed during maintenance; restart with the current manifest")

    with open_host(memory.config, checkpoint=checkpoint, manifest=manifest) as host:
        for row in entries:
            checkpoint()
            thread_id = row["thread_id"]
            try:
                snapshot = host.capture(thread_id)
            except CodexDialogueError as error:
                report["threads"].append({"thread_id": thread_id, "status": "unavailable",
                                          "capture_gaps": [{"reason": error.reason}]})
                continue
            if snapshot["thread_id"] != thread_id:
                raise ValueError("Codex returned a different authorized thread")
            result = index_thread(memory, snapshot, control=control, timeout=timeout,
                                  private=row["private"], path=row["path"], checkpoint=checkpoint)
            report["threads"].append(result)
    return report


def read_host(config, bookmark, *, context=1):
    with open_host(config) as host:
        return host.read(bookmark, context=context)
