"""F-string and ``%`` interpolation building SQL handed to a DB execute call.

These are the dangerous shape: the SQL string is assembled by interpolating
Python values into the statement body, which bypasses parameter binding and
opens the door to injection. The execution call is the labelled line.
"""

from __future__ import annotations


def find_by_email(conn, email):
    cur = conn.cursor()
    cur.execute(f"SELECT id FROM users WHERE email = '{email}'")
    return cur.fetchone()


def delete_by_id(conn, user_id):
    conn.execute(f"DELETE FROM users WHERE id = {user_id}")


def list_in_status(conn, status):
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM orders WHERE status = '%s'" % status)
    return cur.fetchall()


def format_filter(conn, column, value):
    cur = conn.cursor()
    cur.execute("SELECT * FROM widgets WHERE {} = '{}'".format(column, value))
    return cur.fetchall()


def update_role(conn, user_id, role):
    conn.execute(f"UPDATE users SET role = '{role}' WHERE id = {user_id}")


def search_prefix(conn, prefix):
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM items WHERE name LIKE '{prefix}%'")
    return cur.fetchall()
