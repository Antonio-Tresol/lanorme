# LaNorme — Security & Ops Audit (Reviewer 03)

Reviewer perspective: senior application-security engineer + SRE/test-engineering.
Inputs read: `README.md`, `uv run lanorme rules`, top docstring of every
`src/lanorme/checks/*.py`. No implementation bodies, no `docs/audit/*`, no
design docs, no transcripts.

Vocabulary used in the table:

- **Threat-class**: which security/ops risk family the rule reduces.
  `NONE` = pure style/hygiene with no security payoff; `PRIVACY`,
  `AUTH`, `INJECTION`, `SUPPLY-CHAIN`, `OPERATIONAL` for the rest.
- **Security-correctness**: `SOUND` = the stated intent attacks the right
  surface and the obvious cases are covered; `BORDERLINE` = right idea,
  but framing invites large FP/FN populations; `INSUFFICIENT` = covers
  one slice of a real threat and pretends to cover the threat;
  `WRONG` = framing is misleading or actively harmful; `N/A` = not a
  security rule, judged on its own merits.
- **Default verdict**: keep / soften / tighten / split / drop, judged at
  the rule-shape level. Implementation-agnostic.

## 1. Rule-by-rule table

| Rule | Threat-class | Security-correctness | Default verdict | One-sentence reason |
|---|---|---|---|---|
| CMT-001 (no commented-out code) | OPERATIONAL | N/A | keep | Dead code is an audit and rot hazard; banning it raises signal/noise in review. |
| CMT-002 (verbose comments) | NONE | N/A | keep (style) | Pure readability; no security or ops payoff. |
| CMT-005 (restating comments) | NONE | N/A | keep opt-in | Experimental and stylistic; no risk dimension. |
| PROSE-001 (no em dashes in comments) | NONE | N/A | keep opt-in | Style only; opt-in is correct. |
| PROSE-003 (no emoji in comments) | NONE | N/A | keep opt-in | Style only. |
| TERM-NNN (domain terms) | NONE | N/A (skipped per brief) | n/a | Out of scope. |
| DRY-001 (duplicate functions) | OPERATIONAL | N/A | keep | Copy-paste is the canonical vector for "fix landed in 1/3 of the auth call sites"; security-relevant indirectly. |
| SIZE-001 (file size) | NONE | N/A | keep | Reviewability; no direct security payoff. |
| SIZE-002 (function length) | OPERATIONAL | N/A | keep | Long functions hide control-flow bugs in auth / validation; weak but real. |
| SIZE-003 (class method count) | NONE | N/A | keep | Design pressure only. |
| COMPLEXITY-001 (cyclomatic) | OPERATIONAL | N/A | keep | High CC tracks with auth-bypass-by-branching bugs; legitimate ops signal. |
| PARAM-001 (param count) | NONE | N/A | keep | Stylistic. |
| PATH-001 (forbidden dirs) | SUPPLY-CHAIN | SOUND (as a mechanism) | keep | Useful for banning `legacy/`, `vendor_copy/`, `secrets_backup/` — only as strong as the configured list. |
| LAYER-001..005 (hex layers) | OPERATIONAL | N/A | keep | Architectural; no direct threat reduction but contains blast radius. |
| META-001..005 (meta) | OPERATIONAL | SOUND | keep | Guarantees every check emits an actionable record — critical for "tool ran clean" trust; this is the rule that lets you trust the others' silence. |
| KWARG-001 (named args) | OPERATIONAL | N/A | keep | Positional-arg drift is a real source of "passed `is_admin` where `is_active` was expected" bugs; ops/correctness, not security per se. |
| NAMING-001..004 (naming) | NONE | N/A | keep | Convention only. |
| IMPORT-001 (no inline imports) | OPERATIONAL | N/A | keep | Inline imports are a known soft signal for lazy-loaded side-effects and circular dep workarounds. |
| TYPING-001 (no TYPE_CHECKING outside models) | NONE | N/A | keep | Style only. |
| ENDPOINT-001 (nesting depth) | OPERATIONAL | N/A | keep | High nesting in endpoints correlates with missed authz branches. |
| PORT-001..003 (port coverage) | OPERATIONAL | N/A | keep | Containment, not threat reduction. |
| **AUTH-001 (mutation endpoints need auth dep)** | **AUTH** | **INSUFFICIENT** | **split + tighten** | Catches the easiest mistake (POST/PUT/PATCH/DELETE with no `Depends(get_current_user/require_*)`) but says nothing about authorization (RBAC/ABAC), object-level access, idempotent GETs that read PII, or WebSockets/background jobs. The exempt-set (`login/logout/refresh/token`) is name-based and trivially defeated by `/auth/sign-in`. |
| **SQL-001 (no raw SQL)** | **INJECTION** | **BORDERLINE** | **tighten** | Regex against `SELECT … FROM`, `.execute("…")`, `text("…")` will (a) miss f-string SQL assembled in variables (`q = f"SELECT … {user_input}"; conn.execute(q)`), (b) miss `executescript`, `executemany`, async drivers (`asyncpg.execute`, `aiomysql`), ORM raw escape hatches (`session.execute(text(...))` wrapped in a helper), and (c) false-positive on legitimate `text("SET search_path=…")`, Alembic migrations, and any SQL-in-docstring. The framing also conflates "raw SQL" with "injection"; parameterised raw SQL is safe, while ORM `.filter(text(user_input))` is not. |
| **SECRET-001 (no hardcoded secrets)** | **PRIVACY / AUTH** | **INSUFFICIENT** | **split + tighten** | "Hardcoded secrets in source code" is the right intent but the wrong scope: real-world leaks happen in `.env`, `*.yaml`, Helm values, Jupyter notebooks, fixtures, `tests/` JWT signing keys, `conftest.py`, Docker `ENV`, GitHub Actions workflows, and committed `screenshot-2024-…png` — none of which are `*.py`. A regex-only Python scan will also miss base64-encoded keys, PEM blocks split across lines, and high-entropy strings that don't match a labelled pattern; and it will false-positive on `password="example"` in docstrings. Needs entropy + labelled-pattern + extension expansion + allow-list for tests. |
| STALE-001 (stale path tokens) | OPERATIONAL | N/A | keep opt-in | Doc-rot only. |
| **JUNK-001 (scratch/OS/build junk)** | **PRIVACY** | SOUND | keep + extend | This is a genuine security control: `.DS_Store` leaks directory structure, `screenshot-*` regularly leak tokens/PII/customer data, editor backups (`*.bak`, `*~`, `*.swp`) sometimes contain pre-redaction secrets. Worth tightening the default list. |
| **JUNK-002 (stray images/binaries)** | **PRIVACY** | SOUND | keep | Same vector as JUNK-001; screenshots dropped at repo root are a known token-leak path. |
| PROSE-001/002/003 (markdown style) | NONE | N/A | keep opt-in | Style. |
| TYPE-001..003 (strong types) | OPERATIONAL | N/A | keep | Reduces `dict[str, Any]` bag-of-anything pattern that hides authz / validation bugs; correctness lever, not direct security. |
| **TEST-001 (every module has a test)** | OPERATIONAL | BORDERLINE (as ops signal) | keep, but weaken claim | Presence of a `test_foo.py` file is not evidence of coverage; the rule is a presence-of-fixture lint, not a coverage lint. Useful as a floor, dangerous if read as "we have tests". |
| **AAA-001 (AAA/GWT markers)** | OPERATIONAL | N/A | keep opt-in | Style for tests; orthogonal to whether the test actually asserts the right thing. |
| **AAA-002 (no shared arrange prefix)** | OPERATIONAL | N/A | keep | Genuine DRY signal; prevents fixture-extraction debt. |

