# why: negative - two computed-price properties share a getter shape but apply different arithmetic semantics (tax-inclusive total vs tiered discount); the pricing rules are the content.
from __future__ import annotations


class LineItem:
    unit_price: float
    quantity: int
    tax_rate: float
    discount_tier: int

    @property
    def total_price(self):
        gross = self.unit_price * self.quantity
        tax = gross * self.tax_rate
        total = gross + tax
        rounded = round(total, 2)
        return rounded

    @property
    def discounted_price(self):
        gross = self.unit_price * self.quantity
        if self.discount_tier >= 2:
            rate = 0.20
        else:
            rate = 0.05
        net = gross * (1 - rate)
        floor = max(net, 0.0)
        return round(floor, 2)
