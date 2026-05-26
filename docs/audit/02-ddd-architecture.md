# LaNorme — DDD / Hexagonal / Layered Architecture Audit

Reviewer perspective: domain-driven design, hexagonal (ports & adapters),
layered architecture. Judges every rule from the architecture lens.
Inputs: README, module + class docstrings of `src/lanorme/checks/*.py`,
`uv run lanorme rules`. No implementation bodies were read.

## 1. Rule-by-rule classification

`TERM-NNN` is omitted per spec (it is a project-defined family, not a fixed
emitted code).

| Rule | Class | DDD-correctness | Default | One-sentence reason |
|------|-------|------------------|---------|----------------------|
| CMT-001 | FUNDAMENTAL | N/A | on | Dead/commented-out code is universal noise; architecture-neutral. |
| CMT-002 | FUNDAMENTAL | N/A | on | Caps on comment verbosity is style, neutral to architectural style. |
| CMT-005 | FUNDAMENTAL | N/A | off (experimental) | Restating comments are noise regardless of layering. |
| PROSE-001 (comments) | FUNDAMENTAL | N/A | off | Pure typography preference. |
| PROSE-003 (comments) | FUNDAMENTAL | N/A | off | Pure typography preference. |
| DRY-001 | FUNDAMENTAL | BORDERLINE | on | DRY at AST level is sound, but DDD intentionally repeats shape across bounded contexts (separate aggregates may look identical yet must stay separate). |
| SIZE-001 | FUNDAMENTAL | N/A | on | Line caps are style, not architecture. |
| SIZE-002 | FUNDAMENTAL | N/A | on | Function length cap is generic hygiene. |
| SIZE-003 | FUNDAMENTAL | BORDERLINE | on (warn) | Method-count cap pushes against rich aggregates/entities which legitimately accumulate behaviour. |
| COMPLEXITY-001 | FUNDAMENTAL | N/A | on | Cyclomatic limit is language-/style-level. |
| PARAM-001 | FUNDAMENTAL | BORDERLINE | on | Soft cap encourages parameter objects (good for DDD value objects), but can be cargo-culted against legitimate factory constructors. |
| PATH-001 | CONDITIONAL | CORRECT | off (opt-in) | Structural invariant on directory layout; aligns with module-as-context discipline. |
| LAYER-001 | DOMAIN-SPECIFIC | CORRECT | on if layout present | Pure-domain rule = textbook Dependency Rule / hexagonal core isolation. |
| LAYER-002 | DOMAIN-SPECIFIC | CORRECT | on if layout present | Application depends only on domain; canonical onion/hexagonal layering. |
| LAYER-003 | DOMAIN-SPECIFIC | CORRECT | on if layout present | Infrastructure adapters depend inward; correct ports-and-adapters direction. |
| LAYER-004 | DOMAIN-SPECIFIC | CORRECT | on if layout present | API/primary adapter limited to domain + application; correct. |
| LAYER-005 | DOMAIN-SPECIFIC | CORRECT | on if layout present | Composition root exception is exactly the standard pattern (Mark Seemann). |
| META-001..005 | FUNDAMENTAL | N/A | on | Self-validation of the linter itself; architecture-neutral. |
| KWARG-001 | FUNDAMENTAL | BORDERLINE | on | Keyword-only at call sites improves clarity but is an opinionated Python style rule, not an architectural invariant. |
| NAMING-001 | DOMAIN-SPECIFIC | WRONG (anti-DDD) | on | Forces CRUD verbs on repositories; the repository pattern is a domain-collection abstraction, idiomatic names are `add`, `save`, `of_id`, `for_customer`, *not* `create_/update_/delete_/list_`. |
| NAMING-002 | DOMAIN-SPECIFIC | WRONG (anti-DDD) | on | Application/domain services should expose **ubiquitous-language** verbs (`approve_loan`, `ship_order`), not CRUD prefixes; this rule actively suppresses the ubiquitous language. |
| NAMING-003 | DOMAIN-SPECIFIC | BORDERLINE | on (warn) | HTTP-verb alignment is reasonable REST hygiene but the primary adapter should not dominate domain naming; warning level is appropriate. |
| NAMING-004 | FUNDAMENTAL | CORRECT | on (warn) | Boolean predicate prefixing aids readable specifications; harmless and helpful. |
| IMPORT-001 | FUNDAMENTAL | BORDERLINE | on | Module-level imports are usually right, but DDD codebases sometimes use deferred imports to break legitimate circular dependencies between aggregates/bounded contexts. |
| TYPING-001 | CONDITIONAL | WRONG | on | `if TYPE_CHECKING:` is *the* idiomatic way to keep the domain layer import-light and avoid cycles between ports and adapters; forbidding it outside "model files" is backwards for hexagonal layouts. |
| ENDPOINT-001 | DOMAIN-SPECIFIC | N/A | on (warn) | Endpoint nesting cap is a primary-adapter style nit. |
| PORT-001 | DOMAIN-SPECIFIC | CORRECT | on if layout present | Every adapter must reference a port = ports-and-adapters textbook. |
| PORT-002 | DOMAIN-SPECIFIC | BORDERLINE | on if layout present | Useful, but a port can legitimately exist with zero current adapter (defined for future binding, or implemented in tests only). |
| PORT-003 | DOMAIN-SPECIFIC | CORRECT | on if layout present | Composition-root-only wiring; canonical. |
| PROSE-001/002/003 (markdown) | FUNDAMENTAL | N/A | off | House style for docs, architecture-neutral. |
| AUTH-001 | DOMAIN-SPECIFIC | BORDERLINE | on | FastAPI-shaped; assumes auth lives at the endpoint via `Depends`, which is one (popular) choice among several. |
| SQL-001 | FUNDAMENTAL | CORRECT | on | Raw SQL in domain/application leaks persistence concerns; rule aligns with repository abstraction. |
| SECRET-001 | FUNDAMENTAL | N/A | on | Generic security hygiene. |
| STALE-001 | FUNDAMENTAL | N/A | off (opt-in) | Reference rot hygiene; neutral. |
| JUNK-001 | FUNDAMENTAL | N/A | on | Tree hygiene; neutral. |
| JUNK-002 | FUNDAMENTAL | N/A | on | Tree hygiene; neutral. |
| TYPE-001 | FUNDAMENTAL | CORRECT | on | "No `dict[str, Any]` at boundaries" actively pushes toward value objects / DTOs, which is exactly the DDD prescription. |
| TYPE-002 | FUNDAMENTAL | CORRECT | on | Parametrised generics are basic type hygiene; helps domain model precision. |
| TYPE-003 | FUNDAMENTAL | CORRECT | on | Forces typed boundary contracts (TypedDict/Unpack); aligns with "make the implicit explicit". |
| TEST-001 | FUNDAMENTAL | BORDERLINE | on (warn) | 1-module-1-test mapping is sensible, but DDD tests cluster by behaviour/aggregate, not file, so per-file mirroring is a slight architectural mis-fit. |
| AAA-001 | FUNDAMENTAL | N/A | on | Test structure discipline; neutral. |
| AAA-002 | FUNDAMENTAL | N/A | on | Arrange-block DRY; encourages fixtures, neutral. |

