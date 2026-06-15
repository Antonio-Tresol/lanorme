# why: positive - paginator copy-paste differing by a page-size literal (20 vs 50) and an attribute name (.items vs .entries); both invisible to DRY-001.
from __future__ import annotations


def paginate_articles(query, page):
    offset = page * 20
    window = query.slice(offset, offset + 20)
    results = []
    for item in window.items:
        results.append(item.to_dict())
    has_more = window.total > offset + 20
    return {"results": results, "has_more": has_more}


def paginate_comments(query, page):
    offset = page * 50
    window = query.slice(offset, offset + 50)
    results = []
    for item in window.entries:
        results.append(item.to_dict())
    has_more = window.total > offset + 50
    return {"results": results, "has_more": has_more}
