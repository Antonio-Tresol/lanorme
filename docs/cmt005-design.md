# CMT-005 — Restating / redundant comment detector (design)

Status: design only. The current implementation (`_restates` /
`_restating_violations` in `src/lanorme/checks/comments.py`) is a placeholder,
off by default, and false-positive-prone. This document specifies the detector
that should replace it.

## 0. Overriding priority

**Precision over recall.** A linter that wrongly flags a valuable comment is
worse than one that misses a redundant one. Every design decision below trades
recall away to protect precision. The target before flipping `restating = true`
to default-on is **precision >= 0.95** on a real-world corpus (see section 8).

Concretely this means:

- We flag **only** the narrowest, most defensible class of redundancy: a short,
  standalone comment whose entire content is subsumed by the single simple
  statement it sits directly above (or trails on the same line).
- When in doubt, we do not flag. Ambiguity resolves to silence.

---

## 1. Definition and taxonomy

### 1.1 Definition

A comment is **restating / redundant** when it adds no information that is not
already recoverable by reading the immediately adjacent statement. The comment
paraphrases the *what* of the code without supplying any *why*, *caveat*,
*context*, or *non-obvious detail*.

Formally, a comment `C` adjacent to statement `S` is a restatement when:

1. Every content word of `C` is **covered** by `S` — either it appears as (a
   normalized form of) an identifier/keyword in `S`, or it maps to `S`'s
   top-level AST node type via a curated verb table; **and**
2. `C` contributes nothing beyond that coverage (no extra content words, no
   *why*/caveat markers, no references); **and**
3. `S` is a single, simple statement (not a `def`/`class`/decorated node, not a
   compound body).

Restatement is **asymmetric**: the comment must be *subsumed by* the code. The
code may (and usually does) say more than the comment. We do **not** require the
reverse, so we use a one-directional coverage ratio, never a symmetric metric
like Jaccard (section 4.3).

### 1.2 Taxonomy

| Class | Example (comment over code) | Verdict |
| --- | --- | --- |
| **Restating — verb echo** | `# increment counter` / `counter += 1` | redundant |
| **Restating — call echo** | `# normalize the url` / `url = normalize(url)` | redundant |
| **Restating — control echo** | `# loop over users` / `for user in users:` | redundant |
| **Valuable — why** | `# +1 because the header row is excluded` / `counter += 1` | keep |
| **Valuable — caveat** | `# WARNING: mutates input in place` / `normalize(url)` | keep |
| **Valuable — non-obvious detail** | `# normalize to NFC form` / `url = normalize(url)` | keep |
| **Valuable — disambiguation** | `# 0-based; row 0 is the header` / `i += 1` | keep |
| **Valuable — section/intent** | `# --- request parsing ---` | keep |
| **Valuable — API/usage doc** | `# Public: callers must hold the lock` over a `def` | keep |
| **Tooling** | `# noqa`, `# type: ignore` | not prose (skip) |

The line between the first three rows and the rest is exactly the three-part
definition in 1.1. The taxonomy is not enforced by classification; it is
enforced by the **funnel** in section 4 — most "valuable" rows are eliminated by
the allowlist (section 3) before any scoring happens.

---

## 2. Architecture: a precision funnel

Precision comes from **gates that exclude**, not from a clever score. The score
is the last and weakest line of defense. Order of evaluation:

```
candidate comment
  → GATE A  shape gates        (standalone/trailing single comment, length)
  → GATE B  allowlist          (markers that prove the comment is valuable)
  → GATE C  adjacency          (resolve the single adjacent AST statement)
  → GATE D  statement-shape    (must be a simple statement, not def/class/...)
  → SCORE   asymmetric coverage of comment content words by the statement
  → THRESHOLD  flag only if coverage == 1.0 AND content_words <= cap AND ...
```

Anything that fails any gate is silently dropped. Only comments that survive A–D
*and* clear the conservative threshold are reported as CMT-005.

