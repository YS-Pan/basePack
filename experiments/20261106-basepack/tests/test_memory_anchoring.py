import pytest

from basepack.memory.content import (
    comparison_text, line_changes, literal_spans, locate_lines, mapped_line_range,
)


def test_comparison_preserves_everything_except_crlf():
    original = "  中文😀\r\n\tkeep  spaces\rsolo\nCafe\u0301 != Café\u2028"
    assert comparison_text(original) == (
        "  中文😀\n\tkeep  spaces\rsolo\nCafe\u0301 != Café\u2028")


def test_line_ending_only_change_maps_all_original_lines():
    before = "# 条件\r\n\r\n正文😀\r\n末行"
    after = before.replace("\r\n", "\n")
    changes = line_changes(before, after)
    assert changes == [("equal", 0, 4, 0, 4)]
    assert mapped_line_range(changes, 1, 4) == (1, 4)
    anchor, = locate_lines(before, after, 3, 4)
    assert (anchor.start_line, anchor.end_line, anchor.context_match) == (3, 4, True)
    assert after[anchor.start:anchor.end] == "正文😀\n末行"


def test_front_insertion_maps_unchanged_lines_and_preserves_raw_offsets():
    before = "# 条件\r\n中文😀\r\n第二行\r\n"
    after = "新增\r\n\r\n" + before
    changes = line_changes(before, after)
    assert changes == [("insert", 0, 0, 0, 2), ("equal", 0, 3, 2, 5)]
    assert mapped_line_range(changes, 2, 3) == (4, 5)
    anchor, = locate_lines(before, after, 2, 3)
    assert (anchor.start_line, anchor.end_line) == (4, 5)
    assert anchor.start == len("新增\r\n\r\n# 条件\r\n")
    assert after[anchor.start:anchor.end] == "中文😀\r\n第二行\r\n"
    assert anchor.context_match


def test_changed_or_internally_split_range_is_not_mapped_as_equal():
    before = "first\nsecond\nthird\n"
    changes = line_changes(before, "first\nnew\nsecond\nthird\n")
    assert mapped_line_range(changes, 1, 3) is None
    assert mapped_line_range(changes, 2, 3) == (3, 4)
    assert mapped_line_range(line_changes(before, "first\nchanged\nthird\n"), 2, 2) is None


def test_line_move_retains_position_without_claiming_unchanged_context():
    before = "# A\nbody\n# B\nother\n"
    after = "# A\n# B\nother\nbody\n"
    anchor, = locate_lines(before, after, 2, 2)
    assert (anchor.start_line, anchor.end_line) == (4, 4)
    assert after[anchor.start:anchor.end] == "body\n"
    assert not anchor.context_match


@pytest.mark.parametrize("text,quote,expected", [
    ("aaaa", "aaa", [(0, 3), (1, 4)]),
    ("banana", "ana", [(1, 4), (3, 6)]),
    ("😀中😀中", "😀中", [(0, 2), (2, 4)]),
    ("[a].*?\\\n[a].*?\\", "[a].*?\\", [(0, 7), (8, 15)]),
])
def test_all_literal_occurrences_include_overlaps_and_regex_metacharacters(text, quote, expected):
    assert literal_spans(text, quote) == expected


def test_literal_context_is_exact_and_returns_quote_span():
    assert literal_spans("aaaaa", "aa", prefix="a", suffix="a") == [(1, 3), (2, 4)]
    assert literal_spans("p[中😀]s", "中😀", prefix="p[", suffix="]s") == [(2, 4)]
    assert literal_spans("P[中😀]s", "中😀", prefix="p[", suffix="]s") == []
    assert literal_spans("Café", "Cafe\u0301") == []
    assert literal_spans("one  two", "one two") == []


def test_duplicate_quotes_keep_all_candidates_and_context_evidence():
    before = "first\nquote\nend\n"
    after = "first\nquote\nend\nsecond\nquote\nend\n"
    candidates = locate_lines(before, after, 2, 2)
    assert [(item.start_line, item.end_line, item.context_match) for item in candidates] == [
        (2, 2, True), (5, 5, False)]
    # difflib may map one repeated range; that is not a uniqueness guarantee.
    assert mapped_line_range(line_changes(before, after), 2, 2) == (2, 2)


def test_overlapping_complete_line_quotes_remain_ambiguous():
    candidates = locate_lines("x\nx\n", "x\nx\nx\n", 1, 2)
    assert [(item.start_line, item.end_line) for item in candidates] == [(1, 2), (2, 3)]
    assert all(item.context_match for item in candidates)


def test_context_edits_do_not_hide_exact_body():
    anchor, = locate_lines("old heading\nbody\nend\n", "new heading\nbody\nend\n", 2, 2)
    assert anchor.start_line == 2
    assert not anchor.context_match
    assert locate_lines("old heading\nbody\nend\n", "new heading\nchanged\nend\n", 2, 2) == []


@pytest.mark.parametrize("before,after", [
    ("target\n", "prefix target\n"),
    ("target", "target tail"),
    ("target", "target\n"),
    ("target\n", "target"),
])
def test_substring_and_partial_line_matches_are_not_line_candidates(before, after):
    assert locate_lines(before, after, 1, 1) == []


def test_unicode_line_boundaries_and_unterminated_last_line():
    before = "head\u2028中文😀\r\nlast"
    after = "new\n" + before
    anchor, = locate_lines(before, after, 2, 3)
    assert (anchor.start_line, anchor.end_line) == (3, 4)
    assert after[anchor.start:anchor.end] == "中文😀\r\nlast"


def test_lone_carriage_return_is_not_lost_when_normalization_joins_characters():
    assert line_changes("\r\r\n", "\r\n") == [
        ("delete", 0, 1, 0, 0), ("equal", 1, 2, 0, 1)]
    anchor, = locate_lines("\r\r\n", "\r\r\n", 1, 1)
    assert (anchor.start_line, anchor.end_line, anchor.start, anchor.end) == (1, 1, 0, 1)


def test_empty_new_source_has_no_candidates_or_line_mappings():
    assert locate_lines("old\n", "", 1, 1) == []
    assert line_changes("", "") == []
    assert mapped_line_range(line_changes("old\n", ""), 1, 1) is None


@pytest.mark.parametrize("start,end", [(0, 1), (-1, 1), (2, 1), (1, 3)])
def test_quote_range_must_select_existing_complete_old_lines(start, end):
    with pytest.raises(ValueError, match="Invalid line range"):
        locate_lines("one\ntwo", "one\ntwo", start, end)


def test_empty_quote_and_negative_context_are_invalid():
    with pytest.raises(ValueError, match="Quote must not be empty"):
        literal_spans("source", "")
    with pytest.raises(ValueError, match="context_chars"):
        locate_lines("one", "one", 1, 1, context_chars=-1)
