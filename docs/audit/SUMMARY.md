# LaNorme audit synthesis — 4 independent reviewers

Four parallel reviewers each judged every rule independently from a distinct
lens, without reading each other's verdicts, the design docs, the corpus-audit
report, or any check implementation past the docstring:

- `01-generic-python.md` — generic mainstream Python OSS practitioner.
- `02-ddd-architecture.md` — DDD / hexagonal / layered-architecture practitioner.
- `03-security-ops.md` — application-security engineer + SRE.
- `04-linter-design.md` — linter-tooling designer (ruff/pylint/mypy lens).

The interesting signal is the cross-reviewer agreement matrix, not any one
verdict. This file is that matrix.

---

## 1. Consensus: LaNorme's actual identity

All four reviewers, in different words, converge on the same finding:

> LaNorme is **two-thirds generic code-style linter** (where it competes
> with ruff/pylint/bandit and mostly loses on precision and ecosystem
> maturity), and **one-third architectural linter** (where it has no
> serious competitor in Python: LAYER, PORT, TERM, STALE, PATH, JUNK,
> AAA-002, and parts of TYPE).
>
> The architectural third is where LaNorme is unique and valuable. The
> generic third is a strategic choice: own it (and ship per-file ignores,
> severity overrides, autofix, caching to actually compete), or delegate
> it to ruff and lean into the architectural identity.

This is the most important finding in the audit. Every other call below
flows from it.

---

## 2. Cross-reviewer agreement matrix (rules with notable signal)

Cells are the reviewer's classification on whatever axis they used; the
right-most column is the consensus action.

| Rule | Generic | DDD | Security | Linter | Consensus action |
|------|---------|-----|----------|--------|------------------|
| **NAMING-001** | DOMAIN, BORDERLINE | DOMAIN, **WRONG (anti-DDD)** | NONE | CLEAN, RISKY | **Demote default-off**; the CRUD prefix set actively destroys what TERM enforces |
| **NAMING-002** | DOMAIN, BORDERLINE | DOMAIN, **WRONG (anti-DDD)** | NONE | CLEAN, RISKY | **Demote default-off**; same defect; the two reviewers who reasoned about DDD both flagged it as the most architecturally suspect rule in the suite |
| **AAA-001** | DOMAIN, QUESTIONABLE | FUNDAMENTAL | OPERATIONAL | UNSAFE default | **Demote default-off**; 4/4 reviewers (including DDD which calls it "neutral") agree the default-on choice will fire on every existing pytest suite |
| **KWARG-001** | CONDITIONAL, QUESTIONABLE | BORDERLINE | OPERATIONAL | UNSAFE default | **Demote default-off**; 3/4 flag as house-style enforcement, not a community norm |
| **TYPING-001** | DOMAIN, QUESTIONABLE | CONDITIONAL, **WRONG** | NONE | UNSAFE default | **Flip the premise** (encourage TYPE_CHECKING, not forbid) or drop; 3/4 say the rule inverts the community consensus |
| **SECRET-001** | UNIVERSAL, SOUND | FUNDAMENTAL | PRIVACY, **INSUFFICIENT** | RISKY | **Rename to match scope** (`SECRET-PY-001`); split to add a non-Python scope; the security reviewer flags this as the rule most likely to give false confidence |
| **AUTH-001** | DOMAIN, SOUND | DOMAIN, BORDERLINE | AUTH, **INSUFFICIENT** | RISKY | **Rename + split**: AUTHN-001 (auth present) + AUTHZ-001 stub; stop using HTTP verb as the mutation oracle |
| **SQL-001** | CONDITIONAL, BORDERLINE | FUNDAMENTAL, CORRECT | INJECTION, BORDERLINE | RISKY | **Tighten** to "string-formatted SQL at execute call sites" (AST-tracked) and exempt `alembic/`, `migrations/` |
| **JUNK-002** | CONDITIONAL, BORDERLINE | FUNDAMENTAL | **PRIVACY, SOUND** | RISKY | **Keep on but tighten**: security reviewer says this is genuine security work (screenshot token-leak vector); generic/linter say tighten the asset-dir default and add `allow` to absorb FPs |
| **SIZE-003** (10-method) | CONDITIONAL, BORDERLINE | FUNDAMENTAL, BORDERLINE | NONE | RISKY | **Keep advisory**; already WARN-level so the noise is bounded |
| **TEST-001** | CONDITIONAL, QUESTIONABLE | FUNDAMENTAL, BORDERLINE | OPERATIONAL, BORDERLINE | RISKY | **Rename + soften claim**: it's a `TEST-FILE-PRESENT` rule, not a coverage rule; add `COV-001` that reads `coverage.py` JSON when present |
| **CMT-001** | UNIVERSAL, BORDERLINE | FUNDAMENTAL | OPERATIONAL | RISKY | **Keep default-on**; reviewers expected noise (docstring examples) but the GAN corpus measured P=0.978 — the implementation is precision-better than the reviewers' priors. Worth highlighting in the README. |
| **META-001..005** | DOMAIN (linter-internal), SOUND | FUNDAMENTAL | OPERATIONAL, SOUND | **MISPLACED** | **Hide from `lanorme check`**, expose via `lanorme self-check`; one reviewer's "the most important rules in the suite" but it's a developer-facing concern that pollutes user output |
| **TERM-NNN** | DOMAIN, SOUND | DOMAIN, **CORRECT and rare** | NONE | CLEAN, SAFE | **Keep**; DDD reviewer calls this one of LaNorme's strongest ideas (operationalising chapter 2 of the blue book); add per-bounded-context scoping later |
| **LAYER-001..005** | DOMAIN, SOUND | DOMAIN, **CORRECT** (canonical) | OPERATIONAL | SAFE | **Keep**; all four agree this is well-shaped and unique; DDD reviewer cites Dependency Rule + composition root |
| **PORT-002** | DOMAIN, SOUND | DOMAIN, **BORDERLINE** | OPERATIONAL | SAFE | **Demote to advisory**; a port may legitimately have zero adapters (test-doubles, sibling plugins) |
| **DRY-001** | CONDITIONAL, BORDERLINE | FUNDAMENTAL, BORDERLINE | OPERATIONAL | RISKY | **Keep**; DDD reviewer notes cross-aggregate AST-identical functions are sometimes correctly separate — add a per-directory exclusion knob |

