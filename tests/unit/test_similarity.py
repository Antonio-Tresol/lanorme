"""Tests for the SIMILAR-001 fuzzy near-duplicate check.

The headline test is a corpus regression lock: the check must hold precision
1.0 and recall >= 0.85 on the labelled corpus under
``evals/corpora/duplication_similar/``. The rest are targeted behaviour tests.
"""

from __future__ import annotations

from pathlib import Path

from lanorme import Status
from lanorme.checks.similarity import SimilarityCheck

_CORPUS = Path(__file__).resolve().parents[2] / "evals" / "corpora" / "duplication_similar"


def _enabled() -> SimilarityCheck:
    check = SimilarityCheck()
    check.configure(settings={"enabled": True})
    return check


def _flags(tmp_path: Path, body: str) -> bool:
    # Score one case in isolation: write it alone, run the check, report whether
    # SIMILAR-001 fired (mirrors the corpus scoring methodology).
    path = tmp_path / "case.py"
    path.write_text(body, encoding="utf-8")
    result = _enabled().run(src_root=str(tmp_path))
    return any(w.rule == "SIMILAR-001" for w in result.warnings)


def test_corpus_precision_is_perfect_and_recall_is_high():
    # Arrange: each corpus file scored in isolation against its directory label.
    check = _enabled()
    tp = fp = fn = tn = 0
    for label, folder in (("pos", "positives"), ("neg", "negatives")):
        for case in sorted((_CORPUS / folder).glob("*.py")):
            flagged = any(
                w.rule == "SIMILAR-001"
                for w in check.run(src_root=str(case.parent)).warnings
                if w.file == case.name
            )
            if label == "pos":
                tp += flagged
                fn += not flagged
            else:
                fp += flagged
                tn += not flagged

    # Act.
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0

    # Assert: precision-first contract, locked as a regression.
    assert precision == 1.0, f"precision regressed to {precision:.3f} (FP={fp})"
    assert recall >= 0.85, f"recall regressed to {recall:.3f} (FN={fn})"


def test_attribute_renamed_clone_is_flagged(tmp_path: Path):
    # Arrange + Act: same computation, one attribute renamed (DRY-001 misses this).
    body = (
        "def a(s):\n x = s.alpha\n y = s.beta\n z = combine(x, y)\n w = z * 2\n return w\n\n"
        "def b(s):\n x = s.gamma\n y = s.beta\n z = combine(x, y)\n w = z * 2\n return w\n"
    )

    # Assert.
    assert _flags(tmp_path, body)


def test_parallel_builder_with_disjoint_attrs_is_not_flagged(tmp_path: Path):
    # Arrange + Act: same dict keys, disjoint source attributes (precision trap).
    body = (
        "def a(o):\n d = {}\n d['host'] = o.mail_host\n d['port'] = o.mail_port\n"
        " d['user'] = o.mail_user\n return d\n\n"
        "def b(o):\n d = {}\n d['host'] = o.bucket_host\n d['port'] = o.bucket_port\n"
        " d['user'] = o.bucket_user\n return d\n"
    )

    # Assert.
    assert not _flags(tmp_path, body)


def test_disabled_by_default(tmp_path: Path):
    # Arrange: a clear clone pair.
    body = (
        "def a(s):\n x = s.alpha\n y = s.beta\n z = combine(x, y)\n w = z * 2\n return w\n\n"
        "def b(s):\n x = s.alpha\n y = s.beta\n z = combine(x, y)\n w = z * 2\n return w\n"
    )
    (tmp_path / "m.py").write_text(body, encoding="utf-8")

    # Act: the default check ships off.
    result = SimilarityCheck().run(src_root=str(tmp_path))

    # Assert.
    assert result.status == Status.PASS
    assert result.warnings == []


def test_findings_are_warnings_not_violations(tmp_path: Path):
    # Arrange + Act.
    body = (
        "def a(s):\n x = s.alpha\n y = s.beta\n z = combine(x, y)\n w = z * 2\n return w\n\n"
        "def b(s):\n x = s.gamma\n y = s.beta\n z = combine(x, y)\n w = z * 2\n return w\n"
    )
    (tmp_path / "m.py").write_text(body, encoding="utf-8")
    result = _enabled().run(src_root=str(tmp_path))

    # Assert: advisory only, never fails the build.
    assert result.status == Status.WARN
    assert result.violations == []
    assert result.warnings