### Counts

- AUTH: 1 (AUTH-001)
- INJECTION: 1 (SQL-001)
- PRIVACY: 3 (SECRET-001, JUNK-001, JUNK-002)
- SUPPLY-CHAIN: 1 (PATH-001, mechanism only)
- OPERATIONAL: ~15
- NONE: ~12

## 2. AUTH / SQL / SECRET deep-dive

### AUTH-001 — "Mutation endpoints must have auth dependency"

**Intent vs threat.** The threat is *unauthenticated mutating requests*.
The rule reduces the most common form of it: a FastAPI `@router.post(...)`
handler with no `Depends(get_current_user)` / `Depends(require_*)`.
That is a real and frequent bug, and catching it mechanically is valuable.

**Where the framing under-delivers.**

- **HTTP-verb scoping is wrong.** Mutation is not "POST/PUT/PATCH/DELETE";
  `GET /admin/export` reads PII, `GET /users/{id}/impersonate?confirm=1`
  mutates, GraphQL mutations ride on POST and look identical to queries,
  and JSON-RPC tunnels everything through POST. Verb-based scoping
  produces both FN (sensitive GETs missed) and FP (idempotent POSTs that
  are public by design).
- **Authentication ≠ authorization.** `Depends(get_current_user)` says
  "someone is logged in", not "this user may do this thing to this
  object". The dominant real-world API bug class (OWASP API-1: BOLA /
  IDOR) is invisible to this rule. The rule's name *implies* authz
  coverage to a casual reader, which is the dangerous part.
