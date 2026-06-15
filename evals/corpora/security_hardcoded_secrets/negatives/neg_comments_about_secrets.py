"""Comments that mention secrets but commit nothing."""

from __future__ import annotations

import os


# the password is read from KMS at boot
password = os.environ["DB_PASSWORD"]

# api_key comes from Vault; never commit it
api_key = os.environ["API_KEY"]

# TODO: rotate this secret_key on the next release
secret_key = os.environ["SECRET_KEY"]

# NOTE: bearer_token used to live here as a literal; do not re-add
bearer_token = os.environ["BEARER_TOKEN"]

# WARNING: do not hardcode the aws_secret_access_key
aws_secret_access_key = os.environ["AWS_SECRET_ACCESS_KEY"]

# private_key is loaded lazily by the cryptography helper module
private_key = None

# Example (do not commit): api_key = "sk_live_XXXXXXXXXX"
# Example (do not commit): password = "hunter2"
github_token = os.environ.get("GITHUB_TOKEN")
