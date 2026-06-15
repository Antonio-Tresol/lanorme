# why: negative - two ORM table column-spec builders; each lists the real columns of a different table, so the parallel append calls are schema definitions whose strings are the meaning.
def define_users_columns(table):
    table.add_column("id", "uuid", primary_key=True)
    table.add_column("email", "varchar", unique=True)
    table.add_column("display_name", "varchar", nullable=True)
    table.add_column("is_active", "boolean", default=True)
    table.add_column("created_at", "timestamp", nullable=False)
    return table


def define_orders_columns(table):
    table.add_column("id", "uuid", primary_key=True)
    table.add_column("reference", "varchar", unique=True)
    table.add_column("notes", "text", nullable=True)
    table.add_column("is_paid", "boolean", default=False)
    table.add_column("placed_at", "timestamp", nullable=False)
    return table
