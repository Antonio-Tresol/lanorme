# why: negative - two field mappers where the keys and source attributes carry the meaning; parallel shape is intentional DTO boilerplate, not an extractable clone.
def map_user_to_dto(user):
    dto = {}
    dto["id"] = user.pk
    dto["display"] = user.full_name
    dto["email"] = user.contact_email
    dto["active"] = user.is_enabled
    dto["joined"] = user.created_at
    return dto


def map_invoice_to_dto(invoice):
    dto = {}
    dto["id"] = invoice.number
    dto["total"] = invoice.gross_amount
    dto["currency"] = invoice.iso_code
    dto["paid"] = invoice.settled
    dto["due"] = invoice.due_date
    return dto
