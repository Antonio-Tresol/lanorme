# why: negative - two row mappers into a shared report schema, each applying a str() coercion per field but over unrelated domains (sensor reading vs ledger entry); the keys and the coercion are common formatting while the per-field source columns carry the real meaning, so no helper extracts cleanly.
def map_sensor_row(reading):
    row = {}
    row["id"] = str(reading.device_serial)
    row["primary"] = str(reading.temperature_c)
    row["secondary"] = str(reading.humidity_pct)
    row["flag"] = str(reading.is_calibrated)
    row["when"] = str(reading.sampled_at)
    return row


def map_ledger_row(entry):
    row = {}
    row["id"] = str(entry.transaction_ref)
    row["primary"] = str(entry.debit_amount)
    row["secondary"] = str(entry.credit_amount)
    row["flag"] = str(entry.is_reconciled)
    row["when"] = str(entry.posted_at)
    return row
