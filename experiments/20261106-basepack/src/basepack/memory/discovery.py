"""Discover project source candidates without scanning ignored Git trees."""

import os
from pathlib import Path
import subprocess

from .content import _project_path, read_source
from .images import IMAGE_SUFFIXES


# These are generated or local state, even when an enclosing scope is selected.
_EXCLUDED = {".git", ".basepack", "__pycache__", ".cache", ".pytest_cache",
             ".mypy_cache", ".ruff_cache", ".venv", "venv", "node_modules"}


def _allowed(path: Path) -> bool:
    return (not any(part in _EXCLUDED for part in path.parts)
            and path.suffix.lower() not in {".pyc", ".pyo"})


def _selected_files(root: Path, scopes):
    for scope in scopes:
        target = _project_path(root, scope)
        relative = target.relative_to(root)
        if not _allowed(relative):
            continue
        if target.is_dir():
            for directory, names, files in os.walk(target, followlinks=False):
                names[:] = [name for name in names if name not in _EXCLUDED]
                for name in files:
                    path = Path(directory) / name
                    if path.is_file():
                        # Resolve links using the same containment contract as source reads.
                        yield _project_path(root, path.relative_to(root).as_posix())
        elif target.is_file():
            yield target


def _git_repository(root: Path) -> bool:
    return any((directory / ".git").exists() for directory in (root, *root.parents))


def _git_files(root: Path, directory: Path, *, git_dir=None):
    command = ["git"]
    if git_dir is not None:
        command.extend(["--git-dir", str(git_dir), "--work-tree", str(directory)])
    output = subprocess.run([*command, "ls-files", "--cached", "--others",
                             "--exclude-standard", "-z", "--", "."],
                            cwd=directory, check=True, stdout=subprocess.PIPE).stdout
    for entry in output.split(b"\0"):
        if entry:
            relative = directory.relative_to(root) / os.fsdecode(entry)
            if _allowed(relative):
                target = _project_path(root, relative.as_posix())
                if target.is_file():
                    yield target


def discover_sources(config, scope=None) -> dict:
    """Return readable files and explicit gaps for this maintenance discovery.

    A Git project's default inventory includes tracked and untracked nonignored
    files, plus the root private/ repository's own inventory when present.
    Configured scopes can add local originals; an explicit scope replaces both
    inventories and configured scopes. Registered history is maintained separately
    by the caller.
    """
    root = Path(config.root).resolve()
    candidates = set()
    if scope is not None:
        mode = "explicit"
        scopes = scope
    elif _git_repository(root):
        mode = "git"
        candidates.update(_git_files(root, root))
        scopes = config.raw["memory"]["source_scope"]
    else:
        mode = "configured"
        scopes = config.raw["memory"]["source_scope"]
    if scope is None:
        private = _project_path(root, "private")
        if private.exists():
            candidates.update(_git_files(root, private, git_dir=private / ".git"))
    candidates.update(_selected_files(root, scopes))

    paths, gaps = [], []
    for target in sorted(candidates):
        relative = target.relative_to(root).as_posix()
        if not _allowed(Path(relative)):
            continue
        if target.suffix.lower() not in IMAGE_SUFFIXES:
            try:
                source = read_source(root, relative)
            except UnicodeDecodeError as error:
                gaps.append({"path": relative, "reason": "non_utf8", "error": str(error)})
                continue
            if "\0" in source.text:
                gaps.append({"path": relative, "reason": "binary"})
                continue
        paths.append(relative)
    return {"paths": paths, "gaps": gaps, "mode": mode}


def retained_codex_paths(config, project_id) -> dict:
    """Recover owned captures and their local image snapshots for maintenance."""
    import json

    if not project_id:
        return {"paths": [], "gaps": []}
    root = Path(config.root).resolve()
    memory_dir = Path(config.memory_dir).resolve()
    capture_dir = memory_dir / "codex"
    attachment_dir = (memory_dir / "codex-attachments").resolve()
    paths, gaps = set(), []
    for capture in sorted(capture_dir.glob("*.txt")):
        resolved = capture.resolve()
        if not resolved.is_relative_to(capture_dir.resolve()):
            raise ValueError(f"Codex capture leaves capture directory: {capture}")
        with capture.open("rb") as stream:
            first = stream.readline()
            if not first:
                continue
            header = json.loads(first)
            if header["project_id"] != project_id:
                continue
            thread_id = header["thread_id"]
            paths.add(resolved.relative_to(root).as_posix())
            while True:
                if header["project_id"] != project_id or header["thread_id"] != thread_id:
                    raise ValueError(f"Inconsistent Codex capture ownership: {capture}")
                length = header["byte_length"]
                if not isinstance(length, int) or isinstance(length, bool) or length < 0:
                    raise ValueError(f"Invalid Codex capture body length: {capture}")
                stream.seek(length, os.SEEK_CUR)
                if stream.read(1) != b"\n":
                    raise ValueError(f"Truncated Codex capture body: {capture}")
                if "managed_attachment" in header:
                    name = Path(header["managed_attachment"])
                    attachment = (memory_dir / name).resolve()
                    if name.is_absolute() or not attachment.is_relative_to(attachment_dir):
                        raise ValueError(f"Codex attachment leaves attachment directory: {name}")
                    relative = attachment.relative_to(root).as_posix()
                    if attachment.is_file():
                        paths.add(relative)
                    else:
                        gaps.append({"path": relative, "reason": "missing_attachment"})
                line = stream.readline()
                if not line:
                    break
                header = json.loads(line)
    return {"paths": sorted(paths), "gaps": gaps}
