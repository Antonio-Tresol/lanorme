"""``pandas.read_sql`` / ``read_sql_query`` with a raw SQL literal.

Notebooks and ETL pipelines lean on ``pandas.read_sql``. The query string is
the same raw-SQL surface as ``conn.execute(...)``; if it is a hand-written
SELECT, label it.
"""

from __future__ import annotations

import pandas as pd


def revenue_frame(con):
    return pd.read_sql("SELECT day, total FROM revenue_daily ORDER BY day", con)


def churn_frame(con):
    return pd.read_sql_query(
        "SELECT cohort, churned FROM cohort_summary WHERE churned > 0",
        con,
    )


def user_table(con):
    df = pd.read_sql("SELECT id, email, created_at FROM users", con)
    return df


def filter_by_status(con, status):
    return pd.read_sql(f"SELECT id FROM orders WHERE status = '{status}'", con)


def join_payments(con):
    return pd.read_sql(
        """
        SELECT u.id, u.email, SUM(p.amount) AS total
        FROM users u JOIN payments p ON p.user_id = u.id
        GROUP BY u.id, u.email
        """,
        con,
    )
