"""Input boundaries shared by request rendering and memory commands."""

import json
from pathlib import Path
from pathlib import PurePosixPath, PureWindowsPath


def normalize_scope(value: str) -> str:
    """Keep a literal project-relative prefix; an empty prefix means all paths."""
    if not isinstance(value, str):
        raise ValueError("scope must be a project-relative path prefix string")
    scope = value.replace("\\", "/")
    if (PureWindowsPath(scope).drive or PurePosixPath(scope).is_absolute()
            or ".." in PurePosixPath(scope).parts):
        raise ValueError(f"scope must be a project-relative path prefix: {value}")
    return scope


def load_json_file(path):
    source = Path(path)
    if source.is_dir():
        raise ValueError(f"Expected a UTF-8 JSON file, got a directory: {path}")
    return json.loads(source.read_text(encoding="utf-8"))
