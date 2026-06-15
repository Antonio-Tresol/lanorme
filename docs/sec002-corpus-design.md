# SQL-001 corpus design — raw-SQL evaluation

This document records the design of the labeled evaluation corpus for the
SQL-001 ("No raw SQL — use an ORM or parameterized queries") rule and
reports the current detector's performance against it. Labels are derived
from a working definition that is intentionally independent of any specific
detection implementation.

## Working definition (labels are derived from this only)

> A line is **RAW_SQL** when it contains a Python string literal expressing
> SQL syntax (SELECT / INSERT / UPDATE / DELETE / CREATE / DROP / ALTER /
> TRUNCATE / VACUUM as actual statements, not as identifier tokens) AND that
> string is destined for a database execution path (`.execute(...)`,
> `text(...)`, `pandas.read_sql(...)`, `executemany(...)`, `op.execute(...)`,
> ...) in a way that bypasses or pre-builds beyond the safe
> parameter-binding contract. F-string / `%` / `.format()` / `+` string
> concatenation building SQL counts as RAW_SQL even when the call is
> `.execute(...)`.
>
> A line is **OK** when it is: an ORM expression (`session.query(Model)`,
> `select(Model).where(...)`), a parameterized execute (string-only SQL +
> separate bound-params dict or tuple), a SQL literal in prose (docstring,
> comment, log / error / banner message, test assertion, regex pattern,
> changelog entry), an `.execute(...)` call on a non-DB object
> (`subprocess`, `concurrent.futures`, HTTP client, job runner), or it lives
> in an Alembic migration file (`alembic/versions/`) — review-gated by
> convention.

**Labeling rule (resolves ambiguity):** the labeled line is the line where
the SQL string literal first appears in source on the path to the DB. For
inline calls, this is the `.execute(SQL)` line. For SQL stored in a
constant, it is the constant's assignment line. For triple-quoted multi-line
SQL, it is the line containing the opening `"""`. Lines that only contain
the *execute call* of a constant defined elsewhere are left unlabeled (no
SQL literal on the line) unless interpolation is happening on the call line.

A line is only labeled when it is plausibly classifiable; unrelated code
(imports, function signatures, blank lines) is left unlabeled so the scorer
can detect unlabeled detector flags.

## Category split

| Category file                                          | Labels |
|--------------------------------------------------------|-------:|
| **Positives** (41)                                     |        |
| `positives/pos_sqlalchemy_text.py`                     |      6 |
| `positives/pos_conn_execute_literal.py`                |      6 |
| `positives/pos_fstring_interpolation.py`               |      6 |
| `positives/pos_triple_quoted_multiline.py`             |      4 |
| `positives/pos_constant_then_execute.py`               |      4 |
| `positives/pos_pandas_read_sql.py`                     |      5 |
| `positives/pos_executemany.py`                         |      5 |
| `positives/pos_realistic_repo.py`                      |      5 |
| **Negatives** (79)                                     |        |
| `negatives/neg_orm_expressions.py`                     |      9 |
| `negatives/neg_parameterized_execute.py`               |      5 |
| `negatives/neg_sql_in_docstrings.py`                   |      4 |
| `negatives/neg_sql_in_comments.py`                     |      5 |
| `negatives/neg_sql_in_log_messages.py`                 |      7 |
| `negatives/neg_sql_in_test_assertions.py`              |      6 |
| `negatives/neg_sql_in_regex.py`                        |      8 |
| `negatives/neg_changelog_strings.py`                   |     10 |
| `negatives/neg_non_db_execute.py`                      |      6 |
| `negatives/neg_variable_names.py`                      |     11 |
| `negatives/alembic/versions/0001_initial.py`           |      5 |
| `negatives/alembic/versions/0002_add_locale.py`        |      3 |

Total: **120 labels (41 raw_sql / 79 ok)**, ~1 : 1.9 positive-to-negative
ratio. In a stratified real-repo sample the negative side dominates: most
mentions of SQL keywords in production Python live in comments, logs,
identifiers, tests, and ORM call chains, not in hand-written raw SQL.

## Current detector — P/R/F1 against the labeled corpus

Run: `uv run python evals/score_sec002.py`

```
labels: 120 (41 raw_sql / 79 ok)
TP=35  FP=16  FN=6  TN=63
PRECISION: 0.686
RECALL:    0.854
F1:        0.761
```

## Self-audit

