"""Bind Codex thread metadata to a project without inspecting chat contents."""

from pathlib import Path
import subprocess


def _git(root, *args, allow_not_repo=False):
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True)
    if result.returncode:
        if allow_not_repo and b"not a git repository" in result.stderr.lower():
            return None
        raise subprocess.CalledProcessError(result.returncode, result.args, result.stdout, result.stderr)
    return result.stdout.decode("utf-8").strip()


def discover_binding(root, project_id, other_roots=()):
    """Resolve the project's physical root and any registered Git worktrees.

    other_roots must contain the host's other registered project roots. Missing
    worktrees are reported instead of being used as evidence of ownership.
    """
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise NotADirectoryError(root)
    other_roots = [str(Path(path).resolve()) for path in other_roots]
    top = _git(root, "rev-parse", "--path-format=absolute", "--show-toplevel", allow_not_repo=True)
    worktrees, gaps, common = [str(root)], [], None
    if top is not None:
        top = Path(top).resolve(strict=True)
        relative = root.relative_to(top)
        common = Path(_git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")).resolve(strict=True)
        entries = _git(root, "worktree", "list", "--porcelain", "-z").split("\0")
        worktrees = []
        for entry in entries:
            if not entry.startswith("worktree "):
                continue
            tree = Path(entry.removeprefix("worktree "))
            project = tree / relative
            if not project.is_dir():
                gaps.append({"path": str(project), "reason": "worktree_unavailable"})
                continue
            tree_common = Path(_git(tree, "rev-parse", "--path-format=absolute", "--git-common-dir")).resolve(strict=True)
            if tree_common != common:
                gaps.append({"path": str(project), "reason": "worktree_common_dir_mismatch"})
                continue
            worktrees.append(str(project.resolve(strict=True)))
    return {"root": str(root), "project_id": project_id, "common_dir": str(common) if common else None,
            "worktrees": worktrees, "other_roots": other_roots, "gaps": gaps}


def classify_threads(binding, threads):
    """Classify raw thread/list records; preserve unknown ownership as unresolved."""
    roots = [Path(path) for path in binding["worktrees"]]
    other_roots = [Path(path) for path in binding["other_roots"]]
    matched, excluded, unresolved = [], [], []
    for thread in threads:
        project_id = thread.get("projectId")
        if project_id and binding["project_id"] and project_id != binding["project_id"]:
            excluded.append({"thread": thread, "reason": "different_project_id"})
            continue
        if project_id and not binding["project_id"]:
            unresolved.append({"thread": thread, "reason": "project_id_unbound"})
            continue
        cwd = thread.get("cwd")
        path = Path(cwd) if cwd else None
        if path and path.is_absolute() and path.is_dir():
            path = path.resolve(strict=True)
            own_depth = max((len(root.parts) for root in roots if path.is_relative_to(root)), default=0)
            other_depth = max((len(root.parts) for root in other_roots if path.is_relative_to(root)), default=0)
            if other_depth and other_depth >= own_depth:
                if not own_depth and not project_id:
                    excluded.append({"thread": thread, "reason": "other_project"})
                else:
                    unresolved.append({"thread": thread, "reason": "registered_project_conflict"})
                continue
        else:
            path = None
        if project_id:
            matched.append(thread)
        elif path is None:
            unresolved.append({"thread": thread, "reason": "cwd_unavailable"})
        elif any(path.is_relative_to(root) for root in roots):
            matched.append(thread)
        else:
            excluded.append({"thread": thread, "reason": "outside_project_roots"})
    return {"matched": matched, "excluded": excluded, "unresolved": unresolved, "gaps": binding["gaps"]}
