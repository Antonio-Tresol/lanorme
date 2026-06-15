"""Generic API keys, bearer tokens, and provider-shaped tokens assigned to vars."""

from __future__ import annotations


api_key = "sk_live_51HabcDEFghiJKLmnoPQRstuVWXyz0123"
API_KEY = "key-9f8d7c6b5a4e3210fedcba9876543210"
stripe_api_key = "sk_live_4eC39HqLyjWDarjtT1zdp7dc"
openai_api_key = "sk-proj-AbCdEf1234567890GhIjKlMnOpQrStUvWxYz"

github_token = "ghp_AbCdEf1234567890GhIjKlMnOpQrStUvWxYz12"
gh_token = "gho_0123456789abcdef0123456789abcdef0123"
slack_bot_token = "xoxb-1234567890-1234567890123-AbCdEfGhIjKlMnOpQrStUvWx"

bearer_token = "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1In0.signed"
auth_token = "abcdef0123456789abcdef0123456789abcdef01"


def call_api():
    return _request(
        url="https://api.example.com",
        api_key="sk_live_RealLookingKey0123456789abcdef",
        token="ghp_AnotherRealLookingToken12345678abcd",
    )


def _request(**_):
    return None


# OAuth client credentials — both unambiguously secret-named
client_secret = "fakeOAuthClientSecret_abcdef0123456789ABCDEF"
oauth_client_secret = "secret-9f8d7c6b5a4e3210fedcba9876543210abcd"
