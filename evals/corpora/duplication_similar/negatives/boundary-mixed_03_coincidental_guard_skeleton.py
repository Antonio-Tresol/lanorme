# why: negative - short coincidental match just over the floor; a balance debit and a circle-area calc happen to share a guard-compute-return skeleton from unrelated domains.
def debit_account(account, amount):
    if amount <= 0:
        raise ValueError("amount must be positive")
    if account.balance < amount:
        raise ValueError("insufficient funds")
    account.balance -= amount
    account.touched = True
    return account.balance


def circle_area(radius, precision):
    if radius <= 0:
        raise ValueError("radius must be positive")
    if precision < 1:
        raise ValueError("precision too low")
    area = 3.14159 * radius * radius
    rounded = round(area, precision)
    return rounded
