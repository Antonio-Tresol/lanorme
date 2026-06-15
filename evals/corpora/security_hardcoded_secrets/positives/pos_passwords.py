"""Password literals committed in assignments, dict literals, and call kwargs."""

from __future__ import annotations


password = "s3cret-Pa55word!"
PASSWORD = "hunter2hunter2hunter2"
db_password = "Tr0ub4dor&3xample"

USER_CREDS = {
    "username": "alice",
    "password": "alice-hunter2-prod",
}

ADMIN_CREDS = {"password": "ADMIN!root-9000"}


def connect():
    return _open(host="db.internal", port=5432, password="real-db-password-1!")


def _open(**kwargs):
    return kwargs


# Postgres-style URL with embedded credentials
DATABASE_URL = "postgres://app_user:my-prod-password-42@db.internal:5432/app"
REDIS_URL = "redis://:reallySecretRedisPwd@cache.internal:6379/0"
MONGO_URI = "mongodb://root:RealMongoPwd2024!@mongo.internal:27017/admin"
