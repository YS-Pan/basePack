"""Read versioned originals and prepare line-addressed material for an agent."""

from bisect import bisect_left
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from difflib import SequenceMatcher
from hashlib import sha256
from itertools import accumulate
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
class LineAnchor:
    """An exact complete-line candidate, with offsets in the original new text."""

    start_line: int
    end_line: int
    start: int
    end: int
    context_match: bool


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


def comparison_text(text: str) -> str:
    """Normalize only CRLF to LF, never the stored original or its byte hash."""
    return text.replace("\r\n", "\n")


def line_changes(before: str, after: str) -> list[tuple[str, int, int, int, int]]:
    """Return difflib opcodes over complete lines with CRLF/LF equivalence.

    All opcode coordinates are 0-based, half-open line indexes. Equal blocks
    provide position evidence, including for repeated lines, not uniqueness.
    """
    old_lines = [comparison_text(line) for line in before.splitlines(keepends=True)]
    new_lines = [comparison_text(line) for line in after.splitlines(keepends=True)]
    return SequenceMatcher(None, old_lines, new_lines, autojunk=False).get_opcodes()


def mapped_line_range(changes: Iterable[tuple[str, int, int, int, int]],
                      start_line: int, end_line: int) -> tuple[int, int] | None:
    """Map a 1-based inclusive old range wholly contained in one equal block."""
    if not 1 <= start_line <= end_line:
        raise ValueError(f"Invalid line range {start_line}:{end_line}")
    for operation, old_start, old_end, new_start, _ in changes:
        if operation == "equal" and old_start <= start_line - 1 and end_line <= old_end:
            offset = new_start - old_start
            return start_line + offset, end_line + offset
    return None


def literal_spans(text: str, quote: str, *, prefix: str = "",
                  suffix: str = "") -> list[tuple[int, int]]:
    """Find all literal quote spans, including overlaps, with adjacent context.

    Coordinates are Python character indexes, 0-based and half-open. Callers
    choose the comparison view; this primitive performs no normalization.
    """
    if not quote:
        raise ValueError("Quote must not be empty")
    pattern = (r"(?=" + re.escape(prefix) + r"(?P<quote>" + re.escape(quote)
               + r")" + re.escape(suffix) + r")")
    return [match.span("quote") for match in re.finditer(pattern, text)]


def locate_lines(before: str, after: str, start_line: int, end_line: int, *,
                 context_chars: int = 64) -> list[LineAnchor]:
    """Locate an old complete-line quote in the new CRLF/LF comparison view.

    Keep every exact candidate whose boundaries are complete original lines;
    full adjacent context is evidence on each candidate, never a filter that
    hides an exact quote after surrounding edits. Returned line numbers are
    1-based inclusive and character offsets address the unmodified ``after``.
    This proves text/position only; callers resolve ambiguity and dependencies.
    """
    old_lines = before.splitlines(keepends=True)
    if not 1 <= start_line <= end_line <= len(old_lines):
        raise ValueError(f"Invalid line range {start_line}:{end_line} "
                         f"({len(old_lines)} lines)")
    if context_chars < 0:
        raise ValueError("context_chars must be nonnegative")
    old_lines = [comparison_text(line) for line in old_lines]
    old_offsets = list(accumulate(map(len, old_lines), initial=0))
    old_view = "".join(old_lines)
    start, end = old_offsets[start_line - 1], old_offsets[end_line]
    quote = old_view[start:end]
    prefix = old_view[max(0, start - context_chars):start]
    suffix = old_view[end:end + context_chars]

    new_lines = after.splitlines(keepends=True)
    raw_offsets = list(accumulate(map(len, new_lines), initial=0))
    normalized_lines = [comparison_text(line) for line in new_lines]
    offsets = list(accumulate(map(len, normalized_lines), initial=0))
    new_view = "".join(normalized_lines)
    contextual = set(literal_spans(new_view, quote, prefix=prefix, suffix=suffix))
    candidates = []
    for start, end in literal_spans(new_view, quote):
        first, last = bisect_left(offsets, start), bisect_left(offsets, end)
        if offsets[first] == start and offsets[last] == end:
            candidates.append(LineAnchor(first + 1, last, raw_offsets[first],
                                         raw_offsets[last], (start, end) in contextual))
    return candidates


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
