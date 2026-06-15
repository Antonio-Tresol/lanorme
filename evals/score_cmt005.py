"""Score CMT-005 (restating comments) against the labeled evaluation corpus.

Runs ``CommentsCheck`` with the restating rule enabled over the labeled corpus
under ``evals/corpora/comments_restating/``, compares what it flags as CMT-005
to the ground-truth labels in ``labels.json``, and reports precision, recall and
F1 along with the explicit false-positive and false-negative lists.

The corpus is deliberately precision-hostile: it is heavy on adversarial
negatives (why/rationale comments, warnings, section headers, pragmas, and
short comments that share vocabulary with the code but still add meaning) so the
detector's tendency to flag valuable comments is exposed.

Run:
    uv run python evals/score_cmt005.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from lanorme.checks.restating import RestatingCheck

_CORPUS = Path(__file__).resolve().parent / "corpora" / "comments_restating"
_LABELS = _CORPUS / "labels.json"

# The label string that marks a comment as a genuine restatement (a positive).
_RESTATING = "restating"
_OK = "ok"

# The rule code this scorer measures (exposed for the audit harness).
RULE = "CMT-005"
_REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_labels() -> dict[tuple[str, int], dict[str, str]]:
    """Map (relative_file, line) -> {label, note} for every labeled comment."""
    raw = json.loads(_LABELS.read_text(encoding="utf-8"))
    labels: dict[tuple[str, int], dict[str, str]] = {}
    for rel_file, entries in raw.items():
        for entry in entries:
            labels[(rel_file, int(entry["line"]))] = entry
    return labels


def _flagged_cmt005() -> set[tuple[str, int]]:
    """Run the ``restating`` check; return the set of CMT-005 (file, line)."""
    check = RestatingCheck(enabled=True)
    result = check.run(src_root=str(_CORPUS))
    return {
        (v.file.replace("\\", "/"), v.line)
        for v in result.violations
        if v.rule == "CMT-005"
    }


def _ratio(*, numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def score() -> dict:
    """Run CMT-005 against its labelled corpus and return metrics.

    Returns a dict with rule, corpus (repo-relative), tp/fp/fn/tn and
    precision/recall/f1. Raises ValueError if the corpus is out of date
    (a finding not in labels.json, or a missing labels file).
    """
    if not _LABELS.is_file():
        raise ValueError(f"labels file not found at {_LABELS}")

    labels = _load_labels()
    positives = {key for key, entry in labels.items() if entry["label"] == _RESTATING}
    negatives = {key for key, entry in labels.items() if entry["label"] == _OK}
    flagged = _flagged_cmt005()

    # Every flagged line must be a comment we labelled; an unlabelled flag means
    # the corpus is missing a label and the precision number cannot be trusted.
    unlabeled = sorted(flagged - set(labels))
    if unlabeled:
        site = f"{unlabeled[0][0]}:{unlabeled[0][1]}"
        raise ValueError(
            f"CMT-005 flagged {len(unlabeled)} line(s) not in labels.json "
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
    positives = {key for key, entry in labels.items() if entry["label"] == _RESTATING}
    negatives = {key for key, entry in labels.items() if entry["label"] == _OK}
    flagged = _flagged_cmt005()
    false_positives = sorted(flagged & negatives)
    false_negatives = sorted(positives - flagged)

    tp, fp, fn = metrics["tp"], metrics["fp"], metrics["fn"]
    precision, recall, f1 = metrics["precision"], metrics["recall"], metrics["f1"]

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