Rules where all four reviewers agree (KEEP, no action):
CMT-002, SIZE-001, SIZE-002, COMPLEXITY-001, PARAM-001, TYPE-002, TYPE-003,
PROSE-* (all opt-in), STALE-001 (opt-in), JUNK-001, PATH-001 (opt-in),
NAMING-004, AAA-002, ENDPOINT-001 (warn-level), NAMING-003 (warn-level).

---

## 3. The biggest defect surfaced

**NAMING-001 / NAMING-002 are in active tension with TERM-NNN.**

The DDD reviewer alone framed it sharply, but the Generic and Linter reviewers
independently reached "BORDERLINE / RISKY" on the same rules from different
angles. The defect:

- TERM-NNN exists to enforce *ubiquitous language* (`Account`, not `Acct`).
- NAMING-001/002 force CRUD prefixes (`get_/create_/update_/delete_/list_`)
  on every repository and service method.
- Idiomatic DDD names are `add(entity)`, `of_id(id)`, `for_customer(c)`,
  `approve_loan`, `transfer_funds`, `release_inventory`, `ship_order`.
- A project with both rules enabled will be told "use canonical vocabulary"
  by TERM-NNN and "rename `approve_loan` to `update_loan`" by NAMING-002 in
  the same lint run.

This is the single highest-priority taxonomy fix.

---

## 4. Missing rules — aggregated by reviewer demand

### Security (security reviewer's items 1-6 are each "one AST node")

1. `subprocess(shell=True)` / `os.system` / `os.popen`
2. `pickle.loads` / `marshal.loads` / `yaml.load` (without SafeLoader)
3. `eval` / `exec` / `compile` on non-literal arguments
4. Weak crypto: `hashlib.md5`/`sha1`, `random` for security purposes,
   `Crypto.Cipher.DES`/`Blowfish`/AES-ECB, `ssl.PROTOCOL_TLSv1`/`TLSv1_1`
5. TLS off: `verify=False` in `requests`/`httpx`, `ssl.CERT_NONE`
6. `debug=True` in Flask/Django/FastAPI config
7. JWT misuse: `jwt.decode(..., verify=False)`, `algorithms=["none"]`
8. CORS `allow_origins=["*"]` with `allow_credentials=True`
9. `tempfile.mktemp`, `os.chmod(0o777)`, `os.path.join(BASE, user_input)` without commonpath
10. Logging secrets: `logger.info(f"token={token}")`

### Architectural / DDD (DDD reviewer)

1. **AGGREGATE-001** — no cross-aggregate references by object, only by ID (Vernon)
2. **VO-001** — value objects must be `@dataclass(frozen=True)`
3. **DOMAIN-PURE-001** — no I/O primitives (`requests`, `sqlalchemy`, `datetime.now()`) in `domain/`
4. **PORT-004** — port files must contain only `Protocol` / abstract types
5. **DOMAIN-EVENT-001** — domain events immutable, past-tense, in `domain/events/`
6. **COMMAND-QUERY-001** — CQS at the application boundary
7. **CONTEXT-001** — no cross-context imports except through a published contract

### Generic Python hygiene (generic reviewer)

