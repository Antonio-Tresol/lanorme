"""Raw SQL stored in a module/local constant and then executed.

The pattern in dashboards and report modules: pull the SQL out into a named
constant for readability, then ``.execute(SQL)`` later. Both the constant
definition and the execute call are raw SQL surfaces, but per our working
definition we label the EXECUTION line -- the constant alone never reaches the
DB.
"""

from __future__ import annotations

from sqlalchemy import text

ACTIVE_USERS_SQL = "SELECT id, email FROM users WHERE active = 1 AND deleted_at IS NULL"

REVENUE_BY_DAY_SQL = """
    SELECT date_trunc('day', paid_at) AS day, SUM(amount) AS total
    FROM payments
    WHERE status = 'captured'
    GROUP BY 1
"""

DELETE_STALE_SESSIONS = "DELETE FROM sessions WHERE expires_at < NOW()"


def active_users(engine):
    with engine.connect() as conn:
        return conn.execute(text(ACTIVE_USERS_SQL)).all()


def revenue_by_day(engine):
    with engine.connect() as conn:
        return conn.execute(text(REVENUE_BY_DAY_SQL)).all()


def purge_sessions(conn):
    cur = conn.cursor()
    cur.execute(DELETE_STALE_SESSIONS)
    conn.commit()


def disable_account(conn):
    cur = conn.cursor()
    cur.execute("UPDATE users SET disabled = 1 WHERE last_login < '2019-01-01'")
    conn.commit()
