"""Resolving secrets via function calls / KMS / vault — references, not literals."""

from __future__ import annotations


def get_secret(name: str) -> str: ...
def fetch_token() -> str: ...
def kms_decrypt(blob: bytes) -> str: ...
def read_secret_file(path: str) -> str: ...


password = get_secret("db_password")
api_key = get_secret("stripe/api_key")
secret_key = get_secret("app/secret_key")
token = fetch_token()
bearer_token = fetch_token()

aws_secret_access_key = get_secret("aws/secret")
aws_access_key_id = get_secret("aws/access")

private_key = kms_decrypt(b"ciphertext-blob")
PRIVATE_KEY = read_secret_file("/etc/keys/id_rsa")

github_token = get_secret("github/pat")
slack_bot_token = get_secret("slack/bot")


def make_client():
    return dict(
        password=get_secret("db"),
        api_key=get_secret("api"),
        token=fetch_token(),
    )
