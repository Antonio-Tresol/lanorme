# why: negative - a single-field coercion validator and a cross-field model validator look superficially similar but operate on different scopes (one value vs the whole model) with different return contracts.
from __future__ import annotations

from pydantic import field_validator, model_validator


class Booking:
    @field_validator("quantity")
    @classmethod
    def coerce_quantity(cls, value):
        number = int(value)
        if number <= 0:
            raise ValueError("quantity must be positive")
        if number > 100:
            number = 100
        rounded = number
        return rounded

    @model_validator(mode="after")
    def check_dates(self):
        start = self.start_date
        end = self.end_date
        if end < start:
            raise ValueError("end before start")
        span = (end - start).days
        if span > 30:
            raise ValueError("range too long")
        return self
