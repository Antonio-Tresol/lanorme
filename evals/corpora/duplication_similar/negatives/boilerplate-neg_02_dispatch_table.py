# why: negative - two dispatch tables mapping distinct event names to distinct handlers; the string keys and target callables carry the meaning, so identical shape is not duplication.
def build_inbound_dispatch(handlers):
    table = {}
    table["order.created"] = handlers.on_order_created
    table["order.cancelled"] = handlers.on_order_cancelled
    table["order.shipped"] = handlers.on_order_shipped
    table["order.refunded"] = handlers.on_order_refunded
    table["order.delivered"] = handlers.on_order_delivered
    return table


def build_outbound_dispatch(handlers):
    table = {}
    table["payment.authorised"] = handlers.on_payment_authorised
    table["payment.captured"] = handlers.on_payment_captured
    table["payment.failed"] = handlers.on_payment_failed
    table["payment.disputed"] = handlers.on_payment_disputed
    table["payment.settled"] = handlers.on_payment_settled
    return table
