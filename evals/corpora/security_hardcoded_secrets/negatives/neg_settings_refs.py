"""Pulling credentials from settings/config objects — not hardcoded."""

from __future__ import annotations


class _Settings:
    PASSWORD: str = ""
    API_KEY: str = ""
    SECRET_KEY: str = ""
    DATABASE_URL: str = ""


settings = _Settings()
config = _Settings()


password = settings.PASSWORD
api_key = settings.API_KEY
secret_key = config.SECRET_KEY
database_url = settings.DATABASE_URL

token = config.API_KEY
aws_access_key_id = settings.PASSWORD  # placeholder wiring


def build_client():
    return _Client(
        password=settings.PASSWORD,
        api_key=settings.API_KEY,
        secret=config.SECRET_KEY,
    )


class _Client:
    def __init__(self, **_):
        pass