- **Exempt-set is name-based and brittle.** `{login, logout, refresh,
  token}` does the right thing for the *default* convention but is
  trivially bypassed by `/auth/sign-in`, `/session/begin`,
  `/oauth2/access_token`. Conversely it green-lights any handler that
  happens to be called `login` (e.g. a "login event" audit endpoint that
  absolutely should require auth).
- **Composition path.** A handler that pulls auth out of `request.state`
  set by middleware looks unauth'd by this AST shape and will false-fire,
  pushing teams toward decorative `Depends()` calls that satisfy the
  linter without doing anything.
- **Surfaces not covered.** WebSocket routes, background workers /
  Celery / APScheduler tasks that act on user data, gRPC servicers,
  CLI admin commands, Lambda handlers. The check is FastAPI-shaped.

**FP/FN scorecard.**

- FN: GET-with-side-effects, GraphQL mutations, WS, middleware-driven
  auth, BOLA/IDOR (entire class), tenancy violations.
- FP: idempotent POSTs (webhooks intentionally public, /metrics, /health,
  signed-request endpoints validated by signature not bearer),
  middleware-authenticated routes.

**Verdict.** Keep, but split into AUTHN-001 (authentication present) and
add stubs for AUTHZ-001 (object-level permission check present in
mutation handlers, e.g. an explicit `authorize(...)` / `policy.check(...)`
call). And expand exempt-set + scope by decorator/route metadata, not
function name.

### SQL-001 — "No raw SQL — use ORM or parameterized queries"

**Intent vs threat.** The threat is SQL injection. The rule attacks
"raw SQL strings" as a proxy. The proxy is loose in both directions.

**Where the framing under-delivers.**

- **The dangerous pattern is not "raw SQL", it's "string-built SQL".**
  `session.execute(text("SELECT … WHERE id = :id"), {"id": x})` is safe;
  `session.execute(f"SELECT … WHERE id = {x}")` is not. A "ban raw SQL"
  framing teaches the team that parameterised `text()` is bad and that
  `.filter_by(name=user_input)` is automatically safe — the latter is
  true, but the former pushes people to ORM expressions that wrap unsafe
  input in `func.literal_column(user_input)` or `.filter(text(...))`.
- **Regex on `SELECT … FROM`** will FP on docstrings, comments,
  log messages ("SELECT FROM cache failed"), tests, Alembic migrations
  (which *must* contain raw SQL), and SQL embedded in Markdown.
- **Async / non-SQLAlchemy drivers missed.** `asyncpg.Connection.execute`,
  `aiomysql`, `psycopg`/`psycopg2` raw cursors, `databases.execute`,
  `duckdb.execute`, `sqlite3` cursor, `clickhouse_driver` — patterns
  matched on `.execute(` may catch some, but f-string assembly into a
  variable that is later `.execute()`-d will not be caught by either
  the literal-after-`.execute(` regex or the SELECT-FROM regex unless
  the literal SQL sits *at* the call site.
