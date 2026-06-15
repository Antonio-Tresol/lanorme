"""Test assertions that compare GENERATED SQL strings to expected strings.

When a project tests its query-builder layer, the expected SQL appears as a
string literal in the test -- but the literal is the assertion target, not a
runtime payload. It is never handed to a DB.
"""

from __future__ import annotations


def compile_active_users():
    return "SELECT id, email FROM users WHERE active = 1"


def compile_admin_count():
    return "SELECT COUNT(*) FROM users WHERE role = 'admin'"


def test_active_users_sql():
    assert compile_active_users() == "SELECT id, email FROM users WHERE active = 1"


def test_admin_count_sql():
    expected = "SELECT COUNT(*) FROM users WHERE role = 'admin'"
    assert compile_admin_count() == expected


def test_update_clause_renders():
    rendered = "UPDATE orders SET archived = 1 WHERE id = :id"
    assert ":id" in rendered
    assert rendered.startswith("UPDATE orders")


def test_delete_clause_contains_table():
    sql = "DELETE FROM sessions WHERE expires_at < :cutoff"
    assert "sessions" in sql
