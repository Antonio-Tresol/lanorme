"""Alembic revision script -- raw SQL is the EXPECTED idiom here.

Alembic upgrade/downgrade bodies use ``op.execute("...")`` with hand-written
DDL because schema migrations are review-gated artefacts; the SEC-002 rule
is meant to skip files under ``alembic/versions/``.
"""

from __future__ import annotations

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT NOT NULL)")
    op.execute("CREATE INDEX idx_users_email ON users (email)")
    op.execute("INSERT INTO users (id, email) VALUES (1, 'root@example.com')")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_users_email")
    op.execute("DROP TABLE IF EXISTS users")
