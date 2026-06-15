"""Reading credentials from environment variables — not hardcoded."""

from __future__ import annotations

import os


api_key = os.environ["API_KEY"]
password = os.environ.get("DB_PASSWORD")
secret_key = os.getenv("SECRET_KEY")
aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID", "")
aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY", "")

token = os.environ.get("GITHUB_TOKEN")
bearer_token = os.environ["BEARER_TOKEN"]

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY")

PRIVATE_KEY = os.environ["RSA_PRIVATE_KEY"]


def load() -> dict[str, str | None]:
    return {
        "password": os.getenv("DB_PASSWORD"),
        "api_key": os.getenv("API_KEY"),
        "token": os.environ.get("AUTH_TOKEN"),
    }
