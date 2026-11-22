"""Synthetic nominations exercise version, scope, and review receipts without a database."""

from copy import deepcopy

import pytest

from basepack.memory.graph_maintenance import nominate


class DeliveryFacts:
    def __init__(self, *events):
        self.events = events
        self.queries = []

    def _execute(self, query):
        self.queries.append(query)
        return [self.events]


def member(name, **overrides):
    return {"id": f"member:{name}", "path": f"{name}.md", "kind": "chunk", "knowledge_revision": "current",
            "source_revision": f"digest-{name}", "source_version": f"source_version:{name}", "start_line": 2,
            "end_line": 2, "stale": False, "retired": False, "text": "Local source prose", **overrides}


def sources(*members):
    return {row["path"]: {"path": row["path"], "version": row["source_version"], "revision": row["source_revision"]}
            for row in members}


def pin(row):
    return {"member": row["id"], "knowledge_revision": row["knowledge_revision"], "source_version": row["source_version"]}


def confirmed(j, *members):
    return {"j": j, "items": [{"id": row["id"], "knowledge_revision": row["knowledge_revision"]} for row in members]}


def ids(pair):
    return [row["id"] for row in pair["endpoints"]]


def test_records_confirmed_exact_co_delivery_and_reserves_one_random_slot():
    a = member("aa", private=False)
    b = member("bb")
    c = member("cc")
    d = member("dd")
    available = sources(a, b, c, d)
    available[b["path"]]["private"] = True
    facts = DeliveryFacts(confirmed(9, a, b), confirmed(10, {**a, "id": "member:`aa`"}, b))

    result = nominate(facts, members=[d, b, c, a], eligible_sources=available)
    assert result == nominate(DeliveryFacts(*reversed(facts.events)), members=[a, c, b, d],
                              eligible_sources=dict(reversed(list(available.items()))))
    assert len(result) == 2
    assert ids(result[0]) == [a["id"], b["id"]]
    assert result[0]["signals"] == ["co_delivery"]
    assert result[0]["delivery_events"] == [9, 10]
    assert result[1]["signals"] == ["random"]
    assert "delivery_events" not in result[1]
    assert result[0]["id"].startswith("pair:") and len(result[0]["id"]) == 69
    assert [row["private"] for row in result[0]["endpoints"]] == [False, True]
    assert all("text" not in row and "basis" not in row for pair in result for row in pair["endpoints"])
    assert all("private" not in row for row in result[1]["endpoints"] if row["id"] in {c["id"], d["id"]})
    assert len(facts.queries) == 1
    assert "SELECT j,items FROM delivery" in facts.queries[0]
    assert "j >= 1 AND legacy != true" in facts.queries[0] and "LIMIT 256" in facts.queries[0]


def test_repeated_confirmation_of_one_j_and_stale_observed_versions_do_not_make_co_delivery():
    a, b = member("aa"), member("bb")
    old_b = {**b, "knowledge_revision": "old"}
    repeated = confirmed(5, a, b, b)
    facts = DeliveryFacts(repeated, repeated, confirmed(6, a, old_b))
    result = nominate(facts, members=[a, b], eligible_sources=sources(a, b), limit=1)
    assert len(result) == 1
    assert result[0]["signals"] == ["random"]


def test_basis_does_not_nominate_or_prioritize_a_pair():
    a, b, c = member("aa"), member("bb"), member("cc")
    facts = DeliveryFacts()
    before = nominate(facts, members=[a, b, c], eligible_sources=sources(a, b, c))
    a["basis"] = [pin(b), pin(c)]
    b["basis"] = [pin(c)]
    after = nominate(facts, members=[a, b, c], eligible_sources=sources(a, b, c))
    assert before == after
    [exploratory] = after
    assert exploratory["signals"] == ["random"]
    assert "delivery_events" not in exploratory


def test_ineligible_versions_sources_and_identical_originals_never_nominate():
    a = member("aa")
    other_span = {**a, "id": "member:aa-second", "start_line": 8, "end_line": 8}
    same_bytes = member("duplicate", source_revision=a["source_revision"])
    good = member("bb")
    stale = member("stale", stale=True)
    retired = member("retired", retired=True)
    old_file = member("old_file")
    old_snapshot = member("old_snapshot")
    outside = member("outside")
    rows = [a, other_span, same_bytes, good, stale, retired, old_file, old_snapshot, outside]
    allowed = sources(*rows[:-1])
    allowed[old_file["path"]]["revision"] = "updated"
    allowed[old_snapshot["path"]]["version"] = "source_version:new_snapshot"

    result = nominate(DeliveryFacts(confirmed(1, *rows), confirmed(2, *rows)), members=rows,
                      eligible_sources=allowed)
    assert result and ids(result[0]) == [a["id"], good["id"]]
    assert all(good["id"] in ids(pair) for pair in result)
    assert {v for pair in result for v in ids(pair)} <= {a["id"], other_span["id"], same_bytes["id"], good["id"]}


@pytest.mark.parametrize("change", [{"knowledge_revision": "k2"}, {"source_version": "source_version:bb2"}])
def test_reviewed_ids_skip_exact_pair_and_a_changed_pin_can_be_new(change):
    a, b = member("aa"), member("bb")
    facts = DeliveryFacts(confirmed(1, a, b), confirmed(2, a, b))
    fresh = nominate(facts, members=[b, a], eligible_sources=sources(a, b), limit=1)
    reviewed_ids = [fresh[0]["id"]]
    assert nominate(facts, members=[a, b], eligible_sources=sources(a, b),
                    reviewed=iter(reviewed_ids)) == []

    changed = {**b, **change}
    facts = DeliveryFacts(confirmed(3, a, changed), confirmed(4, a, changed))
    result = nominate(facts, members=[a, changed], eligible_sources=sources(a, changed), reviewed=reviewed_ids)
    assert len(result) == 1
    assert result[0]["id"] != reviewed_ids[0]
    assert result[0]["signals"] == ["co_delivery"]
    assert result[0]["delivery_events"] == [3, 4]


def test_budget_one_keeps_a_strong_clue_and_no_possible_pair_requires_no_query():
    a, b, c = member("aa"), member("bb"), member("cc")
    memory = DeliveryFacts(confirmed(1, a, b), confirmed(2, a, b), confirmed(3, a, c), confirmed(4, a, c),
                           confirmed(5, a, c))
    result = nominate(memory, members=[c, b, a], eligible_sources=sources(a, b, c), limit=1)
    assert len(result) == 1 and ids(result[0]) == [a["id"], c["id"]]
    assert result[0]["signals"] == ["co_delivery"]
    assert result[0]["delivery_events"] == [3, 4, 5]

    unopened = DeliveryFacts()
    assert nominate(unopened, members=[a, b], eligible_sources=sources(a), limit=0) == []
    assert nominate(unopened, members=[a, b], eligible_sources=sources(a)) == []
    assert not unopened.queries


def test_deliveries_have_a_bounded_basket_before_pair_expansion():
    rows = [member(f"item_{index:02}") for index in range(13)]
    facts = DeliveryFacts(confirmed(2, *rows), confirmed(1, *reversed(rows)))
    result = nominate(facts, members=deepcopy(rows), eligible_sources=sources(*rows), limit=70)
    confirmed_pairs = [pair for pair in result if "co_delivery" in pair["signals"]]
    assert len(confirmed_pairs) == 66
    assert all(rows[-1]["id"] not in ids(pair) for pair in confirmed_pairs)
    assert len(result) == 67
