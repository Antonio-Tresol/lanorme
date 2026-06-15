"""``cursor.executemany("...", seq)`` where the SQL is built unsafely.

Batched DB writes. The positives here are the unsafe shape: either the table
name / WHERE clause is interpolated into the SQL body (bypassing parameter
binding), or the call drops the params seq entirely and embeds values inline.
"""

from __future__ import annotations


def bulk_insert_into(conn, table, rows):
    cur = conn.cursor()
    cur.executemany(f"INSERT INTO {table} (address, verified) VALUES (?, ?)", rows)
    conn.commit()


def bulk_update_status_in(conn, table, rows):
    cur = conn.cursor()
    cur.executemany(f"UPDATE {table} SET status = ? WHERE id = ?", rows)
    conn.commit()


def bulk_delete_inline(conn, ids):
    cur = conn.cursor()
    for ident in ids:
        cur.executemany(f"DELETE FROM cache WHERE key = '{ident}'", [()])
    conn.commit()


def bulk_insert_tags_format(conn, schema, pairs):
    cur = conn.cursor()
    cur.executemany(
        "INSERT INTO {}.tags (post_id, label) VALUES (%s, %s)".format(schema),
        pairs,
    )
    conn.commit()


def bulk_set_locale_concat(conn, table, rows):
    cur = conn.cursor()
    cur.executemany("UPDATE " + table + " SET locale = ? WHERE id = ?", rows)
    conn.commit()
