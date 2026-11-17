from math import exp, sqrt

import pytest

from basepack.memory.behavior_model import influence_bounds, kernel, mass_score, train_model


@pytest.fixture
def geometry():
    return {"vectors": {"a": [1.0, 0.0], "b": [0.0, 1.0],
                        "both": [1 / sqrt(2), 1 / sqrt(2)]}}


def test_gaussian_mixes_kernels_per_anchor_and_keeps_positive_tail(geometry):
    beta = .2
    tail = exp(-1 / beta)
    assert kernel(geometry, "a", "b", beta) == pytest.approx(tail)
    assert influence_bounds(geometry, "a", {"a": .5, "b": .5}, beta) == pytest.approx(
        ((1 + tail) / 2, (1 + tail) / 2))
    assert kernel(geometry, "a", "both", beta) != pytest.approx((1 + tail) / 2)
    assert mass_score(geometry, "a", {"a": 2, "b": 3}, beta) == pytest.approx(2 + 3 * tail)


def test_unknown_anchor_share_is_not_renormalized(geometry):
    assert influence_bounds(geometry, "a", {"a": .25, "unknown": .75}, .2) == pytest.approx((.25, 1))
    assert influence_bounds(geometry, "unknown", {"a": 1}, .2) == (0, 1)
    assert influence_bounds(geometry, "a", {}, .2) == (0, 1)
    with pytest.raises(ValueError):
        influence_bounds(geometry, "a", {"a": .9}, .2)
    with pytest.raises(ValueError):
        influence_bounds(geometry, "a", {"a": float("nan")}, .2)


def test_lazy_anchor_mass_equals_per_event_age(geometry):
    events = [{"a": .5, "b": .5}, {"a": .4, "missing": .6}, {}, {"b": 1}]
    epsilon, beta = .001, .2
    lower = upper = 0
    mass = {}
    missing = 0
    for anchors in events:
        lo, hi = influence_bounds(geometry, "a", anchors, beta)
        lower += epsilon + (1 - epsilon) * lo
        upper += epsilon + (1 - epsilon) * hi
        known_mass = 0
        for anchor, share in anchors.items():
            if anchor in geometry["vectors"]:
                mass[anchor] = mass.get(anchor, 0) + share
                known_mass += share
        missing += 1 - known_mass
    lazy_lower = epsilon * len(events) + (1 - epsilon) * mass_score(geometry, "a", mass, beta)
    assert lazy_lower == pytest.approx(lower)
    assert lazy_lower + (1 - epsilon) * missing == pytest.approx(upper)


def test_training_is_pure_basket_support_and_repeatable():
    pytest.importorskip("sklearn")
    data = [["a", "b", "b"], ["a", "b"], ["a", "c"], ["singleton"], []]
    first = train_model(data)
    second = train_model(data)
    assert first == second
    assert first["support"] == {"a": 3, "b": 2, "c": 1, "singleton": 0}
    assert set(first["vectors"]) == {"a", "b", "c"}
    assert first["training"]["basket_count"] == 3
    assert first["training"]["distinct_baskets"] == 2
    assert first["training"]["solver_rank"] == 2
    assert all(sum(value * value for value in vector) == pytest.approx(1)
               for vector in first["vectors"].values())
    cold = train_model([["singleton"]])
    assert cold["vectors"] == {}
    assert cold["support"] == {"singleton": 0}


def test_training_matrix_keeps_frequency_and_basket_mass(monkeypatch):
    decomposition = pytest.importorskip("sklearn.decomposition")
    original = decomposition.NMF
    matrices = []

    class CaptureNMF(original):
        def fit_transform(self, matrix, *args, **kwargs):
            matrices.append(matrix.toarray())
            return super().fit_transform(matrix, *args, **kwargs)

    monkeypatch.setattr(decomposition, "NMF", CaptureNMF)
    train_model([["a", "b"], ["a", "b"], ["b", "c", "d"], ["a"]])
    # Sorted basket and ID order; zero entries are part of the KL objective.
    assert matrices[0].tolist() == [[1, 1, 0, 0], [0, 1/3, 1/3, 1/3]]
