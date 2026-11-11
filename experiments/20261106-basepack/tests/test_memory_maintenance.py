import json
import os

import pytest

from test_memory_store import batch_for, memory


def test_maintenance_reuses_semantics_for_line_endings_and_preserves_old_snapshot(memory, monkeypatch):
    from basepack.memory import candidate_vectors

    original = '# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n'
    batch = batch_for(memory, original)
    batch['nodes'].append({'id': 'archive', 'kind': 'decision', 'text': '保留资料', 'evidence': ['retention']})
    batch['edges'].append({'id': 'node_link', 'in': 'node:local', 'out': 'node:archive',
                           'kind': 'depends', 'text': '两项要求', 'evidence': ['storage', 'retention']})
    memory.apply(batch)
    old = memory.read('storage')['member']['source_version']
    calls = []
    embed = candidate_vectors.EmbeddingClient.embed

    def counted(self, inputs, *, timeout):
        calls.extend(inputs)
        return embed(self, inputs, timeout=timeout)

    monkeypatch.setattr(candidate_vectors.EmbeddingClient, 'embed', counted)
    (memory.config.root / 'guide.md').write_bytes(original.replace('\n', '\r\n').encode('utf-8'))
    result = memory.maintain(['guide.md'])
    assert result['mechanical_batches'] == 1
    assert not result['needs_semantic']
    assert len(calls) == 2  # only the two raw chunks changed; summaries were reused
    assert memory.read('storage')['original']['text'].endswith('\r\n')
    assert memory.read('storage', source_version=old, start_line=2, end_line=2)['original']['text'].endswith('\n')
    node = memory.neighbors('node:local')['record']
    edges = memory.neighbors('node:local')['edges']
    assert not node['stale'] and {edge['id'] for edge in edges} == {'semantic:requires', 'semantic:node_link'}
    assert all(not edge['stale'] for edge in edges)
    assert node['basis'][0]['source_version'] == old
    assert all(basis['source_version'] == old for edge in edges for basis in edge['basis'])
    assert not memory.maintain(['guide.md'])['needs_semantic']
    assert len(calls) == 2


def test_maintenance_finds_unaccepted_summary_after_source_only_acceptance(memory):
    original = '# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n'
    memory.apply(batch_for(memory, original))
    (memory.config.root / 'guide.md').write_bytes((original + '例外：缓存可删除。\n').encode('utf-8'))
    prepared = memory.prepare(['guide.md'])
    memory.apply({'sources': [{'path': 'guide.md', 'revision': prepared['sources'][0]['revision']}]})
    assert memory.changes(['guide.md'], deep=True) == []
    result = memory.maintain(['guide.md'])
    report = json.loads(open(result['receipt'], encoding='utf-8').read())
    assert result['needs_semantic']
    source = report['semantic'][0]
    assert 'member:guide' in {row['id'] for row in source['members']}
    assert 'member:storage' not in {row['id'] for row in source['members']}
    assert '缓存可删除' in source['versions'][0]['changes'][0]['new_text']


def test_uncovered_addition_survives_chunk_reuse_and_source_advance(memory):
    path = memory.config.root / 'notes.md'
    path.write_bytes(b'old requirement\n')
    source = memory.prepare(['notes.md'])['sources'][0]
    memory.apply({'sources': [{'path': 'notes.md', 'revision': source['revision']}],
                  'members': [{'id': 'one', 'kind': 'chunk', 'path': 'notes.md',
                               'start_line': 1, 'end_line': 1}]})
    path.write_bytes(b'old requirement\n\nnew requirement\n')
    first = memory.maintain(['notes.md'])
    # Another valid caller may accept only the source metadata. The old member
    # remains evidence of the uncovered difference after that baseline moves.
    prepared = memory.prepare(['notes.md'])
    memory.apply({'sources': [{'path': 'notes.md', 'revision': prepared['sources'][0]['revision']}]})
    second = memory.maintain(['notes.md'])
    assert first['reused_chunks'] == 1
    assert first['needs_semantic'] and second['needs_semantic']
    assert memory.changes(['notes.md'], deep=True) == []
    material = json.loads(open(second['receipt'], encoding='utf-8').read())
    assert 'new requirement' in material['semantic'][0]['uncovered_ranges'][0]['text']

    prepared = memory.prepare(['notes.md'])
    # A partial semantic acceptance may itself move the last old member to the
    # new version without accepting the newly added text.
    memory.apply({'sources': [{'path': 'notes.md', 'revision': prepared['sources'][0]['revision']}],
                  'expected': prepared['expected'], 'members': [
                      {'id': 'one', 'kind': 'chunk', 'path': 'notes.md', 'start_line': 1, 'end_line': 1}]})
    assert memory.changes(['notes.md'], deep=True) == []
    assert memory.maintain(['notes.md'])['needs_semantic']
    prepared = memory.prepare(['notes.md'])
    memory.apply({'sources': [{'path': 'notes.md', 'revision': prepared['sources'][0]['revision']}],
                  'expected': prepared['expected'], 'members': [
                      {'id': 'two', 'kind': 'chunk', 'path': 'notes.md', 'start_line': 2, 'end_line': 3}]})
    assert not memory.maintain(['notes.md'])['needs_semantic']


