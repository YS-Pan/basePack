"""Validate fixed author proposals against their wave task's write scope."""

import json


def validate_draft(task, material):
    from .waves import _path_key

    draft = json.loads(material.decode("utf-8"))
    allowed = {_path_key(path) for path in task["paths"]}
    paths = [source if isinstance(source, str) else source["path"] for source in draft["sources"]]
    paths.extend(member["path"] for member in draft.get("members", []))
    for path in paths:
        if _path_key(path) not in allowed:
            raise ValueError(f"Task {task['id']} cannot write source outside its paths: {path}")