Counts (excluding TERM-NNN): FUNDAMENTAL = 26, CONDITIONAL = 2, DOMAIN-SPECIFIC = 12.

## 2. DDD correctness deep-dive

### LAYER-001 — domain/ imports nothing else in the tree
Canonical principle: **Dependency Rule** (Clean Architecture, Cockburn's
hexagonal "core"), also Evans' "isolating the domain". The domain must not
know about UI, persistence, or transport. **CORRECT.** The check is also
correctly inert when the layout is absent, which is exactly right for a
generic linter that must not impose hexagonal layout on non-hexagonal
projects.

### LAYER-002 — application/ only depends on domain/
Principle: application services orchestrate domain objects and call out
through ports; they must not depend on infrastructure or transport. This is
the onion/hexagonal "use case" layer. **CORRECT.** One nit: in some DDD
schools the application layer is also allowed to depend on a thin
"shared kernel"; the check's package-prefix stripping accommodates that.

### LAYER-003 — infrastructure/ only depends on domain/ + application/
Principle: adapters implement ports defined inward; they are allowed to see
both the domain types they translate to/from and the application ports they
realise. **CORRECT.** Some purists insist infrastructure should only know
the ports (application boundary), not domain entities; the rule as stated is
the permissive-but-mainstream reading.

### LAYER-004 — api/ only depends on domain/ + application/
Principle: the primary/driving adapter (HTTP, CLI) calls application use
cases and surfaces domain types in DTOs. **CORRECT** and symmetric with
LAYER-003.

