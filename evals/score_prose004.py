"""Score PROSE-004 (em-dash density) against the labelled evaluation corpus.

Runs ``ProseCheck`` with the em-dash-density advisory enabled over the labelled
corpus under ``evals/corpora/prose_em_dash/``, compares which Markdown documents
it flags with PROSE-004 to the ground-truth labels in ``labels.json``, and reports
precision, recall and F1 along with the explicit false-positive and false-negative
lists.

The corpus is labelled at the DOCUMENT level: each fixture file maps to
``{"should_fire": true|false}``. It is deliberately precision-hostile on the
negative side. The majority of documents are natural edited English that use em
dashes sparingly, plus a fully eligible long document that clears every floor yet
keeps em dashes in well under half its sentences, a short em-heavy document below
the eligibility floor, and a document whose only em dashes live inside fenced code.
The positives are long machine-style documents that carry an em dash through most
of their sentences. The point is to measure whether the calibrated thresholds
separate natural prose from overuse without a single false positive.

Run:
    uv run python evals/score_prose004.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from lanorme.checks.prose import ProseCheck

_RULE = "PROSE-004"
_CORPUS_REL = "evals/corpora/prose_em_dash"
_CORPUS = Path(__file__).resolve().parent / "corpora" / "prose_em_dash"
_LABELS = _CORPUS / "labels.json"


def _load_labels() -> dict[str, bool]:
    """Map each fixture filename to its ``should_fire`` boolean."""
    raw = json.loads(_LABELS.read_text(encoding="utf-8"))
    return {name: bool(entry["should_fire"]) for name, entry in raw.items()}


def _fired_documents() -> set[str]:
    """Run PROSE-004 over the corpus; return filenames that produced a warning.

    The density advisory is a warning (exit 0), and its rule string is the full
    ``"PROSE-004: ..."`` label, so match by prefix rather than equality.
    """
    check = ProseCheck(
        enabled=True,
        flag_em_dash=False,
        flag_em_dash_density=True,
    )
    result = check.run(src_root=str(_CORPUS))
    return {
        warning.file.replace("\\", "/")
        for warning in result.warnings
        if warning.rule.startswith(_RULE)
    }


def _ratio(*, numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def score() -> dict:
    """Run the rule against its labelled corpus and return metrics.

    Returns ``{"rule", "corpus", "tp", "fp", "fn", "tn", "precision", "recall",
    "f1"}``. Raises ``ValueError`` if the corpus is out of date (a finding on a
    file not in labels.json), naming the offending ``file:line``.
    """
    labels = _load_labels()

    # Every labelled document must exist and be readable, else we would score a
    # wrong number against a doc that could not be analysed. Check before running.
    for name in sorted(labels):
        path = _CORPUS / name
        try:
            path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise ValueError(
                f"labelled document cannot be analysed: {_CORPUS_REL}/{name}:1 ({exc})"
            ) from exc

    fired = _fired_documents()

    # A fired document that is not in labels.json means the corpus is out of date
    # and the precision number cannot be trusted. PROSE-004 reports on line 1.
    unlabelled = sorted(fired - set(labels))
    if unlabelled:
        offenders = ", ".join(f"{_CORPUS_REL}/{name}:1" for name in unlabelled)
        raise ValueError(
            f"PROSE-004 fired on file(s) not in labels.json: {offenders}. "
            "Add them to labels.json (or remove the fixture) before scoring."
        )

    positives = {name for name, should in labels.items() if should}
    negatives = {name for name, should in labels.items() if not should}

    true_positives = sorted(fired & positives)
    false_positives = sorted(fired & negatives)
    false_negatives = sorted(positives - fired)

    tp, fp, fn = len(true_positives), len(false_positives), len(false_negatives)
    tn = len(negatives) - fp
    precision = _ratio(numerator=tp, denominator=tp + fp)
    recall = _ratio(numerator=tp, denominator=tp + fn)
    f1 = _ratio(numerator=2 * precision * recall, denominator=precision + recall)

    return {
        "rule": _RULE,
        "corpus": _CORPUS_REL,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def _print_report(*, metrics: dict, labels: dict[str, bool], fired: set[str]) -> None:
    positives = {name for name, should in labels.items() if should}
    negatives = {name for name, should in labels.items() if not should}
    false_positives = sorted(fired & negatives)
    false_negatives = sorted(positives - fired)

    print("PROSE-004 em-dash-density detector — evaluation against labelled corpus")
    print(f"corpus: {_CORPUS}")
    print(
        f"labels: {len(labels)} documents "
        f"({len(positives)} should-fire / {len(negatives)} should-not-fire)\n"
    )

    print("Confusion counts")
    print(f"  true positives  (TP): {metrics['tp']}")
    print(f"  false positives (FP): {metrics['fp']}")
    print(f"  false negatives (FN): {metrics['fn']}")
    print(f"  true negatives  (TN): {metrics['tn']}\n")

    print("Metrics")
    print(f"  PRECISION: {metrics['precision']:.3f}  (TP / (TP + FP))")
    print(f"  RECALL:    {metrics['recall']:.3f}  (TP / (TP + FN))")
    print(f"  F1:        {metrics['f1']:.3f}\n")

    print(f"FALSE POSITIVES (fired but labelled should-not-fire) — {metrics['fp']}")
    if false_positives:
        for name in false_positives:
            print(f"  {name}")
    else:
        print("  (none) — PROSE-004 fired on no document the corpus marks natural")
    print()

    print(f"FALSE NEGATIVES (labelled should-fire but missed) — {metrics['fn']}")
    if false_negatives:
        for name in false_negatives:
            print(f"  {name}")
    else:
        print("  (none) — PROSE-004 caught every document labelled as overuse")


def main() -> int:
    if not _LABELS.is_file():
        print(f"error: labels file not found at {_LABELS}", file=sys.stderr)
        return 2

    try:
        metrics = score()
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    _print_report(metrics=metrics, labels=_load_labels(), fired=_fired_documents())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
