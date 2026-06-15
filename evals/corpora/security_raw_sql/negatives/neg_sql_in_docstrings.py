"""SQL syntax appearing inside docstrings -- never executed, never reaches DB.

Module, class, and function docstrings often quote example SQL to explain
what a Python helper produces. The triple-quoted text is documentation, not
a runtime payload.

Example:
    SELECT id, email FROM users WHERE active = 1
"""

from __future__ import annotations


def build_user_query(active=True):
    """Build a Python query expression for the active-users view.

    The generated SQL looks roughly like::

        SELECT id, email FROM users WHERE active = 1

    but is assembled by the ORM, not by string concatenation.
    """
    return ("active", active)


def explain_indexes():
    """Document the indexes the schema relies on.

    The reporting query::

        SELECT day, SUM(amount) FROM payments GROUP BY day

    is served by the ``idx_payments_day`` index.
    """
    return None


class OrderQuery:
    """Builder for order queries.

    Equivalent SQL::

        SELECT id, status FROM orders WHERE user_id = :uid

    The actual statement is produced by ``Order.__table__.select()``.
    """

    def __init__(self, user_id):
        self.user_id = user_id
