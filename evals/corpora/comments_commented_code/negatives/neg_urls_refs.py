"""URL and external reference comments (citations, doc links, issue refs)."""

from __future__ import annotations

# See https://docs.python.org/3/library/asyncio-task.html#asyncio.gather
# Algorithm from https://en.wikipedia.org/wiki/Reservoir_sampling#Algorithm_R
# Tracking issue: https://github.com/python/cpython/issues/12345
# RFC 7519 section 4.1.3 (https://www.rfc-editor.org/rfc/rfc7519#section-4.1.3)
# Paper: Vaswani et al., "Attention Is All You Need" (arXiv:1706.03762)


def jwt_payload(token: str) -> dict:
    """Decode a JWT payload (unverified)."""
    # See RFC 7519, especially the "exp" claim semantics
    # Reference impl: https://github.com/jpadilla/pyjwt/blob/main/jwt/api_jwt.py
    return {"sub": token}


# Bug report: https://bugs.example.com/PROJ-4421
# Slack thread: https://example.slack.com/archives/C01/p1700000000000000
# Design doc: https://docs.example.com/design/timeouts
DEFAULT_TIMEOUT = 30
