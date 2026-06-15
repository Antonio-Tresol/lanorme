"""Parameterized execute calls -- SQL string + separate bound-params payload.

These are the calls the rule's prescriptive text actively endorses: SQL with
``:name`` or ``?`` / ``%s`` placeholders, with the values passed as a
separate dict or tuple. The SQL body is hand-written, but the contract
between the driver and the SQL is intact (no value is concatenated in).
"""

from __future__ import annotations

from sqlalchemy import text


def user_by_id_sa(engine, user_id):
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT id, email FROM users WHERE id = :id"),
            {"id": user_id},
        ).first()


def update_status_sa(engine, order_id, status):
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE orders SET status = :status WHERE id = :id"),
            {"status": status, "id": order_id},
        )


def find_orders_dbapi(conn, user_id, since):
    cur = conn.cursor()
    cur.execute(
        "SELECT id, amount FROM orders WHERE user_id = %s AND created_at >= %s",
        (user_id, since),
    )
    return cur.fetchall()


def insert_event(conn, kind, payload):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO events (kind, payload) VALUES (?, ?)",
        (kind, payload),
    )
    conn.commit()


def bulk_insert_emails(conn, rows):
    cur = conn.cursor()
    cur.executemany(
        "INSERT INTO emails (address, verified) VALUES (?, ?)",
        rows,
    )
    conn.commit()
