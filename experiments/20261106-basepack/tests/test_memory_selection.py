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


@pytest.mark.parametrize("score", [float("nan"), float("inf")])
def test_invalid_agent_score_is_visible(score):
    with pytest.raises(ValueError, match="Non-finite"):
        select_scored([candidate("invalid", "text", score)], 10)
