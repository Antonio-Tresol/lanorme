"""Score CMT-005 (restating comments) against the labeled evaluation corpus.

Runs ``CommentsCheck`` with the restating rule enabled over the labeled corpus
under ``tests/fixtures/comments_restating/``, compares what it flags as CMT-005
to the ground-truth labels in ``labels.json``, and reports precision, recall and
F1 along with the explicit false-positive and false-negative lists.

The corpus is deliberately precision-hostile: it is heavy on adversarial
negatives (why/rationale comments, warnings, section headers, pragmas, and
short comments that share vocabulary with the code but still add meaning) so the
detector's tendency to flag valuable comments is exposed.

Run:
    uv run python benchmarks/score_cmt005.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from lanorme.checks.comments import CommentsCheck

_CORPUS = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "comments_restating"
_LABELS = _CORPUS / "labels.json"

# The label string that marks a comment as a genuine restatement (a positive).
_RESTATING = "restating"
_OK = "ok"


def _load_labels() -> dict[tuple[str, int], dict[str, str]]:
    """Map (relative_file, line) -> {label, note} for every labeled comment."""
    raw = json.loads(_LABELS.read_text(encoding="utf-8"))
    labels: dict[tuple[str, int], dict[str, str]] = {}
    for rel_file, entries in raw.items():
        for entry in entries:
            labels[(rel_file, int(entry["line"]))] = entry
    return labels


def _flagged_cmt005() -> set[tuple[str, int]]:
    """Run the check with restating enabled; return the set of CMT-005 (file, line)."""
    check = CommentsCheck()
    check.configure(settings={"restating": True})
    result = check.run(src_root=str(_CORPUS))
    return {
        (v.file.replace("\\", "/"), v.line)
        for v in result.violations
        if v.rule == "CMT-005"
    }


def _ratio(*, numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def main() -> int:
    if not _LABELS.is_file():
        print(f"error: labels file not found at {_LABELS}", file=sys.stderr)
        return 2

    labels = _load_labels()
    positives = {key for key, entry in labels.items() if entry["label"] == _RESTATING}
    negatives = {key for key, entry in labels.items() if entry["label"] == _OK}
    flagged = _flagged_cmt005()

    # Every flagged line must be a comment we labeled; an unlabeled flag means
    # the corpus is missing a label and the precision number cannot be trusted.
    unlabeled = sorted(flagged - set(labels))
    if unlabeled:
        print("error: CMT-005 flagged lines that are not in labels.json:", file=sys.stderr)
        for rel_file, line in unlabeled:
            print(f"  {rel_file}:{line}", file=sys.stderr)
        print(
            "Add these comments to labels.json (or remove the fixture) before scoring.",
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

    print("CMT-005 restating-comment detector — evaluation against labeled corpus")
    print(f"corpus: {_CORPUS}")
    print(
        f"labels: {len(labels)} comments "
        f"({len(positives)} restating / {len(negatives)} ok)\n"
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
        print("  (none) — the detector flagged no comment that the corpus marks valuable")
    print()

    print(f"FALSE NEGATIVES (labeled 'restating' but missed) — {fn}")
    if false_negatives:
        for rel_file, line in false_negatives:
            note = labels[(rel_file, line)].get("note", "")
            print(f"  {rel_file}:{line}  {note}")
    else:
        print("  (none) — the detector caught every labeled restatement")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
