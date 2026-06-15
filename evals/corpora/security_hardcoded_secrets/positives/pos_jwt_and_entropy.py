"""JWT-shaped strings and high-entropy hex/base64 assigned to secret-named vars."""

from __future__ import annotations


# JWT-shaped (header.payload.signature)
jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
session_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyIjoiYWxpY2UifQ.Q3kEXAMPLESignaturePartHere1234567"

# 64-char hex secret
secret = "9f8d7c6b5a4e3210fedcba98765432109f8d7c6b5a4e3210fedcba9876543210"
secret_key = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
SECRET_KEY = "deadbeefcafebabe0123456789abcdefdeadbeefcafebabe0123456789abcdef"

# base64 high-entropy assigned to a secret-named var
encryption_key = "QmFzZTY0RW5jb2RlZFNlY3JldEtleVZhbHVlMTIzNDU2Nzg5MA=="
signing_secret = "MmYzNzg5YmMtZGVmYS00YjY3LWE5MTktZmZlZWRkY2NiYmFh"
