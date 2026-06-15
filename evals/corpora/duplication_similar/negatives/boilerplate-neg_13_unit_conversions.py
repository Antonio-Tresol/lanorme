# why: negative - two converters whose control flow genuinely diverges; one clamps an absolute-zero floor, the other rejects negatives and rounds differently, so neither factors into the other.
def fahrenheit_to_celsius(value):
    celsius = (value - 32.0) * 5.0 / 9.0
    if celsius < -273.15:
        raise ValueError("below absolute zero")
    rounded = round(celsius, 2)
    if rounded == -0.0:
        rounded = 0.0
    return rounded


def miles_to_kilometres(value):
    if value < 0:
        raise ValueError("distance cannot be negative")
    kilometres = value * 1.609344
    whole = int(kilometres)
    fraction = kilometres - whole
    if fraction >= 0.5:
        whole += 1
    return whole
