import json

import pytest

from basepack.memory.query import overview_working_set, startup_overview


def test_large_chat_inventory_keeps_graph_and_project_entries_with_bounded_output():
    prefix = 'workspace/memory/codex/'
    chats = [dict(id=f'member:chat{i:04}', kind='file', path=f'{prefix}{i:04}.txt',
                  title='chat', text='chat content ' * 500, knowledge_revision=f'c{i}', private=False)
             for i in range(1000)]
    projects = [dict(id='member:system', kind='file', path='devDoc/system/overview.md',
                     title='System', text='system ' * 500, knowledge_revision='v1'),
                dict(id='member:task', kind='file', path='experiments/task/readme.md',
                     title='Task', text='task' * 500, knowledge_revision='v2')]
    nodes = [dict(id='node:goal', kind='goal', title='Goal', text='goal ' * 500, knowledge_revision='n1'),
             dict(id='node:decision', kind='decision', title='Decision', text='decision ' * 500,
                  knowledge_revision='n2', private=True)]
    sources = [dict(id=f'source:{i}', path=f'unread/{i}.md', kind='text') for i in range(1000)]
    result = startup_overview(chats + projects, nodes, sources, 6, chat_prefix=prefix)
    assert len(result['clues']) == 6
    assert {'member:system', 'member:task'} <= {row['id'] for row in result['clues']}
    assert any(row['record_type'] == 'node' for row in result['clues'])
    assert any(row.get('path', '').startswith(prefix) for row in result['clues'])
    assert all(len(row['text']) <= 800 and row['text_truncated'] for row in result['clues'])
    assert result['overview_groups'] == {'graph_nodes': 2, 'project_summaries': 2,
                                         'managed_chat_summaries': 1000}
    assert result['overview_count'] == 1004
    assert result['clues_omitted_count'] == 998
    assert len(result['unmapped_sources']) == 3
    assert result['unmapped_count'] == 1000 and result['unmapped_omitted_count'] == 997
    assert len(json.dumps(result, ensure_ascii=False)) < 12000
    assert 'overview_index' not in result
    workset = overview_working_set(chats + projects, nodes, 6, chat_prefix=prefix, rotation='2026-11-17')
    hints = [{**row, 'access_interval': [0.2, 0.6], 'access_model': 'm' * 64,
              'access_compiled_j': 10, 'access_fact_j': 12, 'access_support': 5,
              'access_status': 'lagging', 'access_prior': False} for row in workset]
    sampled = startup_overview(chats + projects, nodes, sources, 6, chat_prefix=prefix, candidates=hints)
    assert len(json.dumps(sampled, ensure_ascii=False)) < 12000
    assert all('access_interval' in row for row in sampled['clues'])


def test_overview_discloses_truncation_and_mandatory_is_mapped_independently():
    member = dict(id='member:a', kind='file', path='a.md', text='x' * 801)
    sources = [dict(id='source:a', path='a.md'), dict(id='source:b', path='b.md'),
               dict(id='source:c', path='c.md'), dict(id='source:gone', path='gone.md', deleted=True)]
    result = startup_overview([member], [], sources, 1, mandatory=[dict(path='b.md')])
    assert result['clues'][0]['text_truncated'] is True
    assert result['unmapped_sources'][0]['path'] == 'c.md'
    assert result['unmapped_count'] == 1
    no_clues = startup_overview([member], [], sources, 0, mandatory=[dict(path='b.md')])
    assert no_clues['clues'] == [] and no_clues['unmapped_omitted_count'] == 1


def test_node_and_project_entries_are_not_drowned_by_chat_when_limit_is_small():
    members = [dict(id=f'member:{i}', kind='file', path=f'.basepack/memory/codex/{i}.txt', text='chat')
               for i in range(20)]
    members.append(dict(id='member:project', kind='file', path='devDoc/guide.md', text='project'))
    nodes = [dict(id='node:goal', kind='goal', text='goal')]
    result = startup_overview(members, nodes, [], 2)
    assert {row['id'] for row in result['clues']} == {'node:goal', 'member:project'}


def test_empty_overview_and_invalid_limit():
    assert startup_overview([], [], [], 6)['clues'] == []
    with pytest.raises(ValueError, match='non-negative'):
        startup_overview([], [], [], -1)


def test_same_group_prefers_hot_but_retains_cold_and_unknown():
    cold = dict(id='member:cold', kind='file', path='devDoc/cold.md', text='cold',
                knowledge_revision='c', access_interval=[0.01, 0.02], access_model='sigma',
                access_compiled_j=10, access_fact_j=10, access_support=3, access_prior=False)
    hot = dict(id='member:hot', kind='file', path='devDoc/hot.md', text='hot',
               knowledge_revision='h', access_interval=[0.8, 0.9], access_model='sigma',
               access_compiled_j=10, access_fact_j=10, access_support=7, access_prior=False)
    unknown = dict(id='member:unknown', kind='file', path='devDoc/unknown.md', text='new',
                   knowledge_revision='u', access_interval=[0, 1], access_prior=True)
    result = startup_overview([cold, hot, unknown], [], [], 3)
    assert [row['id'] for row in result['clues']] == ['member:unknown', 'member:hot', 'member:cold']
    assert result['clues'][2]['access_interval'] == [0.01, 0.02]
    assert result['clues'][2]['access_model'] == 'sigma'
    assert result['clues'][2]['access_compiled_j'] == 10
    assert result['clues'][2]['access_support'] == 3


def test_sample_is_bounded_deterministic_and_rotates_without_losing_structure():
    chats = [dict(id=f'member:{i:04}', kind='file', path=f'memory/codex/{i:04}.txt', text='chat')
             for i in range(1000)]
    project = [dict(id='member:system', kind='file', path='devDoc/system.md', text='system')]
    nodes = [dict(id='node:goal', kind='goal', text='goal')]
    select = lambda day: overview_working_set(chats + project, nodes, 6, chat_prefix='memory/codex', rotation=day)
    first = select('2026-11-17')
    assert len(first) == 48
    assert first == select('2026-11-17')
    assert {row['id'] for row in first} != {row['id'] for row in select('2026-11-18')}
    assert {'member:system', 'node:goal'} <= {row['id'] for row in first}
    assert len(overview_working_set(chats, [], 1000, chat_prefix='memory/codex', rotation='today')) == 96
    assert overview_working_set(chats, nodes, 0, chat_prefix='memory/codex', rotation='today') == []
