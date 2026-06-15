"""Regex literals that DESCRIBE secret shapes — they are patterns, not secrets."""

from __future__ import annotations

import re


AWS_KEY_RE = re.compile(r"AKIA[0-9A-Z]{16}")
GITHUB_TOKEN_RE = re.compile(r"ghp_[A-Za-z0-9]{36}")
JWT_RE = re.compile(r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$")
PRIVATE_KEY_RE = re.compile(r"-----BEGIN (RSA|OPENSSH) PRIVATE KEY-----")

password_pattern = r"(?i)password\s*=\s*['\"][^'\"]+['\"]"
api_key_pattern = r"api[_-]?key\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]"
bearer_pattern = r"Bearer\s+[A-Za-z0-9._\-]+"
secret_pattern = r"secret\s*=\s*['\"][^'\"]{8,}['\"]"


SECRET_NAME_TOKENS = ("password", "api_key", "token", "secret", "private_key")