@pytest.mark.parametrize('retire', [False, True])
def test_source_without_active_knowledge_remains_discoverable(memory, retire):
    path = memory.config.root / 'notes.md'
    path.write_bytes(b'new requirement\n')
    source = memory.prepare(['notes.md'])['sources'][0]
    batch = {'sources': [{'path': 'notes.md', 'revision': source['revision']}]}
    if retire:
        batch['members'] = [{'id': 'one', 'kind': 'chunk', 'path': 'notes.md', 'start_line': 1, 'end_line': 1}]
    memory.apply(batch)
    if retire:
        expected = memory.prepare(['notes.md'])['expected']
        memory.apply({'sources': [], 'expected': expected, 'delete_members': ['one']})
    assert memory.changes(['notes.md'], deep=True) == []
    for _ in range(2):
        result = memory.maintain(['notes.md'])
        material = json.loads(open(result['receipt'], encoding='utf-8').read())
        assert result['needs_semantic']
        assert material['semantic'][0]['reason'] == 'no_active_knowledge'


def test_current_file_acceptance_does_not_flag_fixed_old_relation_basis(memory):
    original = '# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n'
    memory.apply(batch_for(memory, original))
    old = memory.read('storage')['member']['source_version']
    changed = original + '例外：缓存可以删除。\n'
    update = batch_for(memory, changed)
    update['members'][0]['end_line'] = 6
    update['members'][0]['text'] = '本地隔离；资料须保留，但缓存可以删除。'
    update.pop('nodes')
    update.pop('edges')
    memory.apply(update)
    result = memory.maintain(['guide.md'])
    assert not result['needs_semantic']
    assert memory.neighbors('node:local')['record']['basis'][0]['source_version'] == old
    assert memory.neighbors('node:local')['edges'][0]['basis'][0]['source_version'] == old


def test_source_only_then_first_partial_acceptance_keeps_uncovered_text(memory):
    path = memory.config.root / 'notes.md'
    path.write_bytes(b'old\n')
    prepared = memory.prepare(['notes.md'])
    memory.apply({'sources': [{'path': 'notes.md', 'revision': prepared['sources'][0]['revision']}]})
    path.write_bytes(b'old\nnew\n')
    prepared = memory.prepare(['notes.md'])
    memory.apply({'sources': [{'path': 'notes.md', 'revision': prepared['sources'][0]['revision']}],
                  'members': [{'id': 'one', 'kind': 'chunk', 'path': 'notes.md', 'start_line': 1, 'end_line': 1}]})
    for _ in range(2):
        result = memory.maintain(['notes.md'])
        report = json.loads(open(result['receipt'], encoding='utf-8').read())
        assert result['needs_semantic']
        assert report['semantic'][0]['uncovered_ranges'][0]['text'] == 'new\n'


