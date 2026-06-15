# why: positive - validation pair differing only by the numeric bound checked (18 vs 65) and a removed upper clamp; copy-paste with a tweaked constant.
from __future__ import annotations


def validate_minor(profile, errors):
    age = profile.get("age")
    label = profile.get("name", "anon")
    if age is None:
        errors.append(f"{label}: age missing")
        return errors
    if age < 18:
        errors.append(f"{label}: too young")
    if age > 130:
        errors.append(f"{label}: age implausible")
    return errors


def validate_pensioner(profile, errors):
    age = profile.get("age")
    label = profile.get("name", "anon")
    if age is None:
        errors.append(f"{label}: age missing")
        return errors
    if age < 65:
        errors.append(f"{label}: too young")
    return errors
