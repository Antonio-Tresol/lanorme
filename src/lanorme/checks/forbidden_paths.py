"""PROJ-001: Project-level structural invariants, forbidden directories.

Some directories should simply never exist in a project (build artefacts,
leftover scaffolding, directories that belong to a different layout). This
check fails if any configured directory name appears anywhere in the tree.

Configure the forbidden list in ``[tool.lanorme.forbidden_paths]``::

    [tool.lanorme.forbidden_paths]
    dirs = ["build_artifacts", "legacy_src"]

With no configuration the check is inert (always PASS), so it never produces
false positives on a project that has not opted in.

Directories named one of the forbidden tokens but living inside a vendor tree
(``.venv/``, ``node_modules/``, ``.git/``, ``__pycache__/``) are ignored, the
project does not own those.

Run:
    lanorme check . --check=forbidden_paths
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from lanorme import CheckResult, Status, Violation, register

# Default is empty → the check is inert until configured.
_FORBIDDEN_DIRS: tuple[str, ...] = ()
_VENDOR_PATH_FRAGMENTS = (
    ".venv/",
    "node_modules/",
    ".git/",
    "__pycache__/",
)


def _is_vendor_path(*, relative_path: str) -> bool:
    normalised = relative_path.replace("\\", "/") + "/"
    return any(fragment in normalised for fragment in _VENDOR_PATH_FRAGMENTS)


@dataclass
class ForbiddenPathsCheck:
    """Asserts that configured forbidden directories do not exist in the tree."""

    name: str = "forbidden_paths"
    description: str = "Project-level invariants: forbidden directories must not exist"
    forbidden_dirs: tuple[str, ...] = _FORBIDDEN_DIRS
    rules: list[str] = field(
        default_factory=lambda: [
            "PROJ-001: Configured forbidden directories must not exist",
        ]
    )

    def configure(self, *, settings: dict[str, list[str]]) -> None:
        """Apply ``[tool.lanorme.forbidden_paths]`` configuration."""
        self.forbidden_dirs = tuple(settings.get("dirs", []))

    def run(self, *, src_root: str) -> CheckResult:
        violations: list[Violation] = []
        root = Path(src_root)

        for forbidden in self.forbidden_dirs:
            for hit in root.rglob(forbidden):
                if not hit.is_dir():
                    continue
                relative = str(hit.relative_to(root))
                if _is_vendor_path(relative_path=relative):
                    continue
                violations.append(
                    Violation(
                        file=relative,
                        line=0,
                        rule="PROJ-001",
                        message=f"Forbidden directory '{relative}' exists",
                        fix=f"Delete '{relative}' or remove it from the forbidden list",
                    )
                )

        status = Status.FAIL if violations else Status.PASS
        return CheckResult(check=self.name, status=status, violations=violations)


register(ForbiddenPathsCheck())
