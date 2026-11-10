from pathlib import Path
import shutil
import subprocess

from basepack.memory.codex_binding import classify_threads, discover_binding


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def make_repo(tmp_path):
    main = tmp_path / "main 中文"
    main.mkdir()
    git(main, "init", "-q")
    (main / "tracked.txt").write_text("first\n", encoding="utf-8")
    git(main, "add", "tracked.txt")
    git(main, "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "initial")
    worktree = tmp_path / "another worktree"
    git(main, "worktree", "add", "-qb", "branch", str(worktree))
    return main, worktree


def test_real_worktrees_match_nested_cwds_and_unknowns_are_reported(tmp_path):
    main, tree = make_repo(tmp_path)
    (main / "src").mkdir()
    (tree / "src").mkdir()
    other = tmp_path / "other"
    other.mkdir()
    binding = discover_binding(main, "project-a", [other])
    threads = [
        {"id": "main", "projectId": None, "cwd": str(main / "src")},
        {"id": "branch", "projectId": None, "cwd": str(tree / "src"), "forkedFromId": "main"},
        {"id": "explicit", "projectId": "project-a", "cwd": None},
        {"id": "other-id", "projectId": "project-b", "cwd": str(main)},
        {"id": "conflict", "projectId": "project-a", "cwd": str(other)},
        {"id": "missing", "projectId": None, "cwd": str(tmp_path / "deleted")},
        {"id": "outside", "projectId": None, "cwd": str(tmp_path)},
    ]
    result = classify_threads(binding, threads)
    assert {thread["id"] for thread in result["matched"]} == {"main", "branch", "explicit"}
    assert {item["thread"]["id"]: item["reason"] for item in result["excluded"]} == {
        "other-id": "different_project_id", "outside": "outside_project_roots"}
    assert {item["thread"]["id"]: item["reason"] for item in result["unresolved"]} == {
        "conflict": "registered_project_conflict", "missing": "cwd_unavailable"}
    assert binding["common_dir"]
    assert not result["gaps"]


def test_nested_project_does_not_claim_unrelated_paths_in_the_same_repo(tmp_path):
    main, tree = make_repo(tmp_path)
    (main / "project").mkdir()
    (tree / "project").mkdir()
    result = classify_threads(discover_binding(main / "project", "project-a"), [
        {"id": "project", "cwd": str(tree / "project")},
        {"id": "sibling", "cwd": str(tree)},
    ])
    assert [item["id"] for item in result["matched"]] == ["project"]
    assert result["excluded"][0]["thread"]["id"] == "sibling"


def test_removed_worktree_does_not_guess_ownership(tmp_path):
    main, tree = make_repo(tmp_path)
    shutil.rmtree(tree)
    binding = discover_binding(main, "project-a")
    assert binding["gaps"] == [{"path": str(tree), "reason": "worktree_unavailable"}]
    result = classify_threads(binding, [{"id": "old", "cwd": str(tree)}])
    assert result["unresolved"][0]["reason"] == "cwd_unavailable"


def test_non_git_project_and_unbound_explicit_id(tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    root = tmp_path / "project"
    root.mkdir()
    binding = discover_binding(root, None)
    assert binding["common_dir"] is None
    result = classify_threads(binding, [{"id": "local", "cwd": str(root)},
                                         {"id": "unknown-id", "projectId": "remote", "cwd": str(root)}])
    assert [item["id"] for item in result["matched"]] == ["local"]
    assert result["unresolved"][0]["reason"] == "project_id_unbound"


def test_most_specific_registered_project_root_wins(tmp_path):
    parent = tmp_path / "parent"
    project = parent / "project"
    child = project / "other-project"
    own_cwd = project / "src"
    child_cwd = child / "src"
    own_cwd.mkdir(parents=True)
    child_cwd.mkdir(parents=True)
    threads = [{"id": "own", "cwd": str(own_cwd)},
               {"id": "child", "cwd": str(child_cwd)},
               {"id": "child-explicit", "projectId": "target", "cwd": str(child_cwd)}]
    binding = discover_binding(project, "target", [parent, child])
    result = classify_threads(binding, threads)
    assert [thread["id"] for thread in result["matched"]] == ["own"]
    assert {item["thread"]["id"] for item in result["unresolved"]} == {"child", "child-explicit"}
    same_path = discover_binding(project, "target", [project])
    assert classify_threads(same_path, [threads[0]])["unresolved"][0]["reason"] == "registered_project_conflict"


def test_other_registered_project_is_excluded_only_when_unambiguous(tmp_path):
    own = tmp_path / "own"
    other = tmp_path / "other"
    own.mkdir()
    other.mkdir()
    result = classify_threads(discover_binding(own, "target", [other]), [
        {"id": "other", "cwd": str(other)},
        {"id": "conflicting-id", "projectId": "target", "cwd": str(other)},
        {"id": "unavailable", "cwd": str(other / "removed")},
    ])
    assert [(item["thread"]["id"], item["reason"]) for item in result["excluded"]] == [("other", "other_project")]
    assert {item["thread"]["id"]: item["reason"] for item in result["unresolved"]} == {
        "conflicting-id": "registered_project_conflict", "unavailable": "cwd_unavailable"}
