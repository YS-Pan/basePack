import pytest

from basepack.memory.codex import _render
from basepack.memory.codex_locator import message_locations


def _snapshot(parts, memory_dir):
    rows = [{"turnId": "turn-1", "item": {"id": "item-1", "type": "userMessage", "content": parts}},
            {"turnId": "turn-2", "item": {"id": "item-2", "type": "agentMessage", "text": "后续文本"}}]
    return _render("project", {"id": "thread-1"}, rows, memory_dir, None)[0].decode("utf-8")


def _line_containing(text, needle):
    return next(i for i, line in enumerate(text.splitlines(keepends=True), 1) if needle in line)


def test_resolves_exact_message_parts_from_snapshot_with_multibyte_and_fake_header(tmp_path):
    fake = '{"thread_id":"fake","byte_length":100}'
    snapshot = _snapshot([{"type": "text", "text": "你好🚀\n" + fake + "\n末尾无换行"},
                          {"type": "text", "text": "第二部分"}], tmp_path)
    first_line = _line_containing(snapshot, "你好🚀")
    last_line = _line_containing(snapshot, "第二部分")
    found = message_locations(snapshot, first_line, last_line)
    assert [item["text"] for item in found] == ["你好🚀\n" + fake + "\n末尾无换行", "第二部分"]
    assert [(item["thread_id"], item["turn_id"], item["item_id"], item["part"]) for item in found] == [
        ("thread-1", "turn-1", "item-1", 0), ("thread-1", "turn-1", "item-1", 1)]
    data = snapshot.encode("utf-8")
    for item in found:
        assert data[item["snapshot_byte_start"]:item["snapshot_byte_end"]].decode("utf-8") == item["text"]
        assert item["chat_url"] == "codex://threads/thread-1"
    assert found[0]["part_byte_end"] == len(found[0]["text"].encode("utf-8"))
    assert all(item["thread_id"] != "fake" for item in found)


def test_line_subset_reports_part_byte_offsets_and_excludes_generated_headers(tmp_path):
    snapshot = _snapshot([{"type": "text", "text": "前文🚀\n中间\n结尾"}], tmp_path)
    middle = _line_containing(snapshot, "中间")
    result = message_locations(snapshot, middle, middle)
    assert len(result) == 1
    assert result[0]["text"] == "中间\n"
    assert result[0]["part_byte_start"] == len("前文🚀\n".encode("utf-8"))
    assert result[0]["part_byte_end"] == len("前文🚀\n中间\n".encode("utf-8"))
    assert message_locations(snapshot, 1, 1) == []


def test_old_snapshot_is_sufficient_after_revision_and_no_final_newline(tmp_path):
    old = _snapshot([{"type": "text", "text": "原始要求"}], tmp_path)
    new = _snapshot([{"type": "text", "text": "更新后要求"}], tmp_path)
    old_line = _line_containing(old, "原始要求")
    item = message_locations(old, old_line, old_line)[0]
    assert item["text"] == "原始要求"
    assert item["part_byte_end"] == len("原始要求".encode("utf-8"))
    assert "原始要求" not in new


def test_bad_framing_or_line_range_raises(tmp_path):
    snapshot = _snapshot([{"type": "text", "text": "内容"}], tmp_path)
    with pytest.raises(ValueError, match="Invalid line range"):
        message_locations(snapshot, 0, 1)
    with pytest.raises((ValueError, UnicodeDecodeError)):
        message_locations(snapshot.replace('"byte_length":6', '"byte_length":5', 1), 1, 1)
