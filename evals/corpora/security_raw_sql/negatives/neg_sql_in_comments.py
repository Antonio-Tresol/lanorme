"""SQL syntax appearing inside ``#`` comments -- prose, never executed.

Developers often paste the equivalent SQL into a comment next to the ORM
code that produces it, or write TODOs that mention SQL operations. None of
these are runtime payloads.
"""

from __future__ import annotations


def list_users(session):
    # Equivalent SQL: SELECT id, email FROM users WHERE active = 1
    return session.query("User").filter("active").all()


def archive_orders(session):
    # TODO: replace with bulk UPDATE orders SET archived = 1 once the
    # background job is in place.
    for order in session.query("Order").all():
        order.archived = True


def purge_sessions(cache):
    # Effectively a DELETE FROM sessions WHERE expires_at < NOW(), but on
    # the in-memory cache, not the DB.
    cache.purge()


def revenue_view():
    # The view materialises SELECT day, SUM(amount) FROM payments GROUP BY day.
    return "v_revenue"


def reindex_hint():
    # Run CREATE INDEX idx_orders_user ON orders (user_id) during the next window.
    pass