The diagram lists the gates by logical category. The implementation (section
4.6) may evaluate the *cheapest* survivors first — it resolves adjacency (C/D)
before the per-comment allowlist (B) so it can skip work for comments not even
adjacent to a simple statement — but the gating set and its short-circuit
semantics are identical: failing any one gate drops the comment.

This is self-contained: every helper lives in `comments.py` alongside the
existing `_restates` / `_restating_violations`, using only `ast`, `tokenize`,
`re` (all already imported there). No new module, no shared cross-check
infrastructure, no pip dependencies.

---

## 3. Allowlist — comment categories that must NEVER be flagged

This is the core FP-reduction tool. Each category is detected by a **cheap,
literal, case-insensitive prefix / substring / regex test** on the comment text
— never by semantic interpretation. If any test matches, the comment is exempt
and scoring is skipped entirely.

The tests deliberately over-match (they exempt some comments that are *not* in
the named category). That is the correct direction for a precision-first rule:
over-exempting costs recall, never precision.

| # | Category | Trigger (case-insensitive unless noted) | Rationale |
| --- | --- | --- | --- |
| 1 | **Pragmas / tooling** | reuse existing `_PRAGMA_PREFIXES` (`noqa`, `type:`, `pragma`, `pylint:`, `mypy:`, `ruff:`, `isort:`, `fmt:`, `!`, `-*-`, `region`, `endregion`) | machine directives, not prose |
| 2 | **TODO/FIXME tags** | word-start token in `{TODO, FIXME, XXX, HACK, NOTE, BUG, REVIEW, WARNING, OPTIMIZE, DEPRECATED}` | actionable / annotation markers |
| 3 | **Why-explanations** | contains any of `because`, `since`, `so that`, `so we`, `in order to`, `to avoid`, `to prevent`, `otherwise`, `prevent`, `ensure`, `workaround`, `work around`, `reason`, `intentionally`, `on purpose`, `due to`, `caused by`, `that's why`, `which is why` | the comment explains *why*, the highest-value comment kind |
| 4 | **Warnings / caveats** | contains any of `careful`, `caution`, `danger`, `gotcha`, `do not`, `don't`, `must `, `must not`, `never`, `always`, `beware`, `unsafe`, `not thread`, `side effect`, `in place`, `mutate`, `assumes`, `assumption`, `requires`, `precondition`, `invariant` | safety / contract info absent from code |
| 5 | **Section headers** | matches `^[-=#*~ ]{2,}` (rule of dashes/equals/etc.), or text is all-caps with `>= 2` words, or ends with `:` and has no code-side match | structural navigation, not description |
| 6 | **License / legal** | contains `copyright`, `(c)`, `license`, `licence`, `spdx`, `all rights reserved`, `gnu`, `apache`, `mit license`, `bsd`, `gpl` | legal boilerplate |
| 7 | **URLs / references** | contains `http://`, `https://`, `www.`, `see `, `see:`, `cf.`, `ref:`, `ref `, `refs `, `from `, `per `, `rfc`, `pep `, `pep-`, `bug #`, `issue #`, `gh-`, `#` followed by digits | points outward; the value is the pointer |
| 8 | **Examples** | contains `e.g.`, `i.e.`, `eg.`, `for example`, `for instance`, `example:`, `examples:`, `such as` | illustrative content |
| 9 | **Type / usage / API docs** | contains any docstring-field marker `:param`, `:type`, `:returns`, `:return:`, `:rtype`, `:raises`, `args:`, `returns:`, `raises:`, `yields:`, `params:`, `usage:`, `public:`, `internal:`, `deprecated`, `since `, `:: ` | structured documentation |
| 10 | **Disambiguation cues** | contains units/format/range cues: `0-based`, `1-based`, `zero-based`, `one-based`, `inclusive`, `exclusive`, `utc`, `seconds`, `ms`, `bytes`, `index`, `offset`, `nul`, `null-terminated`, digits with `%`, a literal that does **not** appear in the adjacent statement | clarifies non-obvious semantics |
| 11 | **API-bearing adjacency** | the adjacent statement (gate C/D) is a `FunctionDef`/`AsyncFunctionDef`/`ClassDef`, or the comment sits directly above a decorator line (`@...`) | comments over public/named constructs are intent/contract docs |

