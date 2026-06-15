# why: positive - two field validators copy-pasted then drifted by a different attribute name and one reordered guard; reviewer would extract a shared range-check helper.
def validate_temperature(reading):
    if reading.value is None:
        raise ValueError("missing")
    if reading.value < -40:
        raise ValueError("too low")
    if reading.value > 120:
        raise ValueError("too high")
    reading.checked = True
    return reading


def validate_pressure(reading):
    if reading.amount is None:
        raise ValueError("missing")
    if reading.amount > 120:
        raise ValueError("too high")
    if reading.amount < -40:
        raise ValueError("too low")
    reading.checked = True
    return reading
