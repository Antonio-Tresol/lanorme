"""Second Alembic revision -- still under ``alembic/versions/``.

Same exemption applies; raw DDL via ``op.execute`` is the migration idiom.
"""

from __future__ import annotations

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN locale VARCHAR(8) DEFAULT 'en'")
    op.execute("UPDATE users SET locale = 'en' WHERE locale IS NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN locale")
