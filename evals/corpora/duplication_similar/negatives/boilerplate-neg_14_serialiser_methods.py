# why: negative - two to_dict serialisers over different models; the selected fields and key names define each public payload, so the parallel assignments are the contract not a clone.
def serialise_account(account):
    data = {}
    data["id"] = account.id
    data["owner"] = account.owner_name
    data["balance"] = account.balance
    data["currency"] = account.currency
    data["tier"] = account.tier
    data["is_overdrawn"] = account.balance < 0
    return data


def serialise_subscription(subscription):
    data = {}
    data["id"] = subscription.id
    data["plan"] = subscription.plan_name
    data["seats"] = subscription.seat_count
    data["interval"] = subscription.billing_interval
    data["status"] = subscription.status
    data["is_trial"] = subscription.trial_ends_at is not None
    return data