def test_multiple_partial_versions_keep_earlier_uncovered_text(memory):
    path = memory.config.root / 'notes.md'
    path.write_bytes(b'old\n')
    prepared = memory.prepare(['notes.md'])
    memory.apply({'sources': [{'path': 'notes.md', 'revision': prepared['sources'][0]['revision']}],
                  'members': [{'id': 'one', 'kind': 'chunk', 'path': 'notes.md', 'start_line': 1, 'end_line': 1}]})
    path.write_bytes(b'old\nX\n')
    prepared = memory.prepare(['notes.md'])
    memory.apply({'sources': [{'path': 'notes.md', 'revision': prepared['sources'][0]['revision']}],
                  'expected': prepared['expected'], 'members': [
                      {'id': 'one', 'kind': 'chunk', 'path': 'notes.md', 'start_line': 1, 'end_line': 1}]})
    path.write_bytes(b'old\nX\nY\n')
    prepared = memory.prepare(['notes.md'])
    memory.apply({'sources': [{'path': 'notes.md', 'revision': prepared['sources'][0]['revision']}],
                  'expected': prepared['expected'], 'members': [
                      {'id': 'one', 'kind': 'chunk', 'path': 'notes.md', 'start_line': 1, 'end_line': 1},
                      {'id': 'two', 'kind': 'chunk', 'path': 'notes.md', 'start_line': 3, 'end_line': 3}]})
    for _ in range(2):
        result = memory.maintain(['notes.md'])
        report = json.loads(open(result['receipt'], encoding='utf-8').read())
        assert report['semantic'][0]['uncovered_ranges'][0]['text'] == 'X\n'


@pytest.mark.parametrize('addition', [b'\n', b' \n', b'  indented\n'])
def test_uncovered_whitespace_and_indentation_remain_pending(memory, addition):
    path = memory.config.root / 'notes.md'
    path.write_bytes(b'old\n')
    prepared = memory.prepare(['notes.md'])
    memory.apply({'sources': [{'path': 'notes.md', 'revision': prepared['sources'][0]['revision']}],
                  'members': [{'id': 'one', 'kind': 'chunk', 'path': 'notes.md', 'start_line': 1, 'end_line': 1}]})
    path.write_bytes(b'old\n' + addition)
    for _ in range(2):
        result = memory.maintain(['notes.md'])
        report = json.loads(open(result['receipt'], encoding='utf-8').read())
        assert report['semantic'][0]['uncovered_ranges'][0]['text'] == addition.decode()
    prepared = memory.prepare(['notes.md'])
    memory.apply({'sources': [{'path': 'notes.md', 'revision': prepared['sources'][0]['revision']}],
                  'expected': prepared['expected'], 'members': [
                      {'id': 'summary', 'kind': 'file', 'path': 'notes.md', 'start_line': 1, 'end_line': 2,
                       'text': 'Accepted full source.'}]})
    assert not memory.maintain(['notes.md'])['needs_semantic']


def test_metadata_refresh_does_not_restore_correction(memory):
    original = '# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n'
    memory.apply(batch_for(memory, original))
    prepared = memory.prepare(['guide.md'])
    memory.apply({'sources': [], 'expected': prepared['expected'], 'corrections': [
        {'id': 'known_error', 'target': 'member:storage', 'reason': '已知错误'}]})
    source = memory.config.root / 'guide.md'
    os.utime(source, ns=(source.stat().st_atime_ns, source.stat().st_mtime_ns + 1_000_000))
    result = memory.maintain(['guide.md'])
    assert result['mechanical_batches'] == 1
    assert result['needs_semantic']
    assert memory.read('storage')['member']['stale'] is True


def test_maintenance_reports_moved_lines_and_section_end_insertion(memory, monkeypatch):
    from basepack.memory import candidate_vectors

    original = '# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n'
    memory.apply(batch_for(memory, original))
    changed = '前言。\n' + original.replace('\n\n# 保留', '\n例外：临时库可共享。\n\n# 保留')
    (memory.config.root / 'guide.md').write_bytes(changed.encode('utf-8'))
    calls = []
    embed = candidate_vectors.EmbeddingClient.embed
    monkeypatch.setattr(candidate_vectors.EmbeddingClient, 'embed',
                        lambda self, inputs, *, timeout: (calls.extend(inputs), embed(self, inputs, timeout=timeout))[1])
    result = memory.maintain(['guide.md'])
    report = json.loads(open(result['receipt'], encoding='utf-8').read())
    source = report['semantic'][0]
    assert 'member:storage_section' in {row['id'] for row in source['members']}
    assert 'node:local' in {row['id'] for row in source['related_nodes']}
    assert 'semantic:requires' in {row['id'] for row in source['related_edges']}
    moved = {row['id']: row['new_lines'] for row in source['line_mappings']}
    assert moved['member:storage'] == [3, 3]
    assert report['reused_chunks'] == ['member:retention']
    assert memory.read('retention')['original']['start_line'] == 7
    assert not calls
    assert memory.changes(['guide.md'], deep=True) == []
    assert memory.maintain(['guide.md'])['needs_semantic']


