# why: negative - two state-transition guards comparing distinct enum members; the allowed state pairs carry the whole rule and use different enum types, so merging would erase the rules.
def can_transition_order(current, target):
    if current is OrderState.DRAFT and target is OrderState.PLACED:
        return True
    if current is OrderState.PLACED and target is OrderState.SHIPPED:
        return True
    if current is OrderState.SHIPPED and target is OrderState.DELIVERED:
        return True
    if current is OrderState.DELIVERED and target is OrderState.CLOSED:
        return True
    return False


def can_transition_ticket(current, target):
    if current is TicketState.OPEN and target is TicketState.TRIAGED:
        return True
    if current is TicketState.TRIAGED and target is TicketState.IN_PROGRESS:
        return True
    if current is TicketState.IN_PROGRESS and target is TicketState.RESOLVED:
        return True
    if current is TicketState.RESOLVED and target is TicketState.CLOSED:
        return True
    return False
