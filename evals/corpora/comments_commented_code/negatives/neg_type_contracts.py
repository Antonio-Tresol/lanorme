"""Type/contract documentation comments (parameter shapes, returns, raises)."""

from __future__ import annotations


def fit(matrix, labels):
    # matrix: ndarray of shape (n_samples, n_features), dtype float32
    # labels: 1-D ndarray of int64, length n_samples
    # returns: trained Model instance, never None
    # raises: ValueError if matrix has fewer than 2 samples
    return Model()


class Model:
    pass


def parse(spec):
    # spec: str matching the grammar  expr := term ("+" term)*
    # returns: (ast.Node, remaining: str)
    return (None, spec)


def callback(fn):
    # fn: Callable[[int, str], bool]
    # invariant: fn must be pure; we may call it concurrently
    return fn
