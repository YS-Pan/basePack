"""Read versioned originals and prepare line-addressed material for an agent."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from hashlib import sha256
from os import scandir, stat_result
from pathlib import Path
import re
from typing import Literal


@dataclass(frozen=True)
class SourceContent:
    path: str
    revision: str
    size: int
    mtime_ns: int
    text: str


@dataclass(frozen=True)
class ReadingUnit:
    kind: Literal["heading", "paragraph"]
    start_line: int
    end_line: int
    text: str


@dataclass(frozen=True)
class MemberContent:
    member_id: str
    path: str
    revision: str
    start_line: int
    end_line: int
    text: str


@dataclass(frozen=True)
class SourceChange:
    path: str
    kind: Literal["added", "modified", "deleted"]
    revision: str | None = None
    size: int | None = None
    mtime_ns: int | None = None


def _project_path(root: Path, path: str) -> Path:
    relative = Path(path)
    if relative.is_absolute():
        raise ValueError(f"Source path must be project-relative: {path}")
    target = (root / relative).resolve()
    if not target.is_relative_to(root):
        raise ValueError(f"Source path leaves project: {path}")
    return target


def _read_bytes(path: Path) -> tuple[bytes, stat_result]:
    before = path.stat()
    data = path.read_bytes()
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise RuntimeError(f"Source changed while reading: {path}")
    return data, after


def _files(path: Path):
    if path.is_dir():
        with scandir(path) as entries:
            for entry in entries:
                if entry.name in {".basepack", ".git"}:
                    continue
                if entry.is_dir(follow_symlinks=False):
                    yield from _files(Path(entry.path))
                elif entry.is_file():
                    yield Path(entry.path)
    elif path.is_file():
        yield path


def read_source(root: str | Path, path: str) -> SourceContent:
    """Hash original bytes and decode UTF-8 without converting line endings."""
    root = Path(root).resolve()
    target = _project_path(root, path)
    data, stat = _read_bytes(target)
    return SourceContent(target.relative_to(root).as_posix(), sha256(data).hexdigest(),
                         stat.st_size, stat.st_mtime_ns, data.decode("utf-8"))


def numbered_text(source: SourceContent) -> str:
    """Prepare 1-based line labels; these labels are not part of the original."""
    return "".join(f"{number}: {line}" for number, line in
                   enumerate(source.text.splitlines(keepends=True), 1))


def reading_units(source: SourceContent) -> list[ReadingUnit]:
    """Locate Markdown ATX headings and nonblank paragraphs, not semantic blocks."""
    lines = source.text.splitlines(keepends=True)
    units = []
    paragraph = None
    for index, line in enumerate(lines):
        heading = re.match(r" {0,3}#{1,6}(?:[ \t]+|$)", line.rstrip("\r\n"))
        if heading or not line.strip():
            if paragraph is not None:
                units.append(ReadingUnit("paragraph", paragraph + 1, index,
                                         "".join(lines[paragraph:index])))
                paragraph = None
            if heading:
                units.append(ReadingUnit("heading", index + 1, index + 1, line))
        elif paragraph is None:
            paragraph = index
    if paragraph is not None:
        units.append(ReadingUnit("paragraph", paragraph + 1, len(lines),
                                 "".join(lines[paragraph:])))
    return units


def read_member(root: str | Path, path: str, revision: str, member_id: str,
                start_line: int, end_line: int) -> MemberContent:
    """Read the inclusive range chosen by an agent, preserving its stable ID."""
    source = read_source(root, path)
    if source.revision != revision:
        raise ValueError(f"Source revision mismatch for {source.path}: "
                         f"expected {revision}, found {source.revision}")
    lines = source.text.splitlines(keepends=True)
    if not 1 <= start_line <= end_line <= len(lines):
        raise ValueError(f"Invalid line range {start_line}:{end_line} for "
                         f"{source.path} ({len(lines)} lines)")
    return MemberContent(member_id, source.path, source.revision, start_line, end_line,
                         "".join(lines[start_line - 1:end_line]))


def detect_changes(root: str | Path, sources: Iterable[Mapping], scope: Iterable[str],
                   *, deep: bool = False) -> list[SourceChange]:
    """Inspect explicit files/directories; fast mode reads only directory metadata.

    Stored sources have path/revision/size/mtime_ns keys. A modified result means
    metadata or content changed; deep mode supplies its actual revision so a
    metadata-only change can reuse knowledge. No original or database is written.
    """
    root = Path(root).resolve()
    scopes = [_project_path(root, path) for path in scope]
    known = {}
    for source in sources:
        path = _project_path(root, source["path"])
        if any(path == selected or path.is_relative_to(selected) for selected in scopes):
            known[path.relative_to(root).as_posix()] = source
    current = {}
    for selected in scopes:
        for candidate in _files(selected):
            path = _project_path(root, candidate.relative_to(root).as_posix())
            current[path.relative_to(root).as_posix()] = path
    # Directory discovery skips managed trees; an already registered file there
    # is still an explicit source and must not be mistaken for a deletion.
    for relative in known:
        target = _project_path(root, relative)
        if relative not in current and target.is_file():
            current[relative] = target
    changes = []
    for relative in sorted(known.keys() | current.keys()):
        if relative not in current:
            changes.append(SourceChange(relative, "deleted"))
            continue
        path = current[relative]
        revision = None
        if deep:
            data, stat = _read_bytes(path)
            revision = sha256(data).hexdigest()
        else:
            stat = path.stat()
        previous = known.get(relative)
        if previous is None:
            kind = "added"
        elif (stat.st_size, stat.st_mtime_ns) != (previous["size"], previous["mtime_ns"]) or (
                deep and revision != previous["revision"]):
            kind = "modified"
        else:
            continue
        changes.append(SourceChange(relative, kind, revision, stat.st_size, stat.st_mtime_ns))
    return changes
