# why: negative - two field mappers translating distinct external API shapes onto our model; the attribute and key names are the actual logic, so the parallel assignments are meaningful not clonable.
def map_stripe_charge(payload):
    record = {}
    record["external_id"] = payload["id"]
    record["amount"] = payload["amount"] / 100
    record["currency"] = payload["currency"].upper()
    record["status"] = payload["status"]
    record["captured"] = payload["captured"]
    record["created_at"] = payload["created"]
    return record


def map_paypal_payment(payload):
    record = {}
    record["external_id"] = payload["transaction_id"]
    record["amount"] = float(payload["gross_amount"])
    record["currency"] = payload["currency_code"]
    record["status"] = payload["state"]
    record["captured"] = payload["is_final_capture"]
    record["created_at"] = payload["create_time"]
    return record
