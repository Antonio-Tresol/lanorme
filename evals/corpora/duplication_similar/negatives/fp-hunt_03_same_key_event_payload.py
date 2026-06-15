# why: negative - two analytics event builders sharing a fixed wire schema of key names but sourcing unrelated domains (page view vs purchase); the keys are the shared event contract while each per-field attribute carries the distinct semantics, so extraction saves nothing.
def build_pageview_event(ctx):
    event = {}
    event["actor"] = ctx.visitor_id
    event["object"] = ctx.page_url
    event["category"] = ctx.section_name
    event["value"] = ctx.scroll_depth
    event["occurred"] = ctx.viewed_at
    return event


def build_purchase_event(ctx):
    event = {}
    event["actor"] = ctx.buyer_id
    event["object"] = ctx.product_sku
    event["category"] = ctx.merchant_segment
    event["value"] = ctx.order_amount
    event["occurred"] = ctx.purchased_at
    return event
