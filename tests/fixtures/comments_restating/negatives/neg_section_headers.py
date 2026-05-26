"""Section header / banner comments: navigation aids, not restatement."""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def connect(host: str) -> str:
    return host


def disconnect(host: str) -> None:
    pass


# ===========================================================================
# Internal helpers
# ===========================================================================


def _retry(fn):
    return fn


# region serialization


def to_json(obj) -> str:
    return str(obj)


# endregion


# --- Constants ---

MAX_RETRIES = 5
DEFAULT_TIMEOUT = 30