Categories 1–10 are text tests; category 11 is an AST-shape test handled by gates
C/D. Categories are checked with short-circuit OR: first hit exempts.

> Implementation note: keep these as module-level frozensets / a compiled
> `re.Pattern`, mirroring the existing `_STOPWORDS` / `_PRAGMA_PREFIXES` /
> `_EMOJI` style. Lowercase the comment once, test substrings against that.

---

## 4. Detection approaches surveyed, and the chosen algorithm

### 4.1 Survey of approaches and their precision/recall tradeoffs

**(a) Lexical token overlap (bag-of-words).** Compare the set of comment words
to the set of code-line words; flag on high overlap. *This is what the
placeholder does* (`_restates`). Cheap, but precision-poor: it has no notion of
*adjacency* (it text-steps to the next line via `_next_code_line`, which breaks
on multi-line statements, blank lines, and decorators), no asymmetry (it treats
`word in ident or ident in word`, which makes `id` match `identifier`,
`is_valid`, etc.), and no allowlist. Recall is decent; precision is unacceptable.

**(b) AST-aware adjacency.** Build a `lineno → top-level statement` map from
`ast.walk(tree)` and compare the comment to the *actual* statement it precedes /
trails, including that statement's node type. This fixes the placeholder's core
defect (text line-stepping). It lets us (i) exempt `def`/`class`/decorated nodes
by type, (ii) restrict to simple statements, and (iii) drive verb→node mapping.
Higher precision, modest recall cost (we ignore comments not adjacent to a
parseable statement). **Chosen as the backbone.**

**(c) Identifier normalization.** Split `snake_case` and `camelCase`/`PascalCase`
into word tokens, lowercase, then apply a *tiny* suffix stripper (not Porter).
Needed so `increment counter` lines up with `counter`, and `normalize the url`
with `normalize`/`url`. Precision risk comes from over-stemming
(`normalize`→`normal` could spuriously match `normal`), so we keep stemming
minimal and require a minimum stem length. **Chosen, in a deliberately weak
form** (section 4.4).

**(d) Stop-word handling.** Strip articles/prepositions/auxiliaries so they do
not count as "content" words needing coverage (reuse and extend the existing
`_STOPWORDS`). Pure precision/recall-neutral plumbing; without it, `# the url`
would never be coverable. **Chosen.**

**(e) Synonym / verb→AST mapping.** A *small curated table* (~10 entries)
mapping comment verbs to the AST node type they describe (e.g.
`increment → AugAssign(+)`). This is what lets us flag `# increment counter`
over `counter += 1` even though the token `increment` never appears in the code.
A general synonym dictionary (WordNet-style) would be a precision disaster and
needs external data; a 10-entry hand-checked table is safe and stdlib-only.
**Chosen, table only** (section 4.5).

**(f) `difflib` sequence ratio.** Considered for fuzzy comment↔code similarity.
Rejected as a *primary* signal: it conflates token order and surface form, has
no asymmetry, and is hard to threshold defensibly. May be used only as an
optional tie-breaker, off by default.

### 4.2 What gets compared (precise statement of inputs)

For a surviving candidate comment `C` adjacent to statement node `S`:

- **Comment content words** `W_c`: tokens from `re.findall(r"[A-Za-z]+", C)`,
  lowercased, with `_STOPWORDS` removed, and with verbs that are keys of the
  verb table set aside into `V_c` (they are matched against `S`'s node type, not
  against code identifiers).
- **Code surface tokens** `T_s`: the union of (i) every `ast.Name.id`,
  `ast.Attribute.attr`, `ast.arg.arg`, and `ast.keyword.arg` reachable from `S`,
  plus (ii) the hard keyword for `S` (e.g. `return`, `del`, `assert`, `raise`,
  `import`, `for`, `while`, `if`) — each split into word tokens, lowercased,
  suffix-stripped, and added to a set. Literals (numbers, strings) are **not**
  added (so a comment mentioning a literal that the code also contains is not
  auto-covered; literals more often signal disambiguation — see category 10).
