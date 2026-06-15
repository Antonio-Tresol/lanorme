# why: negative - same gate shape but one requires all conditions (and) and the other any condition (or); the boolean operator change inverts the access policy, no shared helper.
def can_edit(user, doc):
    active = user.is_active
    owns = user.id == doc.owner_id
    draft = doc.status == "draft"
    fresh = doc.updated_at is not None
    allowed = active and owns and draft and fresh
    return allowed


def can_view(user, doc):
    active = user.is_active
    owns = user.id == doc.owner_id
    public = doc.status == "public"
    shared = doc.shared_with is not None
    allowed = active or owns or public or shared
    return allowed
