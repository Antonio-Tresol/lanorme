# why: negative - __eq__ guards type then compares a key tuple while __hash__ hashes that tuple; the equality/hashing contract pairs them by convention but their bodies do different things.
from __future__ import annotations


class Money:
    def __eq__(self, other):
        if not isinstance(other, Money):
            return NotImplemented
        left = (self.amount, self.currency)
        right = (other.amount, other.currency)
        if left != right:
            return False
        return True

    def __hash__(self):
        amount = self.amount
        currency = self.currency
        key = (amount, currency)
        digest = hash(key)
        salted = digest ^ 0x9E3779B9
        return salted