def test_same_chunk_under_another_heading_needs_semantic_review(memory):
    original = '# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n'
    memory.apply(batch_for(memory, original))
    changed = '# 数据库\n本地数据库隔离项目。\n资料必须保留。\n\n# 保留\n'
    (memory.config.root / 'guide.md').write_bytes(changed.encode('utf-8'))
    result = memory.maintain(['guide.md'])
    source = json.loads(open(result['receipt'], encoding='utf-8').read())['semantic'][0]
    assert 'member:retention' in {row['id'] for row in source['members']}


def test_stopped_maintenance_does_not_publish_or_advance_source(memory):
    from basepack.memory.maintenance import MaintenanceStopped, stop

    original = '# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n'
    memory.apply(batch_for(memory, original))
    revision = memory.sources()[0]['revision']
    (memory.config.root / 'guide.md').write_bytes(original.replace('\n', '\r\n').encode('utf-8'))
    control = memory.config.root / 'stopped'
    stop(control)
    with pytest.raises(MaintenanceStopped):
        memory.maintain(['guide.md'], control=str(control))
    assert memory.sources()[0]['revision'] == revision


def test_mechanical_publish_rejects_concurrent_knowledge_correction(memory, monkeypatch):
    original = '# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n'
    memory.apply(batch_for(memory, original))
    source = memory.config.root / 'guide.md'
    source.write_bytes(original.replace('\n', '\r\n').encode('utf-8'))
    apply = memory.apply

    def concurrent(batch, **kwargs):
        expected = memory.prepare(['guide.md'])['expected']
        apply({'sources': [], 'expected': expected, 'corrections': [
            {'id': 'racing_error', 'target': 'member:storage', 'reason': '并发更正'}]})
        return apply(batch, **kwargs)

    monkeypatch.setattr(memory, 'apply', concurrent)
    with pytest.raises(RuntimeError, match='Knowledge revision changed'):
        memory.maintain(['guide.md'])
    assert memory.read('storage')['member']['stale'] is True


def test_mechanical_publish_rejects_concurrent_original_change(memory, monkeypatch):
    original = '# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n'
    memory.apply(batch_for(memory, original))
    source = memory.config.root / 'guide.md'
    source.write_bytes(original.replace('\n', '\r\n').encode('utf-8'))
    revision = memory.sources()[0]['revision']
    apply = memory.apply

    def concurrent(batch, **kwargs):
        source.write_bytes((original + '并发补充。\n').encode('utf-8'))
        return apply(batch, **kwargs)

    monkeypatch.setattr(memory, 'apply', concurrent)
    with pytest.raises(ValueError, match='Source revision mismatch'):
        memory.maintain(['guide.md'])
    assert memory.sources()[0]['revision'] == revision


def test_brief_reports_codex_capability_without_collection(memory):
    assert memory.brief(limit=0)['codex_collection']['status'] == 'unavailable'
    memory.connection['codex'] = {'project_id': 'project', 'registry_complete': False}
    assert memory.brief(limit=0)['codex_collection']['status'] == 'registry_incomplete'
    memory.connection['codex']['registry_complete'] = True
    state = memory.brief(limit=0)['codex_collection']
    assert state['status'] == 'not_checked'
    assert 'does not collect' in state['note']


