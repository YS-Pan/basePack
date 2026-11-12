import pytest

from basepack.memory.selection import select_scored


def candidate(identity, text, score, start=1, end=3, kind="chunk"):
    return {"id": identity, "text": text, "score": score, "kind": kind,
            "path": "材料.md", "knowledge_revision": "k1", "revision": "v1", "start_line": start, "end_line": end}


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
    with pytest.raises(ValueError, match="finite"):
        select_scored([candidate("invalid", "text", score)], 10)


def test_rank_requires_observed_version_and_preserves_distinct_knowledge_versions():
    first = candidate("stable", "同一来源里的适用条件", 90)
    second = {**first, "knowledge_revision": "k2", "score": 80}
    assert select_scored([first, second], 100)["items"] == [first, second]
    del first["knowledge_revision"]
    with pytest.raises(KeyError, match="knowledge_revision"):
        select_scored([first], 100)


def test_graph_versions_need_no_fake_source_location_and_use_the_same_budget():
    node = {"record_type": "node", "id": "node:goal", "knowledge_revision": "node-v1",
            "kind": "requirement", "title": "当前目标", "text": "用户要求", "score": 95}
    relation = {"record_type": "semantic", "id": "semantic:replaces", "knowledge_revision": "edge-v1",
                "kind": "supersedes", "text": "新目标替代旧目标", "score": 90,
                "endpoint_versions": {"in": {"id": "node:goal", "knowledge_revision": "node-v1"}}}
    old = {**node, "knowledge_revision": "node-v0", "score": 75, "text": "旧目标"}
    result = select_scored([node, {**node, "score": 80}, relation, old], 20)
    assert result["items"] == [node, relation, old]
    assert result["omitted"][0]["reason"] == "duplicate"
    assert all("path" not in item for item in result["items"])
    limited = select_scored([node, relation, old], 7)
    assert limited["items"] == [node, old]
    assert limited["omitted"][0]["id"] == relation["id"]
    assert limited["omitted"][0]["knowledge_revision"] == "edge-v1"


def test_rank_uses_the_single_final_score_without_access_reweighting():
    important = {**candidate("rare", "必要证据", 95), "access_weight": 0.01}
    popular = {**candidate("hot", "常用背景", 80, 8, 9), "access_weight": 1.0}
    assert select_scored([popular, important], 4)["items"] == [important]


@pytest.mark.parametrize("score", [-1, 101, True])
def test_scores_follow_the_common_zero_to_hundred_contract(score):
    with pytest.raises(ValueError, match="0–100"):
        select_scored([candidate("invalid", "text", score)], 10)