- **Other injection venues not in scope.** NoSQL injection
  (`pymongo` find with user-dict), LDAP injection, XPath, OS-command
  injection via `subprocess(shell=True, …)`, template injection
  (Jinja2 `Template(user_input)`), deserialisation
  (`pickle.loads(user_input)`). The rule's name implies "we lint
  injection"; it lints one corner.

**FP/FN scorecard.**

- FN: f-string-built SQL assigned to a variable then executed,
  `executemany`/`executescript`, ORM escape hatches
  (`literal_column`, `text` wrapped in a helper), non-SQLA drivers
  matched indirectly, ALL non-SQL injection classes.
- FP: Alembic, docstrings/log messages, `text("SET search_path…")`,
  test fixtures, migration scripts, raw SQL that is in fact
  parameterised.

**Verdict.** Tighten and rename. The check should be "string-formatted
SQL at execute call sites" (AST-tracked: is the argument to
`.execute(…)` a literal, an f-string, a `%`-format, a `+`-concat, or a
`.format()` call?) and should exempt `alembic/`, `migrations/`,
docstrings, and `# noqa`. Add sister rules for `subprocess(shell=True)`
and `pickle.loads`/`yaml.load` (see Missing Rules below) so the
"injection" umbrella isn't carried by SQL alone.

### SECRET-001 — "No hardcoded secrets in source code"

**Intent vs threat.** The threat is credential exposure in VCS. The
intent is right. The scope ("source code", read as `.py`) is too narrow
to back the claim.

**Where the framing under-delivers.**

- **Wrong file set.** Real secret leaks live in: `.env`, `.env.example`
  copy-paste, `*.yaml` (Helm values, k8s secrets in plaintext),
  `*.tf`/`*.tfvars`, `Dockerfile` `ENV` lines, `docker-compose.yml`,
  GitHub Actions YAML, `Makefile`, `*.sh`, Jupyter `.ipynb`, JSON
  fixtures, `conftest.py` (test JWT signing keys are frequently real
  shared-test secrets that work in staging), and the JUNK-001/002
  screenshots themselves. A regex-on-`.py` rule will pass green on a
  repo whose secrets are 100% in YAML.
- **Pattern coverage gaps.** Unless the regex bank is huge, a "labelled
  pattern" (`AWS_SECRET_ACCESS_KEY = "..."`) detector will miss:
  - PEM blocks (`-----BEGIN RSA PRIVATE KEY-----`)
  - JWT-shaped strings (`eyJhbGciOi…`)
  - GitHub PAT / fine-grained tokens (`ghp_…`, `github_pat_…`)
  - Slack tokens (`xoxb-…`, `xoxp-…`)
  - Stripe live keys (`sk_live_…`)
  - Google service-account JSON blobs (multi-line)
  - Base64-encoded credentials (Basic auth)
  - High-entropy strings without an obvious label
- **Tests are special.** A real "no hardcoded secrets" rule must distinguish
  "test-only fake key" (e.g. `JWT_SECRET = "test-secret"` in
  `conftest.py` — annoying but mostly OK) from "test that uses a real
  staging key" (a security incident). LaNorme's framing gives the team
  no tools for that distinction.
- **False positives.** Docstring examples (`password="hunter2"`),
  Pydantic `Field(..., example="sk_live_abc")`, test fixtures that
  intentionally simulate a credential. Without an allow-list +
  entropy gate, fatigue sets in and the rule gets globally ignored.
- **Notebooks.** A team that runs `lanorme check .` on a repo with
  `notebooks/` may genuinely believe they've checked for secrets while
  the notebook authentication cell ships a customer API key.

**FP/FN scorecard.**

