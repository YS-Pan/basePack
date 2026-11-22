from hashlib import sha256

import pytest

from basepack.memory.inventory_groups import group_sources


def source(path, content=b"shared\n", *, kind="text", private=False, status="available",
           registered=False, threads=()):
    return {"path": path, "kind": kind, "private": private, "status": status,
            "registered": registered, "revision": sha256(content).hexdigest() if content is not None else None,
            "size": len(content) if content is not None else None,
            "line_count": len(content.splitlines()) if kind == "text" and content is not None else None,
            "codex_threads": list(threads)}


def member(row, role):
    return {"path": row["path"], "revision": row["revision"], "role": role}


def group_map(*members, shared=()):
    return {"schema_version": 1, "groups": [{"id": "source-set", "members": list(members),
                                             "shared_ranges": list(shared)}]}


def test_content_groups_keep_all_paths_and_do_not_modify_source_status():
    prefix = source("A.md", registered=True)
    rows = [source("b.md"), source("a.md"), source("private/b.md", private=True),
            source("image.md", kind="image"), source("other.txt"), prefix]
    result = group_sources(None, rows)
    assert result == group_sources(None, list(reversed(rows)))
    assert result["grouping_gaps"] == []
    assert sorted(path for group in result["groups"] for path in group["paths"]) == sorted(
        row["path"] for row in rows)
    duplicates, = [group for group in result["groups"] if group["kind"] == "content"]
    assert duplicates["paths"] == ["A.md", "a.md", "b.md"]
    assert duplicates["representatives"] == ["A.md"]
    assert duplicates["aliases"] == [{"path": path, "representative": "A.md",
                                       "proof": "same_bytes", "ranges": []}
                                      for path in ["a.md", "b.md"]]
    assert prefix["registered"] is True and rows[0]["registered"] is False


def test_mapping_requires_exact_case_revision_and_matching_role_for_byte_aliases():
    original = source("Report.md")
    copy = source("Copy.md")
    child = source("Child.md")
    lowercase = source("report.md", b"different\n")
    mapping = group_map(member(original, "original"), member(copy, "reading copy"),
                        member(child, "reading copy"))
    result = group_sources(None, [original, copy, child, lowercase], mapping)
    mapped, = [group for group in result["groups"] if group["kind"] == "mapped"]
    assert mapped["paths"] == ["Child.md", "Copy.md", "Report.md"]
    assert mapped["representatives"] == ["Child.md", "Report.md"]
    assert mapped["aliases"] == [{"path": "Copy.md", "representative": "Child.md",
                                  "proof": "same_bytes", "ranges": []}]
    assert [group["paths"] for group in result["groups"] if group["kind"] == "single"] == [["report.md"]]

    inventory_without_matching_case = group_sources(None, [lowercase, copy, child], mapping)
    assert inventory_without_matching_case["grouping_gaps"] == [
        {"group": "source-set", "path": "Report.md", "reason": "unobserved_revision",
         "expected_revision": original["revision"]}]


def test_shared_ranges_check_both_versions_but_keep_uncovered_paths_as_representatives():
    original = source("messages.jsonl", b"header\nmessage\nunique\n")
    transcript = source("transcript.md", b"title\nwrapper\nmessage\n")
    ranges = [{"start_line": 3, "end_line": 3,
               "representative_start_line": 2, "representative_end_line": 2}]
    proof = {"path": "transcript.md", "representative": "messages.jsonl", "ranges": ranges,
             "evidence": "migration log identifying the reviewed message"}
    mapping = group_map(member(original, "message export"), member(transcript, "transcript"),
                        shared=[proof])
    result = group_sources(None, [transcript, original], mapping)
    group, = result["groups"]
    assert group["representatives"] == ["messages.jsonl", "transcript.md"]
    assert group["aliases"] == [{**proof, "proof": "reviewed_ranges"}]
    assert group["aliases"][0]["ranges"] == ranges

    updated = source("transcript.md", b"new title\nwrapper\nmessage\n")
    exact_elsewhere = source("other.md", b"new title\nwrapper\nmessage\n")
    result = group_sources(None, [updated, original, exact_elsewhere], mapping)
    assert result["grouping_gaps"] == [
        {"group": "source-set", "path": "transcript.md", "reason": "revision_changed",
         "expected_revision": transcript["revision"], "observed_revision": updated["revision"]}]
    assert all(not group["aliases"] for group in result["groups"])
    assert {tuple(group["paths"]) for group in result["groups"]} == {
        ("messages.jsonl",), ("other.md",), ("transcript.md",)}


