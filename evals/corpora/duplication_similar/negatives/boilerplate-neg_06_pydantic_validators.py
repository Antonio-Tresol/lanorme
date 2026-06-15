# why: negative - two framework-shaped pydantic field validators; each enforces a distinct field rule, the parallel try/raise shape is dictated by the framework not by copy-paste.
def validate_username(cls, value):
    if not isinstance(value, str):
        raise ValueError("username must be a string")
    stripped = value.strip()
    if len(stripped) < 3:
        raise ValueError("username too short")
    if not stripped.isalnum():
        raise ValueError("username must be alphanumeric")
    return stripped.lower()


def validate_postcode(cls, value):
    if not isinstance(value, str):
        raise ValueError("postcode must be a string")
    stripped = value.strip()
    if len(stripped) != 6:
        raise ValueError("postcode must be six characters")
    if not stripped.isupper():
        raise ValueError("postcode must be uppercase")
    return stripped.replace(" ", "")