- FN: every non-`.py` file class above; entropy-only secrets;
  multi-line PEM blocks; secrets in screenshots (covered by JUNK only
  if the file is removed, not if it's allow-listed).
- FP: docstring examples, intentional fixtures, Pydantic examples.

**Verdict.** Split into SECRET-001 (labelled patterns in `.py`,
current scope), SECRET-002 (the same patterns in
`.env/.yaml/.yml/.json/.toml/.ipynb/.sh/.tf/Dockerfile/*.md`), and
SECRET-003 (entropy + labelled bank with explicit
`# lanorme: allow-secret` escape). Make the README claim match the
scope ("hardcoded secrets in Python source"), not the bigger thing
("no hardcoded secrets").

## 3. Missing security rules (priority order)

A serious security-aware Python linter should also ship rules for:

1. **`subprocess` with `shell=True` / `os.system` / `os.popen`.** Command
   injection is the second-most-common Python web bug after SQLi and
   LaNorme has nothing on it. Easy AST shape.
2. **`pickle` / `marshal` / `shelve` / `dill` load on untrusted input.**
   RCE primitive. Even flagging *all* `pickle.loads`/`pickle.load` calls
   with a `# lanorme: trusted` escape would be a major win.
3. **`yaml.load` without `Loader=SafeLoader` / `yaml.unsafe_load`.**
   Classic RCE. Trivial AST match.
4. **`eval` / `exec` / `compile` on non-literal arguments.** RCE.
5. **Weak crypto: `hashlib.md5`, `hashlib.sha1`, `hmac` with `md5`/`sha1`,
   `random` for security purposes (use `secrets`), `Crypto.Cipher.DES`/
   `Blowfish`/AES-ECB, `ssl.PROTOCOL_TLSv1`/`TLSv1_1`.** Each is a
   one-line AST rule.
6. **TLS verification disabled: `verify=False` in `requests`/`httpx`,
   `ssl._create_unverified_context`, `urllib3.disable_warnings`,
   `ssl.CERT_NONE`.** MITM enabler; very common copy-paste from Stack
   Overflow.
7. **`requests`/`httpx`/`urllib` calls without `timeout=`.** SRE/ops
   rule with security upside (slowloris-style resource exhaustion);
   AST-detectable.
8. **`debug=True` / `DEBUG = True` in Flask/Django/FastAPI config, or
   `app.run(debug=True)`.** Production information disclosure + RCE
   (Werkzeug debugger).
9. **`Jinja2.Template(...)` from a non-literal, `autoescape=False`, or
   `MarkupSafe`/`mark_safe` on user input.** SSTI / stored XSS.
10. **`tempfile.mktemp`** (race condition; use `mkstemp`),
    **insecure file modes** (`os.chmod(path, 0o777)`, world-writable),
    **path traversal** (`os.path.join(BASE, user_input)` without
    `os.path.commonpath` check).
11. **JWT misuse: `jwt.decode(..., verify=False)`,
    `algorithms=["none"]`, `algorithms` missing entirely (PyJWT < 2 lets
    `none` slip), HS256 with key from request.**
12. **CORS wide open: `allow_origins=["*"]` paired with
    `allow_credentials=True`.** FastAPI/Starlette specific; high impact.
13. **Logging secrets: `logger.info(f"... token={token}")`,
    `logger.info(request.headers)`, `print(...)` of objects with `password`
    attributes.** Heuristic, but worth a rule.

Anything in items 1–6 is *more* serious than what AUTH-001 currently
catches and is the same shape (single AST node).

## 4. Test & ops rules — judgement

### Are the test rules the right shape?

- **TEST-001 (test-file presence).** Correct as a *floor*; the README
  should not call it "test coverage" because it does not measure
  coverage — it measures presence of a `test_<module>.py` partner. A
  module with `def test_imports(): import foo` passes this rule and
  ships zero behavioural coverage. Suggest renaming to
  `TEST-FILE-PRESENT` and adding a real coverage threshold rule
  (`COV-001`) that consumes `coverage.py` JSON if present.
- **AAA-001 (AAA/GWT markers).** Fine as a style rule; do not oversell.
  It does not check that the "Assert" block actually contains an
  assertion. A useful sister rule (`AAA-003`) would fail tests with
  zero `assert` / `raises` / `mock.assert_*` calls — the most common
  test-quality bug in the wild ("test that does nothing").
- **AAA-002 (shared arrange prefix).** Genuinely useful; this is the
  fixture-extraction lint nobody else ships. Keep.

### Are the ops/meta rules the right shape?

- **META-001..005** are the most important rules in the suite for
  ops trust: if a check fails to register or emits malformed records,
  every "0 violations" run is a lie. Keep, harden, add META-006
  ("Check execution must not raise"; runner-level wrapper exists,
  but META should assert it). Add META-007 ("rules listed in
  `Check.rules` must match the codes actually emitted") — without it,
  `--select`/`--ignore` silently drops rules whose code drifted from
  the registry.
- **JUNK-001 / JUNK-002** are explicitly listed in the brief as
  privacy-relevant and that framing is correct. A screenshot at repo
  root holding a JWT in the URL bar is a real recurring incident.
  These rules are doing security work that AUTH-001 and SECRET-001 do
  not.

### Ops/SRE rules LaNorme is missing

1. **Logging discipline.**
   - `print(` outside scripts/CLI entrypoints (use logger).
   - `logging.basicConfig` called outside the app entrypoint.
   - `logger.info(f"...")` *with no log record extras* — controversial,
     skip if too noisy; but at least flag `logger.error(e)` without
     `exc_info=True` (loses traceback).
2. **Retry/timeout patterns.**
   - HTTP client without `timeout=` (also security; see above).
   - DB session/transaction without `with` block (leaked txn).
   - `asyncio.wait_for` / `anyio.fail_after` absent on outbound calls
     in async services.
3. **Structured error handling.**
   - `except:` / `except Exception:` without `logger.exception` or a
     re-raise (silent swallow).
   - `raise Exception(...)` / `raise BaseException(...)` instead of a
     domain-specific exception.
   - `assert` used for runtime validation in non-test code (stripped
     by `-O`).
4. **Resource leaks.**
   - File `open()` outside a `with` block.
   - `requests.Session()` constructed per call inside a loop.
5. **Concurrency footguns.**
   - `time.sleep(...)` inside `async def` (blocks the loop).
   - `asyncio.create_task(...)` without storing the reference (GC'd
     task).
6. **Config hygiene.**
   - Module-level reads of `os.environ[...]` without `.get(..., default)`
     (import-time crash; rough heuristic).
   - `os.environ["…"]` in tests (forces global state).
7. **Observability minimums.**
   - HTTP endpoint without `response_model=` (typed response contract
     and PII envelope discipline).
   - Background-job entrypoints without an explicit logger.

## 5. Overall verdict

LaNorme's security posture is **honest hygiene with naive security
labels** — it is not dangerous in what it does, but it *is* dangerous
in what its rule names imply. A team that sees `security_patterns`
pass green will reasonably believe "we lint for auth, SQLi, and
secrets" when in fact the suite catches the most-common version of
each and nothing else, on a Python-only scope, with no coverage of
authorization, command/deserialisation injection, weak crypto, TLS
hygiene, JWT misuse, or YAML/`.env`/notebook secret leaks.

**The single rule most likely to give false confidence: SECRET-001.**
Its name promises a property the implementation cannot deliver
(secrets in non-Python files, entropy-only secrets, test/staging
keys). **The single biggest gap: the entire deserialisation / shell-
injection / weak-crypto family** — items 1–6 in §3 are each cheaper to
implement than SQL-001 and each catches a more devastating bug class.

Implementer priority order: (1) fix the README claims so each rule's
scope is exact; (2) add `subprocess(shell=True)`, `pickle.loads`,
`yaml.load`, `verify=False`, weak-crypto rules — these are one-AST-
node-each and double the suite's real security value; (3) split
SECRET-001 to cover `.env`/`.yaml`/`.ipynb`; (4) split AUTH-001 into
AUTHN + AUTHZ stubs and stop using HTTP verb as the mutation oracle;
(5) tighten SQL-001 to "string-built SQL at execute sites" and exempt
migrations. The test/meta/junk/AAA family is well-shaped; the
security-named family needs work.
