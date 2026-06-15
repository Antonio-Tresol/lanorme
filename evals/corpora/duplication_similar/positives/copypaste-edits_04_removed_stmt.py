# why: positive - second function is the first with one validation statement removed; otherwise byte-identical copy-paste, an obvious extract-helper case.
from __future__ import annotations


def build_user_payload(form, defaults):
    payload = {}
    payload["name"] = form.get("name", defaults["name"])
    payload["email"] = form.get("email", defaults["email"])
    payload["role"] = form.get("role", defaults["role"])
    if not payload["email"]:
        raise ValueError("email required")
    payload["active"] = True
    return payload


def build_admin_payload(form, defaults):
    payload = {}
    payload["name"] = form.get("name", defaults["name"])
    payload["email"] = form.get("email", defaults["email"])
    payload["role"] = form.get("role", defaults["role"])
    payload["active"] = True
    return payload
