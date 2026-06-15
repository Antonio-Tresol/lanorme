"""Score SIMILAR-001 against the labelled duplication_similar corpus.

Each corpus file holds exactly two top-level functions. Files under
``positives/`` ARE near-duplicates (the check SHOULD flag the file); files
under ``negatives/`` look similar but are legitimately distinct (the check
SHOULD NOT flag the file).

Scoring is done IN ISOLATION: the similarity check is run against each single
file on its own, so functions in other corpus files never cross-match. A file
is "flagged" when the check emits at least one SIMILAR-001 warning for it.

  positive flagged   -> TP        positive not flagged -> FN
  negative flagged   -> FP        negative not flagged -> TN

Reports precision, recall, F1, the confusion counts, and the misclassified
filenames.

Run:
    uv run python evals/score_similar.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from lanorme.checks.similarity import SimilarityCheck

_CORPUS = Path(__file__).resolve().parent / "corpora" / "duplication_similar"
_POSITIVES = _CORPUS / "positives"
_NEGATIVES = _CORPUS / "negatives"

# The rule code this scorer measures (exposed for the audit harness).
RULE = "SIMILAR-001"
_REPO_ROOT = Path(__file__).resolve().parent.parent


def _flagged(*, file_path: Path) -> bool:
    """Run the similarity check against a single file in isolation.

    The check scans a *directory*, so point it at a throwaway root containing
    only this one file by scanning its parent and keeping only this file's
    warnings. Within-file-only pairing means no cross-file matches occur, so
    filtering by filename reproduces strict per-file isolation.
    """
    check = SimilarityCheck(enabled=True)
    result = check.run(src_root=str(file_path.parent))
    return any(w.file == file_path.name for w in result.warnings)


def _ratio(*, numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def score() -> dict:
    """Run SIMILAR-001 against its labelled corpus and return metrics.

    This corpus labels whole files by directory (positives/ versus negatives/)
    rather than by labels.json, so there is no unlabelled-finding case. Returns
    a dict with rule, corpus (repo-relative), tp/fp/fn/tn and precision/recall/
    f1. Raises ValueError if the corpus directories are missing.
    """
    if not _POSITIVES.is_dir() or not _NEGATIVES.is_dir():
        raise ValueError(f"corpus not found under {_CORPUS}")

    positives = sorted(p for p in _POSITIVES.glob("*.py") if p.name != "__init__.py")
    negatives = sorted(p for p in _NEGATIVES.glob("*.py") if p.name != "__init__.py")

    tp = sum(1 for p in positives if _flagged(file_path=p))
    fn = len(positives) - tp
    fp = sum(1 for p in negatives if _flagged(file_path=p))
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

    positives = sorted(p for p in _POSITIVES.glob("*.py") if p.name != "__init__.py")
    negatives = sorted(p for p in _NEGATIVES.glob("*.py") if p.name != "__init__.py")
    false_negatives = [p for p in positives if not _flagged(file_path=p)]
    false_positives = [p for p in negatives if _flagged(file_path=p)]

    tp, fp, fn, tn = metrics["tp"], metrics["fp"], metrics["fn"], metrics["tn"]
    precision, recall, f1 = metrics["precision"], metrics["recall"], metrics["f1"]

    print("SIMILAR-001 structural near-duplicate detector - evaluation against labelled corpus")
    print(f"corpus: {_CORPUS}")
    print(f"files:  {len(positives)} positives / {len(negatives)} negatives\n")

    print("Confusion counts")
    print(f"  true positives  (TP): {tp}")
    print(f"  false positives (FP): {fp}")
    print(f"  false negatives (FN): {fn}")
    print(f"  true negatives  (TN): {tn}\n")

    print("Metrics")
    print(f"  PRECISION: {precision:.3f}  (TP / (TP + FP))")
    print(f"  RECALL:    {recall:.3f}  (TP / (TP + FN))")
    print(f"  F1:        {f1:.3f}\n")

    print(f"FALSE POSITIVES (negative wrongly flagged) - {fp}")
    if false_positives:
        for path in false_positives:
            print(f"  {path.name}")
    else:
        print("  (none)")
    print()

    print(f"FALSE NEGATIVES (positive missed) - {fn}")
    if false_negatives:
        for path in false_negatives:
            print(f"  {path.name}")
    else:
        print("  (none)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
