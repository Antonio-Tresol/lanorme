"""Tests for TYPE-001 through TYPE-003 strong typing discipline.

The regression of note: a function annotated with a deeply nested union
(`dict[str, int | int | ... | int]` with thousands of terms) overflowed the
recursive ``_collect_value_names`` walk and crashed the whole run. One bad file
must be skipped with an advisory warning, not be fatal, and the rest of the tree
must still be analysed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lanorme import Status
from lanorme.checks.strong_types import StrongTypesCheck


@pytest.fixture
def deep_union_source() -> str:
    """A file that parses but overflows the recursive annotation walk."""
    union = " | ".join(["int"] * 4000)
    return f"def f(x: dict[str, {union}]) -> None: ...\n"


def test_deeply_nested_annotation_is_skipped_not_crashed(
    tmp_path: Path, deep_union_source: str
):
    # Arrange: a deep-union file that overflows _collect_value_names, beside a
    # genuine TYPE-001 violation that must still be reported.
    (tmp_path / "deep.py").write_text(deep_union_source, encoding="utf-8")
    (tmp_path / "weak.py").write_text(
        "from typing import Any\n\n\ndef g(x: dict[str, Any]) -> None: ...\n",
        encoding="utf-8",
    )

    # Act: the run must complete rather than raise RecursionError.
    result = StrongTypesCheck().run(src_root=str(tmp_path))

    # Assert: the deep file is skipped with a TYPE-000 warning, and the genuine
    # weakly-typed dict elsewhere is still detected.
    assert result.status == Status.FAIL
    assert any(w.rule.startswith("TYPE-000") for w in result.warnings)
    assert any(v.rule.startswith("TYPE-001") for v in result.violations)


def test_type001_any_leaf_is_violation(tmp_path: Path):
    # Arrange: a dict with an Any value, the canonical weakly-typed container.
    (tmp_path / "m.py").write_text(
        "from typing import Any\n\n\ndef handler(payload: dict[str, Any]) -> None: ...\n",
        encoding="utf-8",
    )

    # Act.
    result = StrongTypesCheck().run(src_root=str(tmp_path))

    # Assert: a hard TYPE-001 failure naming the parameter.
    assert result.status == Status.FAIL
    type001 = [v for v in result.violations if v.rule == "TYPE-001"]
    assert len(type001) == 1
    assert "payload" in type001[0].message


def test_type001_object_leaf_is_placeholder_warning(tmp_path: Path):
    # Arrange: the boundary case: `object` is a soft placeholder, not a fail.
    (tmp_path / "m.py").write_text(
        "def handler(payload: dict[str, object]) -> None: ...\n",
        encoding="utf-8",
    )

    # Act.
    result = StrongTypesCheck().run(src_root=str(tmp_path))

    # Assert: warned, not failed.
    assert result.status == Status.WARN
    assert not result.violations
    assert any(w.rule == "TYPE-001" for w in result.warnings)


def test_type001_concrete_dict_is_clean(tmp_path: Path):
    # Arrange: negative case: a fully concrete container is fine.
    (tmp_path / "m.py").write_text(
        "def handler(payload: dict[str, int]) -> None: ...\n",
        encoding="utf-8",
    )

    # Act.
    result = StrongTypesCheck().run(src_root=str(tmp_path))

    # Assert.
    assert result.status == Status.PASS
    assert not result.violations
    assert not result.warnings


def test_type002_bare_container_is_violation(tmp_path: Path):
    # Arrange: a bare `dict` annotation with no type parameters.
    (tmp_path / "m.py").write_text(
        "def handler(payload: dict) -> None: ...\n",
        encoding="utf-8",
    )

    # Act.
    result = StrongTypesCheck().run(src_root=str(tmp_path))

    # Assert: a TYPE-002 failure.
    assert result.status == Status.FAIL
    type002 = [v for v in result.violations if v.rule == "TYPE-002"]
    assert len(type002) == 1
    assert "payload" in type002[0].message


def test_type002_parametrised_container_is_clean(tmp_path: Path):
    # Arrange: negative case: the parametrised form is acceptable.
    (tmp_path / "m.py").write_text(
        "def handler(items: list[int]) -> None: ...\n",
        encoding="utf-8",
    )

    # Act.
    result = StrongTypesCheck().run(src_root=str(tmp_path))

    # Assert.
    assert result.status == Status.PASS
    assert not result.violations


def test_type003_untyped_kwargs_is_violation(tmp_path: Path):
    # Arrange: bare `**kwargs` with no annotation.
    (tmp_path / "m.py").write_text(
        "def handler(**kwargs) -> None: ...\n",
        encoding="utf-8",
    )

    # Act.
    result = StrongTypesCheck().run(src_root=str(tmp_path))

    # Assert: a TYPE-003 failure naming the kwargs parameter.
    assert result.status == Status.FAIL
    type003 = [v for v in result.violations if v.rule == "TYPE-003"]
    assert len(type003) == 1
    assert "kwargs" in type003[0].message


def test_type003_any_kwargs_is_violation(tmp_path: Path):
    # Arrange: boundary case: annotated, but with the forbidden `Any`.
    (tmp_path / "m.py").write_text(
        "from typing import Any\n\n\ndef handler(**kwargs: Any) -> None: ...\n",
        encoding="utf-8",
    )

    # Act.
    result = StrongTypesCheck().run(src_root=str(tmp_path))

    # Assert.
    assert result.status == Status.FAIL
    assert any(v.rule == "TYPE-003" for v in result.violations)


def test_type003_concrete_kwargs_is_clean(tmp_path: Path):
    # Arrange: negative case: a concretely typed **kwargs is fine.
    (tmp_path / "m.py").write_text(
        "def handler(**kwargs: int) -> None: ...\n",
        encoding="utf-8",
    )

    # Act.
    result = StrongTypesCheck().run(src_root=str(tmp_path))

    # Assert.
    assert result.status == Status.PASS
    assert not result.violations


def _type004(result) -> list:
    # TYPE-004 is an advisory warning, not a hard failure.
    return [w for w in result.warnings if w.rule == "TYPE-004"]


def test_type004_annotated_param_value_return_is_flagged(tmp_path: Path):
    # Arrange: the canonical completeness case: an annotated parameter, a real
    # value return, and no return annotation.
    (tmp_path / "m.py").write_text(
        "def first(items: list[int]):\n    return items[0]\n",
        encoding="utf-8",
    )

    # Act.
    result = StrongTypesCheck().run(src_root=str(tmp_path))

    # Assert: advisory warning, so the status is WARN and the build still passes.
    assert result.status == Status.WARN
    assert not result.violations
    hits = _type004(result)
    assert len(hits) == 1
    assert "first" in hits[0].message


def test_type004_async_awaited_return_is_flagged(tmp_path: Path):
    # Arrange: an async function returning an awaited value is in scope; nothing
    # about 'async def' exempts it.
    (tmp_path / "m.py").write_text(
        "async def load(key: str):\n    return await store.get(key)\n",
        encoding="utf-8",
    )

    # Act.
    result = StrongTypesCheck().run(src_root=str(tmp_path))

    # Assert.
    assert _type004(result)


def test_type004_annotated_vararg_satisfies_param_gate(tmp_path: Path):
    # Arrange: the only annotated parameter is the vararg, which must count.
    (tmp_path / "m.py").write_text(
        "def head(*args: int):\n    return args[0]\n",
        encoding="utf-8",
    )

    # Act.
    result = StrongTypesCheck().run(src_root=str(tmp_path))

    # Assert.
    assert _type004(result)


def test_type004_annotated_kwarg_satisfies_param_gate(tmp_path: Path):
    # Arrange: the only annotated parameter is the kwarg, which must count.
    (tmp_path / "m.py").write_text(
        "def merge(**fields: int):\n    return dict(fields)\n",
        encoding="utf-8",
    )

    # Act.
    result = StrongTypesCheck().run(src_root=str(tmp_path))

    # Assert.
    assert _type004(result)


def test_type004_generator_is_exempt(tmp_path: Path):
    # Arrange: an own-scope yield makes this a generator, which is exempt even
    # though it has a typed param and a trailing value return.
    (tmp_path / "m.py").write_text(
        "def scan(root: str):\n    for p in walk(root):\n        yield p\n    return total\n",
        encoding="utf-8",
    )

    # Act.
    result = StrongTypesCheck().run(src_root=str(tmp_path))

    # Assert.
    assert not _type004(result)


def test_type004_nested_yield_does_not_exempt_outer(tmp_path: Path):
    # Arrange: the yield lives in a nested def, so the outer function is not a
    # generator and its own-scope value return must flag.
    (tmp_path / "m.py").write_text(
        "def outer(x: int):\n    def inner():\n        yield 1\n    return x\n",
        encoding="utf-8",
    )

    # Act.
    result = StrongTypesCheck().run(src_root=str(tmp_path))

    # Assert: the outer flags; the nested 'inner' has no annotated param so it
    # does not contribute a TYPE-004 of its own.
    hits = _type004(result)
    assert len(hits) == 1
    assert "outer" in hits[0].message


def test_type004_nested_only_value_return_does_not_flag_outer(tmp_path: Path):
    # Arrange: the only value return lives in a nested def; the outer returns
    # nothing in its own scope.
    (tmp_path / "m.py").write_text(
        "def build(spec: str):\n    def make():\n        return spec\n    register(make)\n",
        encoding="utf-8",
    )

    # Act.
    result = StrongTypesCheck().run(src_root=str(tmp_path))

    # Assert.
    assert not _type004(result)


def test_type004_lambda_body_is_not_an_own_scope_return(tmp_path: Path):
    # Arrange: the only value-bearing expression is a lambda body, a separate
    # scope; the outer has no value return.
    (tmp_path / "m.py").write_text(
        "def transform(values: list[int]):\n    handler = lambda v: v * 2\n    apply(handler, values)\n",
        encoding="utf-8",
    )

    # Act.
    result = StrongTypesCheck().run(src_root=str(tmp_path))

    # Assert.
    assert not _type004(result)


def test_type004_self_only_method_does_not_flag(tmp_path: Path):
    # Arrange: a plain method whose only parameter is the unannotated self.
    (tmp_path / "m.py").write_text(
        "class C:\n    def total(self):\n        return self._a + self._b\n",
        encoding="utf-8",
    )

    # Act.
    result = StrongTypesCheck().run(src_root=str(tmp_path))

    # Assert.
    assert not _type004(result)


def test_type004_sibling_annotated_param_qualifies_method(tmp_path: Path):
    # Arrange: self is unannotated but a sibling parameter is annotated, so the
    # param gate holds.
    (tmp_path / "m.py").write_text(
        "class C:\n    def status_of(self, code: int):\n        if code == 200:\n            return True\n        return False\n",
        encoding="utf-8",
    )

    # Act.
    result = StrongTypesCheck().run(src_root=str(tmp_path))

    # Assert.
    assert _type004(result)


def test_type004_return_none_literal_does_not_flag(tmp_path: Path):
    # Arrange: the only return is the literal None, which is not a real value.
    (tmp_path / "m.py").write_text(
        "def reset(state: dict[str, int]):\n    state.clear()\n    return None\n",
        encoding="utf-8",
    )

    # Act.
    result = StrongTypesCheck().run(src_root=str(tmp_path))

    # Assert.
    assert not _type004(result)


def test_type004_bare_return_does_not_flag(tmp_path: Path):
    # Arrange: the only return is bare, which carries no value.
    (tmp_path / "m.py").write_text(
        "def log_event(message: str):\n    write(message)\n    return\n",
        encoding="utf-8",
    )

    # Act.
    result = StrongTypesCheck().run(src_root=str(tmp_path))

    # Assert.
    assert not _type004(result)


def test_type004_false_and_notimplemented_are_real_values(tmp_path: Path):
    # Arrange: returning False (and NotImplemented) counts as a real value; the
    # literal-None exclusion must not swallow other constants.
    (tmp_path / "m.py").write_text(
        "class C:\n    def __exit__(self, exc_type: type, exc: BaseException, tb: object):\n"
        "        self._closed = True\n        return False\n",
        encoding="utf-8",
    )

    # Act.
    result = StrongTypesCheck().run(src_root=str(tmp_path))

    # Assert.
    assert _type004(result)


def test_type004_overload_stub_does_not_flag(tmp_path: Path):
    # Arrange: an @overload stub with a '...' body returns no value and so falls
    # out naturally without special-casing the decorator.
    (tmp_path / "m.py").write_text(
        "from typing import overload\n\n\nclass C:\n    @overload\n    def f(self, x: int): ...\n",
        encoding="utf-8",
    )

    # Act.
    result = StrongTypesCheck().run(src_root=str(tmp_path))

    # Assert.
    assert not _type004(result)


def test_type004_abstractmethod_raise_only_does_not_flag(tmp_path: Path):
    # Arrange: an @abstractmethod stub that only raises returns no value.
    (tmp_path / "m.py").write_text(
        "from abc import abstractmethod\n\n\nclass C:\n    @abstractmethod\n"
        "    def area(self, scale: float):\n        raise NotImplementedError\n",
        encoding="utf-8",
    )

    # Act.
    result = StrongTypesCheck().run(src_root=str(tmp_path))

    # Assert.
    assert not _type004(result)


def test_type004_existing_return_annotation_is_out_of_scope(tmp_path: Path):
    # Arrange: a '-> None' is still a return annotation, so condition one fails.
    (tmp_path / "m.py").write_text(
        "def log(self, msg: str) -> None:\n    return print(msg)\n",
        encoding="utf-8",
    )

    # Act.
    result = StrongTypesCheck().run(src_root=str(tmp_path))

    # Assert.
    assert not _type004(result)


def test_type004_unannotated_params_do_not_flag(tmp_path: Path):
    # Arrange: a real value return but no annotated parameter at all.
    (tmp_path / "m.py").write_text(
        "def describe(value):\n    return repr(value)\n",
        encoding="utf-8",
    )

    # Act.
    result = StrongTypesCheck().run(src_root=str(tmp_path))

    # Assert.
    assert not _type004(result)


def test_type004_generator_expression_return_flags(tmp_path: Path):
    # Arrange: a returned generator expression is a separate code object; the
    # enclosing function has no own-scope yield and returns a real object.
    (tmp_path / "m.py").write_text(
        "def make_gen(seq: list[int]):\n    return (x * 2 for x in seq)\n",
        encoding="utf-8",
    )

    # Act.
    result = StrongTypesCheck().run(src_root=str(tmp_path))

    # Assert.
    assert _type004(result)