### LAYER-005 — only api/dependencies/ may import infrastructure/
Principle: **composition root** (Mark Seemann). All concrete wiring of
adapters to ports happens in one place; the rest of the api/ layer stays
adapter-agnostic. **CORRECT and important.** Carving out a single directory
as the composition root is exactly how DI-without-a-container is supposed
to look in Python.

### PORT-001 — infrastructure services must import application/ports/
Principle: every adapter binds to a port (structural subtyping in Python's
case). **CORRECT.** Without this, "ports & adapters" silently degrades into
"plain classes calling other plain classes".

### PORT-002 — every port Protocol must have ≥1 infrastructure implementation
Principle: dead-port detection. **BORDERLINE.** Useful as a warning. Strict
correctness objection: a port may exist with zero infrastructure adapters if
it is only realised by test doubles, or if the production adapter lives in a
sibling package/plugin; making this a hard fail can incentivise deleting
ports prematurely.

### PORT-003 — no direct infrastructure import in api/ outside composition root
Principle: re-states LAYER-005 from the port-coverage side, ensuring API
handlers depend on ports (typed via `Depends`), never on concrete adapters.
**CORRECT and load-bearing.** This is the rule that actually keeps a
FastAPI codebase testable.

### TERM (family) — canonical ubiquitous-language enforcement
Principle: Evans' **ubiquitous language**. A linter that mechanically
forbids `Acct`/`Acnt` and demands `Account` is one of the few tools that
genuinely operationalises chapter 2 of the blue book. **CORRECT and rare**;
this is one of LaNorme's strongest DDD ideas. Caveat: enforcement scope
should be per bounded context, not project-wide; the current single global
list cannot model multiple contexts where the same word means different
things (a documented DDD pain point).

### NAMING-001 — repository methods must use `get_/create_/update_/delete_/list_`
Principle invoked: **none from DDD.** Evans/Vernon describe repositories as
**collection-like abstractions**: `add(entity)`, `remove(entity)`,
`of_id(id)`, `for_customer(customer)`, `matching(specification)`. The CRUD
verb set comes from data-access/CRUD frameworks, not DDD. **WRONG as a
DDD rule.** It will actively flag idiomatic DDD repository names.

### NAMING-002 — service methods must use CRUD prefixes
Principle invoked: **the opposite of ubiquitous language.** Domain services
exist to host operations that don't fit on an entity, named in the
business's verbs: `approve_loan`, `transfer_funds`, `release_inventory`,
`rebalance_portfolio`. Forcing `create_/update_/delete_/list_` on these
turns the domain into a CRUD facade and silently undoes the work TERM-NNN
is trying to do. **WRONG, and in active tension with the TERM check.**

### NAMING-003 — endpoint name matches HTTP verb
Principle: REST hygiene at the primary adapter. **BORDERLINE.** Reasonable
at warning level; not a DDD concern per se.

### NAMING-004 — boolean prefix `is_/has_/can_/should_`
Principle: readable predicates, useful for specification objects and
invariant checks. **CORRECT** and DDD-friendly.

## 3. Missing architectural rules

A serious DDD/hexagonal project would want, at minimum:

1. **AGGREGATE-001 — no cross-aggregate references by object, only by ID.**
   Aggregates must reference each other through identifier value objects, not
   direct object pointers (Vernon, "Effective Aggregate Design"). Detect as:
   in `domain/`, fields typed as another aggregate root → violation; require
   `OrderId`, `CustomerId` instead.

2. **VO-001 — value objects must be immutable / frozen.** Any class under
   `domain/value_objects/` (or marked) must be `@dataclass(frozen=True)` or
   equivalent; no setters, no mutable default fields.