- **Statement node type** `type(S)` (and, for `AugAssign`, the operator), used
  only by the verb table.

### 4.3 The coverage score (asymmetric, comment-subsumed-by-code)

```
content      = W_c \ V_c          # non-verb content words of the comment
verbs        = V_c                # verb words of the comment
covered_word = { w in content : exists t in T_s with stem-match(w, t) }
covered_verb = { v in verbs   : verb_table[v] matches type(S) (and op) }

n_total   = |content| + |verbs|
n_covered = |covered_word| + |covered_verb|
coverage  = n_covered / n_total           # in [0, 1]; 1.0 means fully subsumed
```

`coverage == 1.0` means *every* content/verb word of the comment is accounted
for by the statement — i.e. the comment says nothing the code does not. This is
the asymmetric subsumption we want. We never compute the reverse direction, so a
verbose statement does not penalize a terse correct comment, and — crucially —
an informative comment ("...to NFC form") drops coverage below 1.0 and is spared.

### 4.4 Identifier normalization (deliberately weak)

```
split_identifier(name):
    # snake_case → parts on "_"; camelCase / PascalCase → parts on case change
    parts = re.split(r"_+", name)
    parts = flatten(re.findall(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|[0-9]+", p) for p in parts)
    return [p.lower() for p in parts if p]

stem(word):
    # last-resort suffix trim ONLY; not Porter, no lemmatization, no deps.
    for suffix in ("ing", "tion", "ies", "es", "ed", "er", "s"):   # longest first
        if word.endswith(suffix) and len(word) - len(suffix) >= MIN_STEM_LEN:
            return word[: -len(suffix)]
    return word

stem_match(a, b):
    return stem(a) == stem(b)        # equality of stems, never substring
```

Key precision decisions:

- **Equality of stems, never substring containment.** The placeholder's
  `word in ident or ident in word` is the single biggest FP source (it makes
  `id`⊆`valid`, `set`⊆`offset`, etc.). We forbid it.
- **`MIN_STEM_LEN` guard** prevents `normalize`→`normal` style collisions and
  keeps short words (`url`, `id`) from collapsing to nothing.
- Stemming is applied to *both* sides identically before equality.

### 4.5 Verb → AST node table (curated, ~12 entries)

Each entry: comment verb(s) → predicate on `type(S)` (and operator for
`AugAssign`). An entry "covers" the verb iff the predicate holds for the
adjacent statement. Hand-checked; intentionally small.

| Comment verb(s) | Matches statement |
| --- | --- |
| `increment`, `inc`, `bump`, `add` (to) | `AugAssign` with `Add` |
| `decrement`, `dec`, `subtract` | `AugAssign` with `Sub` |
| `return`, `returns` | `Return` |
| `yield`, `yields` | any `Yield`/`YieldFrom` inside `S` |
| `raise`, `throw`, `throws` | `Raise` |
| `import`, `imports` | `Import` / `ImportFrom` |
| `loop`, `iterate`, `iterates`, `iterating` | `For` / `AsyncFor` / `While` |
| `assign`, `set`, `store` | `Assign` / `AnnAssign` |
| `delete`, `del`, `remove` | `Delete` |
| `assert`, `check`, `verify` | `Assert` (only; `check`→`If` is too loose — omitted) |
| `call`, `invoke` | top-level `Expr(Call)` |
| `print`, `log` | `Expr(Call)` whose func attr/name is `print`/`log*` |

Notes:

- `check`/`test` → `If` is **deliberately excluded**: `if` guards usually encode
  a non-obvious condition worth a comment, so mapping them invites FPs.
- A verb word counts as covered **only** via this table, never via identifier
  matching, so a verb that does not match the node type leaves coverage < 1.0
  and spares the comment.

