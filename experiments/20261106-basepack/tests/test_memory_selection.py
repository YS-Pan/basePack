import pytest

from basepack.memory.selection import select_scored


def candidate(identity, text, score, start=1, end=3, kind="chunk"):
    return {"id": identity, "text": text, "score": score, "kind": kind,
            "path": "材料.md", "revision": "v1", "start_line": start, "end_line": end}


def test_scores_deliver_actual_content_and_keep_complementary_evidence():
    items = [candidate("leaf", "必要证据", 90),
             candidate("duplicate", "必要证据", 60),
             candidate("inside", "子范围", 80, 2, 2),
             candidate("other", "互补证据", 85, 8, 9),
             candidate("summary", "全章背景", 70, kind="section")]
    result = select_scored(items, 12)
    assert [item["id"] for item in result["items"]] == ["leaf", "other", "summary"]
    assert result["text_characters"] == 12
    assert {row["id"]: row["reason"] for row in result["omitted"]} == {
        "inside": "covered_original", "duplicate": "covered_original"}


def test_budget_keeps_read_pointer_without_silently_truncating_evidence():
    items = [candidate("large", "长证据不能截掉其后面的例外", 95),
             candidate("small", "例外", 80, 5, 5)]
    result = select_scored(items, 4)
    assert result["items"] == [items[1]]
    assert result["omitted"][0]["id"] == "large"
    assert result["omitted"][0]["path"] == "材料.md"
    assert result["omitted"][0]["reason"] == "budget"
    assert "text" not in result["omitted"][0]


def test_identical_words_in_different_sources_keep_both_contexts():
    first = candidate("material-a", "可以执行", 90)
    second = candidate("material-b", "可以执行", 85)
    second["path"] = "另一条件.md"
    assert select_scored([first, second], 20)["items"] == [first, second]


@pytest.mark.parametrize("version_field", ["revision", "source_version"])
def test_same_member_keeps_distinct_evidence_versions(version_field):
    first = candidate("stable-member", "已核原文", 90)
    first["source_version"] = "source_version:first"
    second = {**first, "score": 85, version_field: "another-version"}
    assert select_scored([first, second], 100)["items"] == [first, second]


def test_same_member_keeps_complementary_ranges_from_one_snapshot():
    first = candidate("stable-member", "第一处依据", 90)
    second = candidate("stable-member", "第二处依据", 85, start=8, end=9)
    first["source_version"] = second["source_version"] = "source_version:first"
    assert select_scored([first, second], 100)["items"] == [first, second]


@pytest.mark.parametrize("kind", ["file", "section"])
@pytest.mark.parametrize("changed_field", ["text", "title"])
def test_same_snapshot_keeps_corrected_summary_representations(kind, changed_field):
    first = candidate("stable-summary", "旧摘要", 90, kind=kind)
    first.update(source_version="source_version:first", title="原标题")
    second = {**first, "score": 85, changed_field: "更正后的内容"}
    assert select_scored([first, second], 100)["items"] == [first, second]


@pytest.mark.parametrize("second_id", ["stable-summary", "same-evidence"])
def test_identical_summary_representations_still_deduplicate(second_id):
    first = candidate("stable-summary", "已核摘要", 90, kind="section")
    first.update(source_version="source_version:first", title="标题")
    second = {**first, "id": second_id, "score": 85}
    result = select_scored([first, second], 100)
    assert result["items"] == [first]
    assert result["omitted"][0]["reason"] == "duplicate"


@pytest.mark.parametrize("same_member", [True, False])
def test_image_evidence_keeps_distinct_locators(same_member):
    first = candidate("image-a", "批准", 90, start=None, end=None, kind="image")
    first.update(source_version="source_version:image", locator={"region": [0, 0, 10, 10]})
    second = {**first, "id": first["id"] if same_member else "image-b", "score": 85,
              "locator": {"region": [20, 20, 30, 30]}}
    assert select_scored([first, second], 100)["items"] == [first, second]


def test_equivalent_image_locator_objects_still_deduplicate():
    first = candidate("image-a", "批准", 90, start=None, end=None, kind="image")
    first["locator"] = {"page": 1, "region": [0, 0, 10, 10]}
    second = {**first, "id": "image-b", "score": 85,
              "locator": {"region": [0, 0, 10, 10], "page": 1}}
    result = select_scored([first, second], 100)
    assert result["items"] == [first]
    assert result["omitted"][0]["reason"] == "duplicate"


@pytest.mark.parametrize("score", [float("nan"), float("inf")])
def test_invalid_agent_score_is_visible(score):
    with pytest.raises(ValueError, match="Non-finite"):
        select_scored([candidate("invalid", "text", score)], 10)
