"""Multi-line triple-quoted SQL string passed to ``.execute(...)``.

Real reporting queries are often kept as multi-line triple-quoted strings for
readability. They are still raw SQL when handed to the engine: the entire
statement body is hand-written Python source.
"""

from __future__ import annotations

from sqlalchemy import text


def monthly_revenue(engine):
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT date_trunc('month', paid_at) AS month, SUM(amount) AS total
            FROM payments
            WHERE status = 'captured'
            GROUP BY 1
            ORDER BY 1
        """))
        return rows.all()


def churn_cohort(engine):
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT cohort, COUNT(*) AS churned
            FROM user_cohorts
            WHERE last_seen_at < NOW() - INTERVAL '90 days'
            GROUP BY cohort
        """))
        return rows.all()


def top_referrers(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT referrer, COUNT(*) AS hits
        FROM page_views
        GROUP BY referrer
        ORDER BY hits DESC
        LIMIT 25
    """)
    return cur.fetchall()


def bulk_archive(conn):
    cur = conn.cursor()
    cur.execute("""
        DELETE FROM events
        WHERE created_at < NOW() - INTERVAL '180 days'
          AND archived = 1
    """)
    conn.commit()
