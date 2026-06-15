"""SQLAlchemy ``text(...)`` wrapping a raw SQL statement with no bound params.

Each call here passes a hand-written SQL string straight into the engine via
``text(...)`` with no parameter binding -- the SQL body is the entire payload,
which is the canonical raw-SQL pattern this rule targets.
"""

from __future__ import annotations

from sqlalchemy import text


def list_active_users(engine):
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT id, email FROM users WHERE active = 1"))
        return rows.all()


def drop_temp_table(engine):
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS scratch_2024"))


def count_invoices(engine):
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM invoices"))
        return result.scalar()


def alter_users_add_locale(engine):
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE users ADD COLUMN locale VARCHAR(8) DEFAULT 'en'"))


def truncate_staging(engine):
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE staging_events"))


def vacuum_full(engine):
    with engine.connect() as conn:
        conn.execute(text("VACUUM FULL ANALYZE invoices"))