### 4.6 Full algorithm (pseudocode, stdlib-only, lives in `comments.py`)

```python
# Tunables (section 5) ----------------------------------------------------
MAX_CONTENT_WORDS = 4        # comment longer than this in content words: skip
MIN_STEM_LEN      = 4        # do not stem below this many remaining chars
COVERAGE_FLOOR    = 1.0      # require FULL subsumption (no fuzzy fraction)
ALLOW_TRAILING    = True     # consider `code  # restatement` too

# Reused from the existing module:
#   _PRAGMA_PREFIXES, _STOPWORDS, _WORD, _Comment (with .standalone),
#   the standalone-block-collapse logic from _block_violations.

def _statement_at_line(stmt_index: dict[int, ast.stmt], line: int) -> ast.stmt | None:
    """Top-level statement whose lineno == line (built once per file)."""
    return stmt_index.get(line)

def _build_stmt_index(tree) -> dict[int, ast.stmt]:
    index = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.stmt):
            index.setdefault(node.lineno, node)        # first wins
    return index

def _adjacent_statement(comment, stmt_index, stmt_lines):
    # standalone comment: the next statement that STARTS strictly below it,
    #                     with no other statement starting in between.
    # trailing comment:   the statement that STARTS on the comment's own line.
    if comment.standalone:
        below = [ln for ln in stmt_lines if ln > comment.line]
        return stmt_index[min(below)] if below else None
    return stmt_index.get(comment.line)

def _is_simple_statement(s) -> bool:
    # Exempts def/class/decorated/compound; allows the leaf statements that a
    # one-line restating comment could plausibly paraphrase.
    if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return False
    if getattr(s, "decorator_list", None):
        return False
    return isinstance(s, (
        ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Return, ast.Delete,
        ast.Raise, ast.Assert, ast.Import, ast.ImportFrom,
        ast.For, ast.AsyncFor, ast.While,
        ast.Expr,                       # bare call / expression statement
    ))

def _in_comment_block(comment, all_standalone_comments) -> bool:
    # True if a neighbouring standalone comment is directly above or below
    # (reuse _block_violations' adjacency walk). Multi-line comment runs are
    # prose; never restatements.
    ...

def _restates_v2(comment, s) -> tuple[bool, float]:
    text = comment.text
    low  = text.lower()
    # GATE B: allowlist (returns early; never flagged)
    if _is_pragma(text) or _is_allowlisted(low):     # categories 1-10
        return (False, 0.0)
    words = [w for w in _WORD.findall(low) if w not in _STOPWORDS]
    verbs   = [w for w in words if w in _VERB_TABLE]
    content = [w for w in words if w not in _VERB_TABLE]
    if not words or len(content) + len(verbs) > MAX_CONTENT_WORDS:
        return (False, 0.0)            # GATE A: too long / empty
    code_tokens = _code_tokens(s)      # set of stemmed identifier/keyword words
    covered_w = sum(any(stem_match(w, t) for t in code_tokens) for w in content)
    covered_v = sum(_VERB_TABLE[v](s) for v in verbs)   # predicate on node type
    n = len(content) + len(verbs)
    coverage = (covered_w + covered_v) / n
    return (coverage >= COVERAGE_FLOOR, coverage)

def _restating_violations(comments, tree, source_lines, relative_file):
    stmt_index   = _build_stmt_index(tree)
    stmt_lines   = sorted(stmt_index)
    standalone   = [c for c in comments if c.standalone]
    out = []
    for c in comments:
        if c.standalone and _in_comment_block(c, standalone):
            continue                                   # GATE A: prose block
        if not c.standalone and not ALLOW_TRAILING:
            continue
        s = _adjacent_statement(c, stmt_index, stmt_lines)   # GATE C
        if s is None or not _is_simple_statement(s):         # GATE D + cat 11
            continue
        flag, _ = _restates_v2(c, s)
        if flag:
            out.append(_violation(
                relative_file=relative_file, line=c.line, code="CMT-005",
                message=f"Comment restates the code: {c.text[:50]}",
                fix="Remove it, or explain the why rather than the what",
            ))
    return out
