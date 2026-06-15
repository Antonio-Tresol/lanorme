# why: negative - identical control-flow skeleton but the identifiers carry all the meaning; one paginates an API, the other walks a binary tree, no shared helper exists.
def fetch_all_pages(api, query):
    results = []
    seen = 0
    cursor = api.first(query)
    while cursor is not None:
        page = api.load(cursor)
        results.extend(page.items)
        cursor = page.next_cursor
    return results


def inorder_traverse(tree, target):
    results = []
    seen = 0
    cursor = tree.root
    while cursor is not None:
        page = tree.visit(cursor)
        results.extend(page.children)
        cursor = page.successor
    return results
