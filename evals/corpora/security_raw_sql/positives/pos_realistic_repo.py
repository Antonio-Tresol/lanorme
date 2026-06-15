"""Realistic repo module mixing several raw-SQL shapes.

This file imitates a real ``user_repository.py``-style module: a constant for a
hot query, a couple of one-off SELECTs, an admin maintenance DELETE, and a
search method that interpolates a search term. Each highlighted line is raw
SQL by the working definition.
"""

from __future__ import annotations

from sqlalchemy import text

USER_BY_EMAIL_SQL = "SELECT id, email, role FROM users WHERE email = '%s'"


class UserRepo:
    def __init__(self, engine):
        self.engine = engine

    def by_email(self, email):
        with self.engine.connect() as conn:
            return conn.execute(text(USER_BY_EMAIL_SQL % email)).first()

    def admin_count(self):
        with self.engine.connect() as conn:
            return conn.execute(text("SELECT COUNT(*) FROM users WHERE role = 'admin'")).scalar()

    def search(self, term):
        with self.engine.connect() as conn:
            sql = f"SELECT id, email FROM users WHERE email LIKE '%{term}%'"
            return conn.execute(text(sql)).all()

    def purge_inactive(self):
        with self.engine.begin() as conn:
            conn.execute(text("DELETE FROM users WHERE last_login < '2018-01-01'"))

    def reset_failed_attempts(self):
        with self.engine.begin() as conn:
            conn.execute(text("UPDATE users SET failed_attempts = 0"))
