# why: negative - identical accumulate shape but one folds with addition and the other with multiplication; running-sum and running-product are distinct operations, no shared helper.
def running_total(numbers):
    acc = 0
    seen = 0
    values = list(numbers)
    for number in values:
        if number is None:
            continue
        acc = acc + number
        seen += 1
    return acc


def running_product(numbers):
    acc = 1
    seen = 0
    values = list(numbers)
    for number in values:
        if number is None:
            continue
        acc = acc * number
        seen += 1
    return acc
