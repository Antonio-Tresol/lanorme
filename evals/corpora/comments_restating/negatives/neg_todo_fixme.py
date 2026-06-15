"""TODO/FIXME/NOTE/HACK/XXX markers: task tracking, not restatement."""

from __future__ import annotations


def transcode(path: str) -> bytes:
    # TODO: stream the file instead of loading it all into memory.
    with open(path, "rb") as handle:
        return handle.read()


def legacy_sort(rows: list[int]) -> list[int]:
    # FIXME: this is O(n^2); switch to sorted() once tests are added.
    for i in range(len(rows)):
        for j in range(len(rows) - 1):
            if rows[j] > rows[j + 1]:
                rows[j], rows[j + 1] = rows[j + 1], rows[j]
    return rows


def parse(token: str) -> str:
    # HACK: trailing semicolons sneak in from the old exporter; drop them.
    return token.rstrip(";")


def schedule(job) -> None:
    # NOTE: queue ordering is FIFO and relied upon by the billing report.
    _queue.append(job)


def widen(value: int) -> int:
    # XXX: magic constant 4096 mirrors the kernel page size; do not change.
    return value + 4096


_queue: list = []
