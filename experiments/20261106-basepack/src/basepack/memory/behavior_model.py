"""Pure co-delivery representation and Gaussian opportunity geometry.

The serialized model contains no content, query, ranking, or access scores.
Only ``train_model`` needs the optional numerical dependencies.
"""

from collections import Counter
from math import exp, fsum, isclose, isfinite


def train_model(deliveries, rank=8):
    """Fit a frequency-faithful, unregularized KL-NMF to logical-ID baskets.

    Empty/singleton baskets provide no co-delivery evidence. Support counts
    real deliveries with at least one different partner, not distinct baskets.
    """
    if not isinstance(rank, int) or isinstance(rank, bool) or rank < 1:
        raise ValueError("rank must be a positive integer")
    baskets = Counter()
    support = Counter()
    for delivery in deliveries:
        if isinstance(delivery, str):
            raise ValueError("delivery must be a collection of logical IDs")
        basket = tuple(sorted(set(delivery)))
        if any(not isinstance(item, str) or not item for item in basket):
            raise ValueError("logical IDs must be nonempty strings")
        for item in basket:
            support[item] += 0
        if len(basket) >= 2:
            baskets[basket] += 1
            support.update(basket)

    model = {
        "vectors": {},
        "support": dict(sorted(support.items())),
        "training": {
            "requested_rank": rank,
            "effective_rank": 0,
            "basket_count": sum(baskets.values()),
            "distinct_baskets": len(baskets),
            "solver": "mu",
            "beta_loss": "kullback-leibler",
            "init": "random",
            "random_state": 0,
            "tol": 1e-4,
            "max_iter": 500,
            "alpha_W": 0.0,
            "alpha_H": 0.0,
            "row_norm_floor": 1e-12,
        },
    }
    if not baskets:
        return model

    import numpy as np
    import scipy
    from scipy.sparse import csr_matrix
    import sklearn
    from sklearn.decomposition import NMF

    items = sorted(item for item, count in support.items() if count)
    indices = {item: i for i, item in enumerate(items)}
    rows, cols, values = [], [], []
    for row, (basket, count) in enumerate(sorted(baskets.items())):
        for item in basket:
            rows.append(row)
            cols.append(indices[item])
            values.append(count / len(basket))
    x = csr_matrix((values, (rows, cols)), shape=(len(baskets), len(items)), dtype=np.float64)
    actual_rank = min(rank, *x.shape)
    estimator = NMF(n_components=actual_rank, init="random", solver="mu",
                    beta_loss="kullback-leibler", random_state=0,
                    tol=1e-4, max_iter=500, alpha_W=0.0, alpha_H=0.0)
    a = estimator.fit_transform(x)
    z = estimator.components_.T.copy()
    if not (np.isfinite(a).all() and np.isfinite(z).all() and
            (a >= 0).all() and (z >= 0).all()):
        raise ValueError("NMF returned invalid factors")
    norms = np.linalg.norm(z, axis=0)
    nonzero = norms > 0.0
    z = z[:, nonzero]
    a = a[:, nonzero]
    norms = norms[nonzero]
    z /= norms
    a *= norms  # Preserve A Z^T under the column rescaling.
    row_norms = np.linalg.norm(z, axis=1)
    for item, vector, norm in zip(items, z, row_norms, strict=True):
        if norm > model["training"]["row_norm_floor"]:
            model["vectors"][item] = (vector / norm).tolist()
    model["training"].update({
        "effective_rank": int(nonzero.sum()),
        "solver_rank": actual_rank,
        "iterations": int(estimator.n_iter_),
        "reconstruction_error": float(estimator.reconstruction_err_),
        "numpy_version": np.__version__,
        "scipy_version": scipy.__version__,
        "sklearn_version": sklearn.__version__,
    })
    return model


def _vector(model, item):
    vector = model["vectors"][item]
    if not vector or any(not isfinite(x) or x < 0 for x in vector):
        raise ValueError("invalid behavior vector")
    if not isclose(fsum(x*x for x in vector), 1, abs_tol=1e-8):
        raise ValueError("behavior vectors must have unit norm")
    return vector


def kernel(model, item, anchor, beta):
    """Evaluate the Gaussian kernel for two known, same-snapshot vectors."""
    if not isfinite(beta) or beta <= 0:
        raise ValueError("beta must be finite and positive")
    left = _vector(model, item)
    right = _vector(model, anchor)
    if len(left) != len(right):
        raise ValueError("incompatible behavior vectors")
    distance_sq = fsum((x-y)**2 for x, y in zip(left, right, strict=True))
    return exp(-distance_sq / (2 * beta))


def influence_bounds(model, item, anchors, beta):
    """Return the conservative influence interval for original anchor shares."""
    if not isfinite(beta) or beta <= 0:
        raise ValueError("beta must be finite and positive")
    if any(not isfinite(alpha) or alpha < 0 for alpha in anchors.values()):
        raise ValueError("anchor shares must be finite and nonnegative")
    if anchors and not isclose(fsum(anchors.values()), 1, abs_tol=1e-12):
        raise ValueError("nonempty anchor shares must sum to one")
    if item not in model["vectors"]:
        return (0.0, 1.0)
    _vector(model, item)
    known = [(anchor, alpha) for anchor, alpha in anchors.items()
             if anchor in model["vectors"]]
    lower = fsum(alpha * kernel(model, item, anchor, beta) for anchor, alpha in known)
    missing = 1.0 - fsum(alpha for _, alpha in known)
    return (lower, min(1.0, lower + max(0.0, missing)))


def mass_score(model, item, mass, beta):
    """Calculate g_i(H), without constructing an all-pairs kernel matrix."""
    if not isfinite(beta) or beta <= 0:
        raise ValueError("beta must be finite and positive")
    _vector(model, item)
    if any(not isfinite(value) or value < 0 for value in mass.values()):
        raise ValueError("anchor mass must be finite and nonnegative")
    return fsum(value * kernel(model, item, anchor, beta)
                for anchor, value in mass.items() if value)