1. Unused imports / unused variables / undefined names (pyflakes F401/F841/F821)
2. Mutable default arguments (bugbear B006)
3. `print()` / `pdb` / debug-statement detection (T201/T203)
4. TODO/FIXME with author/ticket requirement
5. Missing docstrings on public API (pydocstyle D)
6. Modernisations: `Optional[X]` → `X | None`, f-string conversions (pyupgrade)

### Ergonomic / tooling (linter reviewer)

1. **`[tool.lanorme.per-file-ignores]` table** — the single most-used ruff feature
2. Uniform `# noqa: CODE` story, documented in README
3. Severity overrides (promote NAMING-003 to error; demote SECRET-001 to warn in tests)
4. `lanorme check --fix` — the `Violation.fix` field exists but is unused
5. Output formats: `text`, `github`, `gitlab`, `sarif`, `junit`, `concise`
6. Caching — ruff's speed story; absent here, will hurt on large repos
7. `lanorme rule <CODE>` — introspection like `ruff rule E501`
8. Per-check config introspection — `lanorme rule stray_artifacts` should print the table schema

### Test/ops (security reviewer)

1. AAA-003 — a test must contain at least one `assert` / `raises` / `mock.assert_*`
2. COV-001 — consume `coverage.py` JSON if present (real coverage signal)
3. META-006 — check execution must not raise
4. META-007 — rules listed in `Check.rules` must match codes actually emitted
5. Logging discipline: `logger.error(e)` without `exc_info=True`
6. HTTP client without `timeout=` (also security)

---

## 5. Headline disagreements between reviewers

| Topic | Position A | Position B | My read |
|-------|-----------|-----------|---------|
| **JUNK-002 default-on** | Generic + Linter: too aggressive (every PNG is a finding) | Security: this is genuine security work (token-leak vector) | Keep on, but ship a richer default asset-dir list + `allow` patterns |
| **META-* visibility** | Security: most important rules in the suite | Linter: should not appear in user output, expose via `self-check` | Both right — fork: keep the assertions, route them to a separate `lanorme self-check` subcommand |
| **TYPING-001 default-on** | Generic + DDD + Linter: wrong premise, against community consensus | Security: style only, no risk | Flip the premise (encourage, not forbid) or drop |
| **SECRET-001 framing** | Security: insufficient, false-confidence | Generic + DDD + Linter: sound intent, accepted with caveats | Rename to `SECRET-PY-001` to match scope; defer the full file-set expansion to a follow-up |
| **CMT-001 noise level** | Generic + Linter: notorious for FPs on docstrings | DDD + Security: universal smell, keep on | The corpus measured P=0.978 — the implementation is actually precision-better than the reviewers expected; defend the default with the data |

---

## 6. Recommended action list (priority order)

### Now (highest-value, lowest-cost)

1. **Demote four default-on rules to default-off**:
   - `NAMING-001`, `NAMING-002` (anti-DDD CRUD prefixes; in active conflict with TERM)
   - `AAA-001` (will fire on every existing pytest suite)
   - `KWARG-001` (house style, not community norm)
   - `TYPING-001` (inverts community consensus on `TYPE_CHECKING`)

2. **Rename for honesty**:
   - `AUTH-001` → `AUTHN-001` (currently doesn't check authorization)
   - `TEST-001` → `TEST-FILE-PRESENT-001` (currently doesn't measure coverage)

3. **README scope corrections** so a green run isn't read as a stronger guarantee than it is:
   - `security_patterns` is not "always on for security"; it's three checks with three scopes
   - `SECRET-001` is "secrets in Python source" (not "secrets in your repo")
   - `TEST-001` is "test file presence" (not "tested")
   - `SQL-001` is "raw SQL string detection" (not "SQL injection prevention")

### Next (1-2 follow-up sessions)

4. **Add the cheap security rules** (security reviewer's items 1-6): `subprocess(shell=True)`, `pickle.loads`, `yaml.load`, `eval`/`exec`, weak-crypto, `verify=False`. Each is a single AST-node check and each catches a more devastating bug class than `SQL-001` currently does.

5. **Add `[tool.lanorme.per-file-ignores]`** — the linter reviewer's #1 ergonomic gap; blocker for default-on adoption.

6. **Move META-* to `lanorme self-check`** — keep the assertions, take them out of the user-facing rule output.

### Later (structural)

7. **Decide LaNorme's identity** — standalone-linter (own everything; ship per-file-ignores, severity overrides, autofix, caching) vs architecture-companion (delegate code-level checks to ruff; own LAYER/PORT/TERM/STALE/JUNK/AAA exclusively). The current middle position is what the audit keeps surfacing.

8. **Add the missing DDD invariants** (AGGREGATE-001 / VO-001 / DOMAIN-PURE-001 / etc.) — these are the only checks in their problem space anywhere in the Python ecosystem; this is where LaNorme can stay singular.

9. **Implement `lanorme check --fix`** — `Violation.fix` already carries the fix string; nothing in the schema is blocking it.
