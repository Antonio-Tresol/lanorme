# why: negative - two field-mapper / dispatch routines. They share a flat map
# why: shape, but the per-key transforms differ and the keys carry the meaning;
# why: there is no common helper, so flagging would be a boilerplate false hit.
"""Two field mappers whose per-field transforms genuinely diverge."""

from __future__ import annotations


def map_inbound(raw):
    result = {}
    result["name"] = raw["full_name"].strip()
    result["age"] = int(raw["age"])
    result["vip"] = raw["tier"] == "gold"
    result["tags"] = raw.get("tags", "").split(",")
    return result


def map_outbound(model):
    result = {}
    result["full_name"] = model.name.title()
    result["age"] = str(model.age)
    result["tier"] = "gold" if model.vip else "standard"
    result["tags"] = ",".join(model.tags)
    return result
