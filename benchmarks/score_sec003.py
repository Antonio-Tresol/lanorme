"""Score SECRETPY-001 (no hardcoded secrets) against the labeled evaluation corpus.

Runs the ``security_patterns`` check over the labeled corpus under
``tests/fixtures/security_hardcoded_secrets/``, compares everything it flags
under the SECRETPY-001 rule prefix to the ground-truth labels in ``labels.json``,
and reports precision, recall and F1 plus the explicit FP and FN lists.

The corpus stratifies real-world Python patterns: AWS keys, password literals,
JWTs, PEM blocks, env-var lookups, settings references, placeholders, type
annotations, regex patterns describing secret shapes, help/docstring text,
log/format strings, URL paths, function-call resolutions, and a test-fixture
carve-out file.

Run:
    uv run python benchmarks/score_sec003.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from lanorme import get_check
from lanorme.checks import security_patterns as _sec  # noqa: F401  (self-register)

_CORPUS = (
    Path(__file__).resolve().parent.parent
    / "tests"
    / "fixtures"
    / "security_hardcoded_secrets"
)
_LABELS = _CORPUS / "labels.json"

# Label string that marks a genuine hardcoded secret (a positive).
_SECRET = "secret"
_OK = "ok"

# The rule string is the long form "SECRETPY-001: ..." — match by prefix so the
# scorer stays stable if the description text is reworded.
_RULE_PREFIX = "SECRETPY-001"


def _load_labels() -> dict[tuple[str, int], dict[str, str]]:
    """Map (relative_file, line) -> {label, note} for every labeled line."""
    raw = json.loads(_LABELS.read_text(encoding="utf-8"))
    labels: dict[tuple[str, int], dict[str, str]] = {}
    for rel_file, entries in raw.items():
        for entry in entries:
            labels[(rel_file, int(entry["line"]))] = entry
    return labels


def _flagged_sec003() -> set[tuple[str, int]]:
    """Run the security check and return the set of SECRETPY-001-flagged (file, line)."""
    check = get_check("security_patterns")
    if check is None:
        raise RuntimeError("security_patterns check is not registered")
    result = check.run(src_root=str(_CORPUS))
    return {
        (v.file.replace("\\", "/"), v.line)
        for v in result.violations
        if v.rule.startswith(_RULE_PREFIX)
    }


def _ratio(*, numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def main() -> int:
    if not _LABELS.is_file():
        print(f"error: labels file not found at {_LABELS}", file=sys.stderr)
        return 2

    labels = _load_labels()
    positives = {key for key, entry in labels.items() if entry["label"] == _SECRET}
    negatives = {key for key, entry in labels.items() if entry["label"] == _OK}
    flagged = _flagged_sec003()

    # Every SECRETPY-001 flag must correspond to a labeled line; an unlabeled flag
    # means the corpus is missing a label and the precision number is untrustworthy.
    unlabeled = sorted(flagged - set(labels))
    if unlabeled:
        print("error: SECRETPY-001 flagged lines that are not in labels.json:", file=sys.stderr)
        for rel_file, line in unlabeled:
            print(f"  {rel_file}:{line}", file=sys.stderr)
        print(
            "Add these lines to labels.json (or remove the fixture) before scoring.",
            file=sys.stderr,
        )
        return 2

    true_positives = sorted(flagged & positives)
    false_positives = sorted(flagged & negatives)
    false_negatives = sorted(positives - flagged)

    tp, fp, fn = len(true_positives), len(false_positives), len(false_negatives)
    precision = _ratio(numerator=tp, denominator=tp + fp)
    recall = _ratio(numerator=tp, denominator=tp + fn)
    f1 = _ratio(numerator=2 * precision * recall, denominator=precision + recall)

    print("SECRETPY-001 hardcoded-secret detector — evaluation against labeled corpus")
    print(f"corpus: {_CORPUS}")
    print(
        f"labels: {len(labels)} lines "
        f"({len(positives)} secret / {len(negatives)} ok)\n"
    )

    print("Confusion counts")
    print(f"  true positives  (TP): {tp}")
    print(f"  false positives (FP): {fp}")
    print(f"  false negatives (FN): {fn}")
    print(f"  true negatives  (TN): {len(negatives) - fp}\n")

    print("Metrics")
    print(f"  PRECISION: {precision:.3f}  (TP / (TP + FP))")
    print(f"  RECALL:    {recall:.3f}  (TP / (TP + FN))")
    print(f"  F1:        {f1:.3f}\n")

    print(f"FALSE POSITIVES (flagged but labeled 'ok') — {fp}")
    if false_positives:
        for rel_file, line in false_positives:
            note = labels[(rel_file, line)].get("note", "")
            print(f"  {rel_file}:{line}  {note}")
    else:
        print("  (none) — the detector flagged no line that the corpus marks safe")
    print()

    print(f"FALSE NEGATIVES (labeled 'secret' but missed) — {fn}")
    if false_negatives:
        for rel_file, line in false_negatives:
            note = labels[(rel_file, line)].get("note", "")
            print(f"  {rel_file}:{line}  {note}")
    else:
        print("  (none) — the detector caught every labeled secret")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
