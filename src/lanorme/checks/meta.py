"""META-001 through META-005: Meta-check that validates all other checks produce structured output.

Inspects every registered check (excluding itself) and verifies:
    META-001  Check has a non-empty ``name`` attribute
    META-002  Check has a non-empty ``description`` attribute
    META-003  Check has a non-empty ``rules`` list
    META-004  When run, check returns a ``CheckResult`` with the correct ``check`` name
    META-005  All violations in the result have non-empty ``file``, ``rule``, ``message``, ``fix``

Run:
    lanorme check . --check=meta
"""

from __future__ import annotations

from dataclasses import dataclass, field

from lanorme import CheckResult, Status, Violation, get_all_checks, register


def _validate_name(*, check_name: str) -> Violation | None:
    """META-001: Verify the check has a non-empty name."""
    if not check_name or not check_name.strip():
        return Violation(
            file="checks/",
            line=0,
            rule="META-001: Check must have a non-empty name",
            message="Registered check has an empty or missing name",
            fix="Set a non-empty `name` attribute on the check class",
        )
    return None


def _validate_description(*, check_name: str, description: str) -> Violation | None:
    """META-002: Verify the check has a non-empty description."""
    if not description or not description.strip():
        return Violation(
            file=f"checks/ ({check_name})",
            line=0,
            rule="META-002: Check must have a non-empty description",
            message=f"Check '{check_name}' has an empty or missing description",
            fix="Set a non-empty `description` attribute on the check class",
        )
    return None


def _validate_rules(*, check_name: str, rules: list[str]) -> Violation | None:
    """META-003: Verify the check has a non-empty rules list."""
    if not rules:
        return Violation(
            file=f"checks/ ({check_name})",
            line=0,
            rule="META-003: Check must have a non-empty rules list",
            message=f"Check '{check_name}' has an empty rules list",
            fix="Add at least one rule string to the `rules` list",
        )
    return None


def _validate_result_check_name(
    *,
    check_name: str,
    result: CheckResult,
) -> Violation | None:
    """META-004: Verify the result's ``check`` field matches the check's name."""
    if result.check != check_name:
        return Violation(
            file=f"checks/ ({check_name})",
            line=0,
            rule="META-004: CheckResult.check must match the check's name",
            message=(
                f"Check '{check_name}' returned a CheckResult with "
                f"check='{result.check}' (expected '{check_name}')"
            ),
            fix="Return CheckResult(check=self.name, ...) from the run() method",
        )
    return None


def _validate_violation_fields(
    *,
    check_name: str,
    violation: Violation,
    source: str,
) -> list[Violation]:
    """META-005: Verify a violation has non-empty required fields."""
    problems: list[Violation] = []
    required_fields = ("file", "rule", "message", "fix")

    for field_name in required_fields:
        value = getattr(violation, field_name, "")
        if not value or (isinstance(value, str) and not value.strip()):
            problems.append(
                Violation(
                    file=f"checks/ ({check_name})",
                    line=0,
                    rule="META-005: Violations must have non-empty file, rule, message, and fix",
                    message=(
                        f"Check '{check_name}' produced a {source} with empty '{field_name}' field"
                    ),
                    fix=f"Ensure all Violation instances have a non-empty `{field_name}`",
                ),
            )

    return problems


@dataclass
class MetaCheck:
    """Meta-check: validates all checks produce structured output."""

    name: str = "meta"
    description: str = "Meta-check: validates all checks produce structured output"
    rules: list[str] = field(
        default_factory=lambda: [
            "META-001: Check must have a non-empty name",
            "META-002: Check must have a non-empty description",
            "META-003: Check must have a non-empty rules list",
            "META-004: CheckResult.check must match the check's name",
            "META-005: Violations must have non-empty file, rule, message, and fix",
        ],
    )

    def run(self, *, src_root: str) -> CheckResult:
        """Inspect all registered checks (excluding self) for structural correctness."""
        violations: list[Violation] = []
        all_checks = get_all_checks()

        for check_name, check in sorted(all_checks.items()):
            # Skip self to avoid infinite recursion.
            if check_name == self.name:
                continue

            # META-001: non-empty name.
            name_violation = _validate_name(check_name=check.name)
            if name_violation:
                violations.append(name_violation)

            # META-002: non-empty description.
            desc_violation = _validate_description(
                check_name=check.name,
                description=check.description,
            )
            if desc_violation:
                violations.append(desc_violation)

            # META-003: non-empty rules list.
            rules_violation = _validate_rules(
                check_name=check.name,
                rules=check.rules,
            )
            if rules_violation:
                violations.append(rules_violation)

            # META-004: run the check and verify result.check matches.
            result = check.run(src_root=src_root)
            result_violation = _validate_result_check_name(
                check_name=check.name,
                result=result,
            )
            if result_violation:
                violations.append(result_violation)

            # META-005: all violations and warnings have required fields.
            for violation in result.violations:
                violations.extend(
                    _validate_violation_fields(
                        check_name=check.name,
                        violation=violation,
                        source="violation",
                    ),
                )
            for warning in result.warnings:
                violations.extend(
                    _validate_violation_fields(
                        check_name=check.name,
                        violation=warning,
                        source="warning",
                    ),
                )

        status = Status.FAIL if violations else Status.PASS
        return CheckResult(
            check=self.name,
            status=status,
            violations=violations,
        )


# Self-register on import.
register(MetaCheck())
