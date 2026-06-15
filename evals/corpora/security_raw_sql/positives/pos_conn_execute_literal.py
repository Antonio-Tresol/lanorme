"""Direct ``conn.execute("...")`` / ``cursor.execute("...")`` with a bare SQL literal.

DB-API and ORM connections both accept a bare SQL string; passing a literal
string with no separate params dict is the classic raw-SQL call we want to
flag, regardless of whether the connection is psycopg2, sqlite3, or an
SQLAlchemy ``Connection``.
"""

from __future__ import annotations


def disable_old_accounts(conn):
    conn.execute("UPDATE accounts SET disabled = 1 WHERE last_login < '2020-01-01'")


def purge_sessions(conn):
    cur = conn.cursor()
    cur.execute("DELETE FROM sessions WHERE expires_at < NOW()")
    conn.commit()


def create_index(conn):
    conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_user ON orders (user_id)")


def get_total_revenue(conn):
    cur = conn.cursor()
    cur.execute("SELECT SUM(amount) FROM payments WHERE status = 'captured'")
    return cur.fetchone()[0]


def insert_default_role(conn):
    cur = conn.cursor()
    cur.execute("INSERT INTO roles (name, scope) VALUES ('viewer', 'global')")


def reset_counters(conn):
    cur = conn.cursor()
    cur.execute("UPDATE counters SET value = 0")
    conn.commit()