```

The only signature change versus the placeholder is passing `tree` into
`_restating_violations` (the AST is already parsed in `run` and already passed to
`_scan_file`), so the change is local and self-contained.

---

## 5. Tunable parameters (conservative defaults)

| Parameter | Default | Meaning | Why this default |
| --- | --- | --- | --- |
| `flag_restating` | `False` | master on/off (existing field) | opt-in; experimental |
| `MAX_CONTENT_WORDS` | `4` | max content+verb words to consider | longer comments carry information; capping kills most FPs |
| `COVERAGE_FLOOR` | `1.0` | required coverage to flag | demand *full* subsumption; partial coverage = the comment adds something |
| `MIN_STEM_LEN` | `4` | min chars left after suffix trim | blocks over-stem collisions (`normalize`→`normal`) |
| `ALLOW_TRAILING` | `True` | also check `code  # comment` | trailing restatements are rare but high-confidence |
| `verb_table` | 12 fixed entries | comment-verb → node-type | curated; not user-extensible by default (extensible later via config if needed) |

All are module constants by default, mirroring the existing constants in
`comments.py`. Only `flag_restating` (already wired through `configure`) is
user-facing initially; the rest are deliberately *not* exposed, to keep the
contract narrow. If exposed later, follow the existing `configure` pattern
(`max_block_lines`, `max_comment_chars`).

The single most important tuning lever for precision is the pair
`COVERAGE_FLOOR = 1.0` + `MAX_CONTENT_WORDS = 4`: together they restrict flags
to short, fully-subsumed comments. Lowering either trades precision for recall
and should not be done without re-running section 8's validation.

---

## 6. Hard cases and how the design avoids false positives

| # | Comment / code | Outcome | Mechanism |
| --- | --- | --- | --- |
| 1 | `# increment counter` / `counter += 1` | **FLAG** | verb table `increment→AugAssign(Add)`; `counter` stem-matches; coverage 1.0; 2 content+verb words |
| 2 | `# loop over users` / `for user in users:` | **FLAG** | verb `loop→For`; `users` stem-matches; coverage 1.0 |
| 3 | `# normalize the url` / `url = normalize(url)` | **FLAG** | `the` is a stopword; `normalize`,`url` stem-match identifiers; coverage 1.0 |
| 4 | `# normalize the url to NFC form` / `url = normalize(url)` | keep | `nfc`,`form` not covered → coverage < 1.0 |
| 5 | `# +1 because the header row is excluded` / `counter += 1` | keep | allowlist cat 3 (`because`) |
| 6 | `# WARNING: mutates input in place` / `normalize(x)` | keep | allowlist cat 2 (`WARNING`) + cat 4 (`in place`, `mutate`) |
| 7 | `# 0-based; row 0 is the header` / `i += 1` | keep | allowlist cat 10 (`0-based`) |
| 8 | `# --- request parsing ---` | keep | allowlist cat 5 (rule of dashes) |
| 9 | `# See RFC 5322 for the grammar` / `parse(addr)` | keep | allowlist cat 7 (`see `, `rfc`) |
| 10 | `# returns the user id` / `return user.id` | borderline → **FLAG only if** `id`/`user` stem-match and nothing else | verb `return→Return`; `user`,`id` covered; coverage 1.0. Acceptable: this *is* a pure restatement. If observed to harm precision in validation, demote `return`/`returns` from the verb table. |
| 11 | comment directly above `def load(...)` | keep | gate D / cat 11: adjacent node is `FunctionDef` |
| 12 | comment directly above `@app.route(...)` | keep | gate D: `decorator_list` non-empty |
| 13 | `import os  # noqa: F401` | keep | cat 1 pragma; also trailing-on-import |
| 14 | two standalone comment lines above one statement | keep | `_in_comment_block` excludes runs (prose) |
| 15 | `# id` / `if is_valid(user): ...` | keep | gate D: `If` is not in the simple-statement set; also stem equality, not substring, so `id`≠`valid` |
| 16 | `# set timeout to 30s` / `timeout = 30` | keep | `30s`/`s` not covered (literals excluded from `T_s`) → coverage < 1.0; also `30s` is a disambiguation cue (cat 10) |
| 17 | `# fall through to default` / `pass` | keep | `fall`,`through`,`default` not covered by a bare `Pass`/`Expr`; coverage < 1.0 |
| 18 | comment above a multi-line statement (call spanning 5 lines) | handled | `_build_stmt_index` keys on the statement's `lineno`; adjacency uses the AST start line, not text-stepping |
| 19 | `# TODO: rename this` / `x = compute()` | keep | cat 2 (`TODO`) |
| 20 | `# Copyright 2026 Acme` (module top) | keep | cat 6 (`copyright`); also usually not adjacent to a simple stmt |

