"""LaNorme, a configurable, pluggable architecture & code-quality linter.

This module is the stable public API for writing checks. A check is any object
implementing the ``Check`` protocol below; register it with ``register()`` and
LaNorme will discover and run it.

Run all checks against a path:
    lanorme check .

Run a single check:
    lanorme check . --check=layer_deps

Run a single rule code or category:
    lanorme check . --check=DRY-001

JSON output for tooling/agents:
    lanorme check . --output-format=json     # one object per check
    lanorme check . --output-format=ndjson   # one finding per line, jq-friendly

List every registered rule:
    lanorme rules
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

__version__ = "0.13.0"


class Status(enum.Enum):
    """Result status for a check run."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass(frozen=True)
class Violation:
    """A single rule violation found by a check."""

    file: str
    line: int
    rule: str
    message: str
    fix: str

    @property
    def code(self) -> str:
        """The rule code (e.g. ``DRY-001``) parsed from the rule string."""
        return self.rule.split(":", 1)[0].strip().split()[0]

    def to_dict(self) -> dict[str, str | int]:
        return {
            "file": self.file,
            "line": self.line,
            "code": self.code,
            "rule": self.rule,
            "message": self.message,
            "fix": self.fix,
        }

    def format_human(self) -> str:
        return (
            f"  VIOLATION: {self.file}:{self.line} — {self.message}\n"
            f"    Rule: {self.rule}\n"
            f"    Fix: {self.fix}"
        )


@dataclass
class CheckResult:
    """Result of running a single check."""

    check: str
    status: Status
    violations: list[Violation] = field(default_factory=list)
    warnings: list[Violation] = field(default_factory=list)

    def to_dict(self) -> dict[str, str | list[dict[str, str | int]]]:
        return {
            "check": self.check,
            "status": self.status.value,
            "violations": [v.to_dict() for v in self.violations],
            "warnings": [v.to_dict() for v in self.warnings],
        }

    def format_human(self) -> str:
        lines = [f"[{self.status.value}] {self.check}"]
        for v in self.violations:
            lines.append(v.format_human())
        for w in self.warnings:
            lines.append(w.format_human())
        lines.append(
            f"--- {self.check}: {len(self.violations)} violations, {len(self.warnings)} warnings ---"
        )
        return "\n".join(lines)


class Check(Protocol):
    """Protocol that all checks must implement.

    A check may declare ``scope = "tree"`` (default ``"file"``) to mark that it
    compares or aggregates across files. Under cascading per-directory config a
    file-scoped check runs once per region; a tree-scoped check runs once at the
    scan root, because partitioning it would hide findings split across regions.
    """

    name: str
    description: str
    rules: list[str]

    def run(self, *, src_root: str) -> CheckResult:
        """Run the check against the given source root and return results."""
        ...


@runtime_checkable
class Configurable(Protocol):
    """A check that accepts a ``[tool.lanorme.<name>]`` settings table."""

    def configure(self, *, settings: dict[str, object]) -> None:
        """Apply configuration to the check before it runs."""
        ...


# --- Check registry ---

_registry: dict[str, Check] = {}


def register(check: Check) -> None:
    """Register a check so the unified runner can discover it."""
    _registry[check.name] = check


def get_check(name: str) -> Check | None:
    """Get a registered check by name."""
    return _registry.get(name)


def get_all_checks() -> dict[str, Check]:
    """Return all registered checks."""
    return dict(_registry)


def run_check(check: Check, *, src_root: str) -> CheckResult:
    """Run one check, isolating any exception so it cannot abort the whole run.

    A bug in one check (a `RecursionError` on a pathological file, say) must not
    discard the results of every other check. The failure is reported as a
    warning on that check and the run continues.
    """
    try:
        return check.run(src_root=src_root)
    except Exception as exc:  # noqa: BLE001 - one check must not sink the run
        return CheckResult(
            check=check.name,
            status=Status.WARN,
            warnings=[
                Violation(
                    file="",
                    line=0,
                    rule="RUN-000: check raised an exception",
                    message=f"Check {check.name!r} failed on this tree: {type(exc).__name__}",
                    fix="This is a bug in the check; the rest of the run continued",
                ),
            ],
        )


def run_all(*, src_root: str) -> list[CheckResult]:
    """Run all registered checks and return their results."""
    return [run_check(check, src_root=src_root) for check in _registry.values()]
