"""URL paths containing 'token'/'keys' and f-strings logging tokens — not secrets."""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


API_KEYS_ENDPOINT = "/api/keys/"
TOKEN_REFRESH_PATH = "/auth/token/refresh"
PASSWORD_RESET_URL = "https://example.com/account/password/reset"
BEARER_DOCS_URL = "https://example.com/docs/bearer-token"


def log_request(token: str, api_key: str, password: str) -> None:
    log.info("Authorization: Bearer %s", token)
    log.debug(f"Sending api_key={api_key!r} to {API_KEYS_ENDPOINT}")
    msg = f"Bearer {token}"
    line = f"password={password}"
    return None, msg, line


AUTH_HEADER_FORMAT = "Bearer {token}"
BASIC_AUTH_FORMAT = "Basic {user}:{password}"
API_KEY_HEADER_NAME = "X-Api-Key"