def test_map_separates_privacy_and_rejects_unproven_range_bounds():
    public = source("paper.md")
    restricted = source("private/paper.md", private=True)
    another = source("private/alternate.md", private=True)
    cross_privacy = {"path": "paper.md", "representative": "private/paper.md",
                     "ranges": [{"start_line": 1, "end_line": 1,
                                 "representative_start_line": 1, "representative_end_line": 1}],
                     "evidence": "reviewed cross-scope proof"}
    invalid_bounds = {"path": "private/alternate.md", "representative": "private/paper.md",
                      "ranges": [{"start_line": 1, "end_line": 2,
                                  "representative_start_line": 1, "representative_end_line": 1}],
                      "evidence": "bounds are larger than the observed version"}
    mapping = group_map(member(public, "paper"), member(restricted, "paper"), member(another, "alternate"),
                        shared=[cross_privacy, invalid_bounds])
    result = group_sources(None, [public, restricted, another], mapping)
    assert [(group["private"], group["paths"], group["aliases"]) for group in result["groups"]] == [
        (True, ["private/alternate.md", "private/paper.md"], []), (False, ["paper.md"], [])]
    assert [gap["reason"] for gap in result["grouping_gaps"]] == [
        "different_privacy", "range_outside_source"]


def test_pinned_original_keeps_group_membership_without_claiming_it_is_readable():
    paper = source("paper.pdf", b"pdf bytes", kind=None, status="unsupported")
    reading = source("paper.tex")
    mapping = group_map(member(paper, "original"), member(reading, "transcription"))
    group, = group_sources(None, [paper, reading], mapping)["groups"]
    assert group["paths"] == ["paper.pdf", "paper.tex"]
    assert group["representatives"] == ["paper.tex"]
    assert group["aliases"] == []


def test_custody_groups_one_thread_without_combining_parents_or_shared_attachments():
    rows = [source("chat.txt", threads=["chat"]), source("other.txt", threads=["other"]),
            source("attachment.png", kind="image", threads=["chat"]),
            source("shared.png", kind="image", threads=["chat", "other"]),
            source("private/chat.txt", private=True, threads=["chat"])]
    result = group_sources(None, rows)
    by_id = {group["id"]: group for group in result["groups"] if group["kind"] == "chat"}
    assert by_id["codex:public:chat"]["paths"] == ["attachment.png", "chat.txt"]
    assert by_id["codex:public:chat"]["members"] == [{"path": "attachment.png", "role": "codex_attachment"},
                                                     {"path": "chat.txt", "role": "codex_capture"}]
    assert by_id["codex:public:other"]["paths"] == ["other.txt"]
    assert by_id["codex:private:chat"]["paths"] == ["private/chat.txt"]
    assert [group["paths"] for group in result["groups"] if group["kind"] == "single"] == [["shared.png"]]


def test_invalid_group_map_is_explicit():
    row = source("notes.md")
    with pytest.raises(ValueError, match="more than once"):
        group_sources(None, [row], group_map(member(row, "notes"), member(row, "notes")))
    with pytest.raises(ValueError, match="canonical project-relative"):
        group_sources(None, [row], group_map(member({**row, "path": "../notes.md"}, "notes")))
