"""``.execute(...)`` methods on objects that are NOT database connections.

Many Python APIs use ``.execute`` for their own dispatch: ``subprocess``,
``concurrent.futures``, request transports, task runners. The string passed
in is a shell command, an HTTP path, or a job name -- never SQL.
"""

from __future__ import annotations

import subprocess
from concurrent.futures import ThreadPoolExecutor


def list_files():
    return subprocess.run(["ls", "-la"], capture_output=True, check=True)


def run_in_pool(fn, *args):
    with ThreadPoolExecutor(max_workers=4) as pool:
        future = pool.submit(fn, *args)
        return future.result()


class HttpClient:
    def execute(self, method: str, path: str):
        return (method, path)


def fetch_users(client: HttpClient):
    return client.execute("GET", "/api/users")


class JobRunner:
    def execute(self, job_name: str):
        return f"ran {job_name}"


def run_nightly(runner: JobRunner):
    return runner.execute("nightly-rollup")


def shell_query():
    return subprocess.run(["grep", "SELECT", "queries.sql"], capture_output=True)