def test_task_start_detects_scoped_addition_without_claiming_it_understood(memory):
    memory.apply(batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n"))
    memory.connection["source_scope"] = ["guide.md", "incoming"]
    incoming = memory.config.root / "incoming"
    incoming.mkdir()
    (incoming / "new.md").write_text("新增例外需要实际阅读。\n", encoding="utf-8")
    brief = memory.brief(limit=0)
    assert "changes" not in brief
    assert memory.changes(["incoming"])[0]["path"] == "incoming/new.md"
    assert memory.changes(["incoming"])[0]["kind"] == "added"
    assert brief["source_count"] == 1
    assert memory.search("新增例外") == []
    assert len(brief["mandatory"]) == 1


def test_task_start_checks_registered_originals_outside_new_discovery_scope(memory):
    memory.apply(batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n"))
    memory.connection["source_scope"] = ["incoming"]
    source = memory.config.root / "guide.md"
    source.write_bytes(source.read_bytes() + "\n新增例外。\n".encode("utf-8"))
    assert "changes" not in memory.brief()
    assert memory.changes(["guide.md"])[0]["path"] == "guide.md"


def test_maintenance_discovery_override_keeps_registered_source_changes(memory):
    original = "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n"
    memory.apply(batch_for(memory, original))
    (memory.config.root / "guide.md").write_bytes((original + "新的历史来源约束。\n").encode("utf-8"))
    (memory.config.root / "selected.md").write_text("仅覆盖新增发现。\n", encoding="utf-8")
    result = memory.maintain(["selected.md"])
    report = json.loads(open(result["receipt"], encoding="utf-8").read())
    assert {item["path"] for item in report["semantic"]} == {"guide.md", "selected.md"}
    assert any(item["path"] == "guide.md" and item["kind"] == "modified" for item in report["changes"])


def test_maintenance_empty_discovery_keeps_unaccepted_sources_and_pending_relations(memory):
    memory.apply(batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n"))
    (memory.config.root / "old-unaccepted.md").write_text("尚未接受的旧来源。\n", encoding="utf-8")
    prepared = memory.prepare(["old-unaccepted.md"])
    memory.apply({"sources": [{"path": "old-unaccepted.md", "revision": prepared["sources"][0]["revision"]}]})
    memory._execute("UPDATE node:local SET stale=true;")
    result = memory.maintain([])
    report = json.loads(open(result["receipt"], encoding="utf-8").read())
    assert result["needs_semantic"]
    assert any(item["path"] == "old-unaccepted.md" and item["reason"] == "no_active_knowledge"
               for item in report["semantic"])
    assert "node:local" in {item["id"] for item in report["pending_relations"]}


def test_change_detection_keeps_published_knowledge(memory):
    memory.apply(batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n"))
    source = memory.config.root / "guide.md"
    source.write_bytes(source.read_bytes() + "\n新增关键例外。\n".encode("utf-8"))
    count = len(memory._rows("change"))
    assert memory.changes(["guide.md"])[0]["kind"] == "modified"
    assert memory.brief(limit=0)["mandatory"][0]["stale"] is False
    assert "member:guide" in {row["id"] for row in memory.search("项目", literal=True)}
    assert len(memory._rows("change")) == count


def test_unchanged_start_reads_metadata_without_loading_all_member_bodies(memory, monkeypatch):
    memory.apply(batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n"))
    original_rows = memory._rows

    def rows(table):
        assert table != "member", "unchanged startup must not fetch all accepted bodies"
        return original_rows(table)

    monkeypatch.setattr(memory, "_rows", rows)
    assert "changes" not in memory.brief(limit=0)


def test_startup_receives_short_project_map_without_opaque_versions(memory):
    memory.apply(batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n"))
    result = memory.brief()
    assert result["clues"]
    assert all(row["clue_role"] == "map" for row in result["clues"])
    assert "basis" not in result["mandatory"][0]
    assert "knowledge_revision" not in result["mandatory"][0]
    candidates = memory.search("数据库")
    assert candidates
    assert all("basis" not in row and "knowledge_revision" not in row for row in candidates)


def test_node_merge_and_deleted_support_preserve_remaining_evidence(memory):
    batch = batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n")
    batch["nodes"].append({"id": "alias", "kind": "decision", "text": "采用本地数据库", "evidence": ["storage"]})
    batch["edges"].append({"id": "preserve", "in": "node:alias", "out": "member:retention",
                           "kind": "depends", "text": "资料需保留", "evidence": ["retention"]})
    memory.apply(batch)
    expected = memory.prepare(["guide.md"])["expected"]
    memory.apply({"sources": [], "expected": expected, "delete_nodes": ["alias"],
                  "edges": [{"id": "preserve", "in": "node:local", "out": "member:retention",
                             "kind": "depends", "text": "资料需保留", "evidence": ["retention"]}]})
    assert {edge["id"] for edge in memory.neighbors("node:local")["edges"]} == {"semantic:requires", "semantic:preserve"}
    assert memory.neighbors("node:alias")["record"]["retired"] is True
    assert any(row.get("previous") and row["previous"].get("in") == "node:alias"
               for row in memory._rows("change") if row.get("target") == "semantic:preserve")

    (memory.config.root / "backup.md").write_bytes("本地数据库隔离项目。\n".encode("utf-8"))
    prepared = memory.prepare(["guide.md", "backup.md"])
    backup = next(row for row in prepared["sources"] if row["path"] == "backup.md")
    members = [
        {"id": "backup", "kind": "file", "path": "backup.md", "parent": None,
         "start_line": 1, "end_line": 1, "title": "另一依据", "text": "本地数据库隔离项目。", "evidence": ["backup_leaf"]},
        {"id": "backup_leaf", "kind": "chunk", "path": "backup.md", "parent": "backup",
         "start_line": 1, "end_line": 1, "title": "隔离要求", "text": "本地数据库隔离项目。\n"},
    ]
    edge = {"id": "requires", "in": "node:local", "out": "member:storage", "kind": "depends",
            "text": "本地数据库隔离项目", "evidence": ["storage", "backup_leaf"]}
    memory.apply({"sources": [{"path": "backup.md", "revision": backup["revision"]}],
                  "expected": prepared["expected"], "members": members, "edges": [edge]})
    (memory.config.root / "backup.md").unlink()
    assert "semantic:requires" not in {row["id"] for row in memory.brief()["pending"]}
    assert memory.changes(["backup.md"])[0]["kind"] == "deleted"
    prepared = memory.prepare(["guide.md", "backup.md"])
    edge["evidence"] = ["storage"]
    memory.apply({"sources": [{"path": "backup.md", "revision": backup["revision"], "deleted": True}],
                  "expected": prepared["expected"], "edges": [edge]})
    assert memory.brief()["pending_count"] == 0
    assert len(memory._rows("source_version")) == 2
    assert any(row.get("text") == "本地数据库隔离项目。\n" for row in memory._rows("source_version"))
    assert len(memory.neighbors("node:local")["edges"]) == 2
    assert next(row for row in memory._rows("member") if row["id"] == "member:backup_leaf")["retired"] is True
    assert memory.changes(["backup.md"]) == []


def test_chunk_boundaries_take_exact_crlf_original_without_repeating_raw_text(memory):
    source = memory.config.root / "windows.md"
    source.write_bytes("# 标题\r\n条件与例外必须保留。\r\n".encode("utf-8"))
    prepared = memory.prepare(["windows.md"])
    memory.apply({"sources": [{"path": "windows.md", "revision": prepared["sources"][0]["revision"]}],
                  "expected": prepared["expected"], "members": [
                      {"id": "windows", "kind": "file", "path": "windows.md", "parent": None,
                       "start_line": 1, "end_line": 2, "title": "标题", "text": "条件与例外须保留。", "evidence": ["windows_body"]},
                      {"id": "windows_body", "kind": "chunk", "path": "windows.md", "parent": "windows",
                       "start_line": 2, "end_line": 2, "title": "条件"}]})
    assert memory.read("windows_body")["original"]["text"] == "条件与例外必须保留。\r\n"


def test_accepted_source_deletion_removes_retired_startup_obligations(memory):
    memory.apply(batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n"))
    prepared = memory.prepare(["guide.md"])
    (memory.config.root / "guide.md").unlink()
    memory.apply({"sources": [{"path": "guide.md", "revision": prepared["sources"][0]["revision"], "deleted": True}],
                  "expected": prepared["expected"], "delete_nodes": ["local"], "delete_edges": ["requires"]})
    brief = memory.brief()
    assert brief["mandatory"] == []
    assert brief["mandatory_pending_count"] == 0
    assert brief["pending_count"] == 0
    assert brief["coverage_gaps_count"] == 0


def test_retired_chunk_does_not_invalidate_reaccepted_ancestors(memory):
    memory.apply(batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n"))
    updated = batch_for(memory, "# 数据库\n数据库离线运行并隔离项目。\n\n# 保留\n资料必须保留。\n")
    updated["members"][2]["id"] = "current_storage"
    for item in updated["members"] + updated["nodes"] + updated["edges"]:
        item["evidence"] = ["current_storage" if value == "storage" else value for value in item.get("evidence", [])]
    updated["edges"][0]["out"] = "member:current_storage"
    updated["delete_members"] = ["storage"]
    memory.apply(updated)
    prepared = memory.prepare(["guide.md"])
    before = {row["id"]: row for row in prepared["sources"][0]["members"]}
    assert before["member:storage"]["retired"] is True
    assert prepared["expected"]["member:storage"] == before["member:storage"]["knowledge_revision"]
    assert memory.brief(limit=0)["pending_count"] == 0
    relation = {"id": "current_support", "in": "member:current_storage", "out": "member:retention",
                "kind": "supports", "text": "当前条件共同约束存储", "evidence": ["current_storage", "retention"]}
    result = memory.apply({"sources": updated["sources"], "expected": prepared["expected"], "edges": [relation]})
    assert result["invalidated"] == []
    assert memory.brief(limit=0)["pending_count"] == 0
    assert memory.read("current_storage")["original"]["text"] == "数据库离线运行并隔离项目。\n"
    assert {row["id"] for row in memory.neighbors("current_storage")["edges"]} == {
        "semantic:requires", "semantic:current_support"}
    after = {row["id"]: row for row in memory._rows("member")}
    for member_id in ("member:guide", "member:storage_section", "member:storage"):
        assert after[member_id] == before[member_id]
    assert memory.apply({"sources": updated["sources"]})["invalidated"] == []


@pytest.mark.parametrize("retired", [False, True])
def test_only_active_summary_dependencies_propagate_changes(memory, retired):
    memory.apply(batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n"))
    updated = batch_for(memory, "# 数据库\n数据库离线运行并隔离项目。\n\n# 保留\n资料必须保留。\n")
    guide, storage = updated["members"][0], updated["members"][2]
    guide.update(start_line=4, end_line=5, text="资料必须保留。", evidence=["retention"],
                 coverage_gaps=["数据库章节独立维护"])
    memory.apply({"sources": updated["sources"], "expected": updated["expected"],
                  "members": [guide, storage], "delete_members": ["storage_section"] if retired else []})
    prepared = memory.prepare(["guide.md"])
    section = next(row for row in prepared["sources"][0]["members"] if row["id"] == "member:storage_section")
    assert section["stale"] is retired
    assert section["retired"] is retired
    storage["title"] = "离线隔离条件"
    result = memory.apply({"sources": updated["sources"], "expected": prepared["expected"], "members": [storage]})
    assert result["invalidated"] == []
    assert memory.read("guide")["member"]["stale"] is False
    # Existing node retains its old versioned evidence, even if the new member changes.
    assert memory.neighbors("node:local")["record"]["stale"] is False


def test_retired_unchanged_history_keeps_source_version_and_can_be_explicitly_revived(memory):
    original = batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n")
    memory.apply(original)
    prepared = memory.prepare(["guide.md"])
    memory.apply({"sources": [], "expected": prepared["expected"], "delete_members": ["storage", "storage_section"],
                  "delete_nodes": ["local"], "delete_edges": ["requires"]})
    retired = {row["id"]: row for row in memory._rows("member") if row["retired"]}
    updated = batch_for(memory, "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料与旧依据必须保留。\n")
    updated["members"][0]["evidence"] = ["retention"]
    memory.apply({"sources": updated["sources"], "expected": updated["expected"],
                  "members": [updated["members"][0], updated["members"][3]]})
    after = {row["id"]: row for row in memory._rows("member") if row["retired"]}
    assert after == retired
    snapshot = memory._execute(f"SELECT * FROM ONLY {after['member:storage']['source_version']};")[0]
    assert snapshot["text"] == "# 数据库\n本地数据库隔离项目。\n\n# 保留\n资料必须保留。\n"
    prepared = memory.prepare(["guide.md"])
    revival = {"sources": updated["sources"], "members": [{**original["members"][2], "parent": None}]}
    with pytest.raises(RuntimeError, match="requires expected revision"):
        memory.apply(revival)
    memory.apply({"sources": [], "expected": prepared["expected"], "delete_members": ["storage"]})
    with pytest.raises(RuntimeError, match="Knowledge revision changed"):
        memory.apply({**revival, "expected": prepared["expected"]})
    memory.apply({**revival, "expected": memory.prepare(["guide.md"])["expected"],
                  "corrections": [{"id": "revive_storage", "target": "member:storage", "reason": "重新接受当前原文"}]})
    current = memory.read("storage")["member"]
    assert current["retired"] is False
    assert current["source_revision"] == updated["sources"][0]["revision"]
    previous = memory._execute("SELECT * FROM ONLY change:revive_storage;")[0]["previous"]
    assert previous["retired"] is True
    assert previous["source_version"] == retired["member:storage"]["source_version"]
