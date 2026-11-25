"""Partition a Codex text part without changing its UTF-8 bytes."""

from dataclasses import dataclass
import re


SHORT_PART_BYTES = 4096
SEGMENT_BYTES = 16384
_FENCE = re.compile(r" {0,3}(`{3,}|~{3,})([^\r\n]*)")


@dataclass(frozen=True)
class Segment:
    byte_start: int
    byte_end: int
    kind: str
    text: str


def _regions(text):
    start = position = 0
    fence = None
    for line in text.splitlines(keepends=True):
        next_position = position + len(line)
        match = _FENCE.fullmatch(line.rstrip("\r\n"))
        if fence is not None:
            if (match and match[1][0] == fence[0] and len(match[1]) >= len(fence)
                    and not match[2].strip()):
                yield text[start:next_position], "code"
                start, fence = next_position, None
        elif match:
            if start < position:
                yield text[start:position], "text"
            start, fence = position, match[1]
        elif not line.strip():
            yield text[start:next_position], "text"
            start = next_position
        position = next_position
    if start < position:
        yield text[start:position], "code" if fence is not None else "text"


def _cut(data, start, end, target):
    """Prefer a nearby line break and keep a short whitespace tail with text."""
    limit = min(start + target, end - 1)
    while data[limit] & 0xC0 == 0x80:
        limit -= 1
    cut = data.rfind(b"\n", start + (limit - start) // 2, limit) + 1 or limit
    if end - cut < SEGMENT_BYTES and not data[cut:end].decode("utf-8").strip():
        prefix = data[start:cut].decode("utf-8").rstrip()[:-1]
        adjusted = start + len(prefix.encode("utf-8"))
        if end - adjusted <= SEGMENT_BYTES and prefix.strip():
            return adjusted
    return cut


def split(segment):
    """Bisect a rejected non-singleton segment at an original byte boundary."""
    if len(segment.text) < 2:
        return ()
    data = segment.text.encode("utf-8")
    boundary = _cut(data, 0, len(data), len(data) // 2)
    if boundary == 0:
        boundary = len(segment.text[0].encode("utf-8"))
    middle = segment.byte_start + boundary
    return (Segment(segment.byte_start, middle, segment.kind, data[:boundary].decode("utf-8")),
            Segment(middle, segment.byte_end, segment.kind, data[boundary:].decode("utf-8")))


def segment(text):
    """Keep short messages whole and partition longer prose and fenced code."""
    if not text.strip():
        return []
    data = text.encode("utf-8")
    if len(data) <= SHORT_PART_BYTES:
        kinds = {kind for body, kind in _regions(text) if body.strip()}
        kind = next(iter(kinds)) if len(kinds) == 1 else "mixed"
        return [Segment(0, len(data), kind, text)]

    # Preserve whitespace at its original coordinates in the nearest text region.
    joined = []
    start = end = 0
    for body, kind in _regions(text):
        end += len(body.encode("utf-8"))
        if body.strip():
            joined.append((start, end, kind))
            start = end
    if start < end:
        start, _, kind = joined[-1]
        joined[-1] = (start, end, kind)

    ranges = []
    for start, end, kind in joined:
        while start < end:
            stop = _cut(data, start, end, SEGMENT_BYTES) if end - start > SEGMENT_BYTES else end
            if data[start:stop].decode("utf-8").strip():
                ranges.append((start if ranges else 0, stop, kind))
            elif ranges:
                # Coalesce consecutive blank intervals without copying a growing string.
                preceding, _, preceding_kind = ranges[-1]
                ranges[-1] = (preceding, stop, preceding_kind)
            start = stop
    return [Segment(start, end, kind, data[start:end].decode("utf-8")) for start, end, kind in ranges]
