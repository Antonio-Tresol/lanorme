# why: negative - two DTO mappers projecting unrelated domains (user vs invoice) into a shared response envelope; the keys are a fixed output schema while the per-field source attributes carry the distinct domain meaning, so no single helper extracts cleanly.
def map_user_to_envelope(user):
    out = {}
    out["id"] = user.account_id
    out["label"] = user.display_name
    out["amount"] = user.lifetime_spend
    out["status"] = user.membership_state
    out["timestamp"] = user.last_seen_at
    return out


def map_invoice_to_envelope(invoice):
    out = {}
    out["id"] = invoice.document_number
    out["label"] = invoice.line_description
    out["amount"] = invoice.gross_total
    out["status"] = invoice.settlement_state
    out["timestamp"] = invoice.issued_at
    return out
