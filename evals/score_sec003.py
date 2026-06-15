"""Score SECRETPY-001 (no hardcoded secrets) against the labeled evaluation corpus.

Runs the ``security_patterns`` check over the labeled corpus under
``evals/corpora/security_hardcoded_secrets/``, compares everything it flags
under the SECRETPY-001 rule prefix to the ground-truth labels in ``labels.json``,
and reports precision, recall and F1 plus the explicit FP and FN lists.

The corpus stratifies real-world Python patterns: AWS keys, password literals,
JWTs, PEM blocks, env-var lookups, settings references, placeholders, type
annotations, regex patterns describing secret shapes, help/docstring text,
log/format strings, URL paths, function-call resolutions, and a test-fixture
carve-out file.

Run:
    uv run python evals/score_sec003.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from lanorme import get_check
from lanorme.checks import secrets as _secrets  # noqa: F401  (self-register)

_CORPUS = (
    Path(__file__).resolve().parent
    / "corpora"
    / "security_hardcoded_secrets"
)
_LABELS = _CORPUS / "labels.json"

# Label string that marks a genuine hardcoded secret (a positive).
_SECRET = "secret"
_OK = "ok"

# The rule string is the long form "SECRETPY-001: ..." — match by prefix so the
# scorer stays stable if the description text is reworded.
_RULE_PREFIX = "SECRETPY-001"

# The rule code this scorer measures (exposed for the audit harness).
RULE = "SECRETPY-001"
_REPO_ROOT = Path(__file__).resolve().parent.parent


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
    check = get_check("secrets")
    if check is None:
        raise RuntimeError("secrets check is not registered")
    result = check.run(src_root=str(_CORPUS))
    return {
        (v.file.replace("\\", "/"), v.line)
        for v in result.violations
        if v.rule.startswith(_RULE_PREFIX)
    }


def _ratio(*, numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def score() -> dict:
    """Run SECRETPY-001 against its labelled corpus and return metrics.

    Returns a dict with rule, corpus (repo-relative), tp/fp/fn/tn and
    precision/recall/f1. Raises ValueError if the corpus is out of date
    (a finding not in labels.json, or a missing labels file).
    """
    if not _LABELS.is_file():
        raise ValueError(f"labels file not found at {_LABELS}")

    labels = _load_labels()
    positives = {key for key, entry in labels.items() if entry["label"] == _SECRET}
    negatives = {key for key, entry in labels.items() if entry["label"] == _OK}
    flagged = _flagged_sec003()

    # Every SECRETPY-001 flag must correspond to a labelled line; an unlabelled
    # flag means the corpus is missing a label and precision is untrustworthy.
    unlabeled = sorted(flagged - set(labels))
    if unlabeled:
        site = f"{unlabeled[0][0]}:{unlabeled[0][1]}"
        raise ValueError(
            f"SECRETPY-001 flagged {len(unlabeled)} line(s) not in labels.json "
            f"(first: {site}); update labels.json before scoring."
        )

    tp = len(flagged & positives)
    fp = len(flagged & negatives)
    fn = len(positives - flagged)
    tn = len(negatives) - fp
    precision = _ratio(numerator=tp, denominator=tp + fp)
    recall = _ratio(numerator=tp, denominator=tp + fn)
    f1 = _ratio(numerator=2 * precision * recall, denominator=precision + recall)
    return {
        "rule": RULE,
        "corpus": _CORPUS.relative_to(_REPO_ROOT).as_posix(),
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": precision, "recall": recall, "f1": f1,
    }


def main() -> int:
    try:
        metrics = score()
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    labels = _load_labels()
    positives = {key for key, entry in labels.items() if entry["label"] == _SECRET}
    negatives = {key for key, entry in labels.items() if entry["label"] == _OK}
    flagged = _flagged_sec003()
    false_positives = sorted(flagged & negatives)
    false_negatives = sorted(positives - flagged)

    tp, fp, fn = metrics["tp"], metrics["fp"], metrics["fn"]
    precision, recall, f1 = metrics["precision"], metrics["recall"], metrics["f1"]

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