3. **DOMAIN-PURE-001 — no I/O primitives in domain/.** Forbid imports of
   `requests`, `httpx`, `sqlalchemy`, `redis`, `boto3`, `logging.handlers`,
   `open()`, `datetime.now()` without a clock port. LAYER-001 catches
   first-party leaks; this catches third-party leaks, which are the more
   common failure mode.

4. **PORT-004 — ports must live in application/ports/ and contain only
   `Protocol` / abstract types.** A port file with concrete logic is an
   anti-pattern; today PORT-001..003 assume ports are well-formed but never
   check them.

5. **DOMAIN-EVENT-001 — domain events must be immutable, past-tense named,
   and live in domain/events/.** Naming such as `OrderPlaced`,
   `PaymentCaptured`, never `PlaceOrder` (that's a command).

6. **COMMAND-QUERY-001 — application use cases separated into commands
   (mutating, return None or id) and queries (non-mutating, return DTO).**
   CQS at the application boundary is one of the most useful invariants and
   nothing in the present rule set touches it.

7. **CONTEXT-001 — no cross-context imports except through a published
   contract.** For multi-bounded-context monorepos: `contexts/billing/`
   may not import `contexts/inventory/` except via
   `contexts/inventory/published/`. This is the structural enforcement of
   context maps.

## 4. Architectural mis-fits

- **NAMING-001 / NAMING-002 (CRUD prefixes on repositories and services).**
  Pure generic-CRUD thinking. They contradict the repository pattern and
  contradict the ubiquitous-language goal that TERM-NNN exists to enforce.
  On a DDD project these must be disabled, or they will gradually rename
  `transfer_funds` to `update_account` and call it progress.

- **TYPING-001 (no `if TYPE_CHECKING:` outside model files).** `TYPE_CHECKING`
  is the standard tool for keeping the domain layer free of runtime imports
  while preserving type hints to adapter classes. Forbidding it project-wide
  outside an undefined "model files" category will push developers toward
  *worse* alternatives (string annotations everywhere, or runtime cycles).

- **AUTH-001 (mutation endpoints must have auth dependency).** Sound
  intent, but the framing assumes FastAPI `Depends` style auth at the
  primary adapter. In a hexagonal app, authorisation may be enforced inside
  the application service via a policy port, in which case the endpoint
  legitimately has no `Depends(get_current_user)`.

- **SIZE-003 (>10 methods on a class is a warning).** A rich aggregate root
  in a non-trivial bounded context routinely passes ten methods; the warning
  pressures the design toward anaemic models, the canonical DDD anti-pattern.

- **DRY-001 (identical AST → duplicate).** Across bounded contexts, two
  aggregates can have structurally identical CRUD-ish methods and still
  *need* to stay separate (different invariants, different lifecycle).
  AST-level DRY does not know about context boundaries.

- **TEST-001 (one test file per production module).** DDD test suites tend
  to be organised by behaviour/aggregate/use-case, not by source file; a
  use-case may have several test files, an aggregate may be tested entirely
  through its application service. Per-module mirroring fights this.

- **ENDPOINT-001 / much of pattern_divergence.** Primary-adapter style
  rules. Useful but framed for a single specific HTTP shape.

## 5. Overall verdict

LaNorme is roughly **two-thirds generic code-style linter, one-third real
architectural linter.** The architectural third (LAYER-001..005, PORT-001
and PORT-003, TERM-NNN, TYPE-001..003, SQL-001) is genuinely good and rare
in the Python ecosystem — there is almost nothing else that mechanically
enforces the Dependency Rule and the composition-root pattern in idiomatic
Python. **Keep on a serious DDD project:** all LAYER-*, PORT-001, PORT-003,
TERM-*, TYPE-001..003, SQL-001, SECRET-001, AAA-*, JUNK-*, NAMING-004,
CMT-001/002. **Disable as anti-DDD:** NAMING-001, NAMING-002, TYPING-001,
and treat PORT-002, SIZE-003, DRY-001, TEST-001, AUTH-001 as advisory only.
The most damaging gap is the absence of any aggregate / value-object /
domain-event / CQS invariants — LaNorme currently models the *layering*
of a hexagonal project but not the *domain model* inside it.
