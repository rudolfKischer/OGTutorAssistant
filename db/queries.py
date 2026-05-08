"""Reusable query helpers for batched/grouped fetches."""

from sqlalchemy import select


def group_rows(conn, query, key_fn, val_fn=None):
    """Execute query and group results into a dict of lists.

    key_fn(row) -> grouping key
    val_fn(row) -> value to store (default: full row)
    """
    grouped = {}
    for row in conn.execute(query):
        key = key_fn(row)
        val = val_fn(row) if val_fn else row
        grouped.setdefault(key, []).append(val)
    return grouped


def batch_fetch(conn, table, word_ids, order_by=None, val_fn=None):
    """Fetch rows from a table filtered by word_ids, grouped by word_id."""
    query = select(table).where(table.c.word_id.in_(word_ids))
    if order_by:
        query = query.order_by(*order_by)
    return group_rows(conn, query, key_fn=lambda r: r.word_id, val_fn=val_fn)
