"""Shared pytest fixtures for the LaNorme unit tests.

Centralising fixtures here keeps the per-test arrange blocks small and lets
AAA-002 (DRY tests) pass: the repeated setup lives in one place.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lanorme import discovery, get_check


@pytest.fixture(autouse=True)
def _reset_global_state():
    """Reset process-global state around every test.

    Two leaks to guard: the module-global exclude list published by the CLI,
    and the ``source_root`` field on the registry-singleton checks, which
    ``_apply_check_config`` mutates in place (the protocol carries no config).
    Either would otherwise bleed from one test into the next in the same
    interpreter.
    """
    discovery.set_excludes(())
    yield
    discovery.set_excludes(())
    for name in ("layer_deps", "port_coverage"):
        check = get_check(name)
        if check is not None:
            check.source_root = ""
    # ``domain_terms`` is a registry singleton whose vocabulary is mutated in
    # place by ``configure``; clear it so a configured test does not leak rules.
    domain_terms = get_check("domain_terms")
    if domain_terms is not None:
        domain_terms.term_rules = []


@pytest.fixture
def tmp_py_file(tmp_path: Path):
    """Return a callable that writes a .py file into the test's tmp_path."""

    def _write(*, name: str, body: str) -> Path:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        return path

    return _write
