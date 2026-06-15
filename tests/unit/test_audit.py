"""The evaluation audit harness must record a complete, well-formed result JSON.

``evals/audit.py`` is the release audit trail: it scores every labelled corpus
and stamps the run with version and hardware metadata. This test runs it end to
end in accuracy-only mode (``--no-perf``) against a throwaway output path, so it
never leaves an ``evals/results/v*.json`` behind, and asserts the metadata stamp
and the per-rule accuracy entries are all present.

Tests follow AAA structure with inline ``# Arrange / # Act / # Assert`` markers.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_AUDIT = Path(__file__).resolve().parents[2] / "evals" / "audit.py"

_METADATA_KEYS = {
    "lanorme_version",
    "git_commit",
    "git_dirty",
    "python_version",
    "platform",
    "processor",
    "timestamp_utc",
}
_KNOWN_RULES = {"CMT-001", "CMT-005", "SQL-001", "SECRETPY-001", "SIMILAR-001"}


def test_audit_writes_metadata_and_accuracy(tmp_path):
    # Arrange: a throwaway output path so no results/v*.json is committed.
    out = tmp_path / "audit.json"

    # Act: run the harness in accuracy-only mode, inheriting the test env so the
    # dynamically imported scorers can import lanorme.
    result = subprocess.run(
        [
            sys.executable,
            str(_AUDIT),
            "--no-perf",
            "--version",
            "0.0.0-test",
            "--output",
            str(out),
        ],
        capture_output=True,
        text=True,
    )

    # Assert: clean exit and a file on disk.
    assert result.returncode == 0, result.stderr
    assert out.is_file()

    report = json.loads(out.read_text(encoding="utf-8"))

    # Assert: the metadata stamp carries every required key.
    assert _METADATA_KEYS <= set(report["metadata"])
    assert report["metadata"]["audited_version"] == "0.0.0-test"

    # Assert: the accuracy block covers the known rules, each with metrics.
    rules = {entry.get("rule") for entry in report["accuracy"]}
    assert _KNOWN_RULES <= rules
    for entry in report["accuracy"]:
        assert "error" not in entry, entry
        assert "precision" in entry
        assert "recall" in entry
        assert "f1" in entry


def test_audit_rejects_missing_version(tmp_path):
    # Arrange: invoke without --version.
    out = tmp_path / "audit.json"

    # Act.
    result = subprocess.run(
        [sys.executable, str(_AUDIT), "--no-perf", "--output", str(out)],
        capture_output=True,
        text=True,
    )

    # Assert: usage error exit 2 and no file written.
    assert result.returncode == 2
    assert not out.exists()