The recurring pattern: **valuable comments fail a gate or drop below coverage
1.0; only bare paraphrase survives.**

---

## 7. Why this is more precise than the placeholder

The placeholder (`_restates`) fails on all four axes; the design fixes each:

1. **Adjacency.** `_next_code_line` text-steps to the next non-blank line, which
   misattributes the comment when statements span lines, follow blanks, or are
   decorated. → Replaced by an AST `lineno → statement` map.
2. **Substring matching.** `word in ident or ident in word` produces spurious
   matches (`id`⊆`valid`). → Replaced by stem **equality**.
3. **No allowlist.** Any 1–4 word comment whose words happen to appear in the
   next line is flagged, including why/caveat/section comments. → 11-category
   allowlist runs first.
4. **No node-type awareness.** Comments over `def`/`class` are flagged. → Gate D
   exempts non-simple statements; the verb table requires node-type agreement.

---

## 8. Validation plan (part of "rigorous")

Before `restating = true` can ship default-on:

1. **Corpus.** Run the detector (read-only) over a few thousand files of real,
   well-commented Python (e.g. the stdlib `Lib/`, a handful of popular OSS repos
   already on disk, and LaNorme's own `src/`). Use the existing `run` traversal
   with `flag_restating = True`.
2. **Manual review.** Inspect every flag. A flag is a true positive only if a
   competent reviewer agrees the comment adds nothing the adjacent statement
   already says.
3. **Metric.** Compute precision = TP / (TP + FP). **Gate: precision >= 0.95.**
   If below, the first remedies (in order) are: tighten the allowlist (add the
   leaking category), demote a verb-table entry (e.g. `return`, `check`), or
   lower `MAX_CONTENT_WORDS`. Do **not** raise recall at precision's expense.
4. **Regression fixtures.** Add the 20 hard cases of section 6 as a fixture pair
   (a "should-flag" file and a "must-not-flag" file) under `tests/fixtures/`,
   matching the existing fixture layout (`tests/fixtures/clean`, `.../dirty`).
5. **Re-run on change.** Any edit to the allowlist, verb table, or thresholds
   re-runs steps 1–3 on the same corpus snapshot for comparability.

---

## 9. Open questions

- **`return`/`returns` and `assign`/`set` in the verb table.** They are the
  loosest entries (almost any statement "assigns" or a function "returns"). They
  earn their place on canonical examples (`# returns the user id`), but if
  corpus validation shows them leaking, demote them. Decision deferred to
  section 8 data.
- **Trailing comments default.** `ALLOW_TRAILING = True` is proposed because
  trailing restatements (`x += 1  # increment x`) are high-confidence. If they
  prove rare and noisy in practice, flip the default to `False`.
- **Per-statement vs. per-line adjacency for standalone comments separated by a
  blank line.** Current rule: the comment still binds to the next statement even
  across one blank line. A stricter variant (require zero blank lines between
  comment and statement) would raise precision at some recall cost; revisit with
  corpus data.
- **Whether to surface any tunable beyond `flag_restating`.** Kept internal for
  now to keep the public contract small; expose via `configure` only if users
  ask.