The labels were re-read cold against the working definition. **1 label
flipped:** `pos_realistic_repo.py:22` was originally `raw_sql` on the
argument that `%` interpolation at the call site qualifies. Cold re-read
against the first conjunct of the working definition ("contains a Python
string literal expressing SQL syntax") found that the line has no string
literal at all (the literal is on line 13, already labeled). The
"pre-builds beyond safe parameter binding" clause is a qualifier on the
second conjunct, not a substitute for the first. Removed from labels.

One edge case held:

* Triple-quote-opener lines (e.g. `pos_triple_quoted_multiline.py:15`) carry
  no SQL keyword on the line; the labeling rule pins the label to where the
  literal starts, which is the `"""` line. Kept.

## False-positive pattern diagnoses (implementation-agnostic)

1. **No "safe parameter-binding" awareness (5 FPs in
   `neg_parameterized_execute.py`).** The detector flags every
   `.execute("SELECT ...")` and `text("...")` regardless of whether a
   separate bound-params dict / tuple is supplied. The rule's own
   prescriptive text endorses parameterized queries, so this is the
   highest-value class to fix: distinguish bare-literal calls from
   `(literal, params)` two-argument calls.
2. **No "value vs. payload" channel awareness (6 FPs in
   `neg_sql_in_test_assertions.py`, 1 in `neg_sql_in_log_messages.py`, 1 in
   `neg_changelog_strings.py`).** Any string literal containing SQL keywords
   is flagged, even when it is the right-hand side of an assignment, a
   `return` value, an `==` comparison, or an exception-message argument.
   The detector cannot tell that the string is never reaching a DB.
3. **Method-name overload (2 FPs in `neg_non_db_execute.py`).** Any
   `.execute("...")` is treated as DB execution, including HTTP clients,
   job runners, and any user-defined class with an `execute` method whose
   string argument happens to start with a SQL keyword (or, in two of the
   flagged cases, contains no SQL keyword at all — the call shape alone is
   sufficient).
4. **Regex pattern body looks SQL-like (1 FP in `neg_sql_in_regex.py`).**
   `r"^\s*UPDATE\s+\w+\s+SET\b"` is a regex pattern, not a SQL statement,
   but the keywords trigger the detector.

## False-negative pattern diagnoses (implementation-agnostic)

1. **Multi-line triple-quoted SQL (4 FNs in `pos_triple_quoted_multiline.py`,
   1 in `pos_pandas_read_sql.py`).** When the opening `"""` is on one line
   and the SELECT/DELETE keyword is on the next, the detector apparently
   inspects only the literal-start line and finds no keyword. Real
   reporting / analytics code overwhelmingly uses this shape; this is the
   highest-recall-cost gap.
2. **SQL constant assigned to a multi-line `"""..."""` (1 FN in
   `pos_constant_then_execute.py`).** Same shape, same blind spot —
   `REVENUE_BY_DAY_SQL = """` is missed because the SELECT is on the next
   line.
3. **Constant-then-execute indirection.** Several files (e.g.
   `pos_constant_then_execute.py`, `pos_realistic_repo.py`) put SQL into a
   module constant and then `.execute()` it. The constant line is caught
   when the literal is single-line, but the multi-line constant
   (`REVENUE_BY_DAY_SQL = """`) is missed for the same triple-quote reason
   above. The execute call sites are intentionally unlabeled because no
   literal is on those lines — they are out of scope for this corpus.

## Improvements suggested by this corpus

In priority order — each is a P or R gain the corpus directly measures:

1. **Recognise the two-argument form** `.execute(sql_literal, params)` /
   `.execute(text(sql), params_dict)` / `.executemany(sql, rows)` and treat
   it as parameterized (large precision gain, 5 FPs).
2. **Track string literals across line continuations** — when a `.execute(`
   call's argument is a triple-quoted string, scan inside the string body
   for SQL keywords rather than only the first line (large recall gain,
   5+ FNs).
3. **Bound the "destination" check** — only flag string literals that flow
   into a DB-shaped sink, not every `.execute(...)` regardless of receiver.
   At minimum, exclude `subprocess.*`, `concurrent.futures.*`, and
   `re.execute`-style false friends (precision gain, 2 FPs and others
   latent in real code).
4. **Skip values that never reach an execute path** — string literals that
   are returned, asserted against, or passed to a logger / exception /
   `print` are not payloads (precision gain, 7+ FPs).
