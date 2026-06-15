# why: negative - two FastAPI endpoint handlers over different resources; the route shape is framework boilerplate but each touches a distinct repository and response model.
async def get_user(user_id, session, current_user):
    repo = UserRepository(session)
    entity = await repo.find_by_id(user_id)
    if entity is None:
        raise NotFoundError("user not found")
    if entity.owner_id != current_user.id:
        raise ForbiddenError("not permitted")
    return UserResponse.from_entity(entity)


async def get_invoice(invoice_id, session, current_user):
    repo = InvoiceRepository(session)
    entity = await repo.find_by_id(invoice_id)
    if entity is None:
        raise NotFoundError("invoice not found")
    if entity.account_id != current_user.account_id:
        raise ForbiddenError("not permitted")
    return InvoiceResponse.from_entity(entity)
