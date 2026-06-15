"""Test-fixture file: passwords/tokens used only by tests are not production secrets.

The filename itself signals 'test fixture' (test_*.py), which is the carve-out
for the working definition: literals here are scoped to the test suite.
"""

from __future__ import annotations


TEST_USER_PASSWORD = "test-password-123"
TEST_ADMIN_PASSWORD = "admin-test-pw"

FAKE_API_KEY = "sk_test_fakefakefakefakefakefakefake"
DUMMY_TOKEN = "test-token-not-real-0000000000000000"

# Bog-standard test creds reused across the suite
TEST_BEARER = "Bearer test-bearer-token-aaaaaaaaaaaaaaaa"
TEST_AWS_KEY = "AKIATEST00000000TEST"
TEST_AWS_SECRET = "test/secret/key/abcdefghijklmnopqrstuvwxyz0123"

TEST_JWT = "eyJhbGciOiJIUzI1NiJ9.eyJ1c2VyIjoidGVzdCJ9.test-signature"


def fixture_credentials() -> dict[str, str]:
    return {
        "username": "test-user",
        "password": "test-password-123",
        "api_key": "sk_test_fakefakefakefakefakefakefake",
    }
