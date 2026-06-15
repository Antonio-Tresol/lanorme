"""SQL keywords embedded in log / status / user-facing message strings.

Loggers, exception messages, and stdout printlines often mention SQL
operations narratively (``"Running SELECT for user X"``). The strings are
formatted for humans and never reach a DB execute call.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def warm_cache(user_id):
    logger.info("Running SELECT for user %s", user_id)
    logger.debug("Will UPDATE the warm-cache timestamp after fetch")


def report_progress(table, rows):
    print(f"finished INSERT batch into {table} ({rows} rows)")


def announce_migration(version):
    logger.warning("About to CREATE INDEX as part of migration %s", version)


def handle_failure(exc):
    raise RuntimeError("DELETE FROM users failed: " + str(exc)) from exc


def status_line(state):
    return f"current pipeline stage: SELECT-then-AGGREGATE ({state})"


def banner():
    return "ETL pipeline: SELECT -> TRANSFORM -> LOAD"
