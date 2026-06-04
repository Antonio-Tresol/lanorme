---
name: merge-ready
description: Decide whether a change is ready to merge, and review it to that bar. Use when reviewing a pull request or deciding whether to merge a branch, to check that the change does what it claims, is DRY, clean, idiomatic and maintainable, has a solid test base that would actually catch a regression, holds up on performance, and ships with the right docs.
license: MIT
metadata:
  project: lanorme
---

# Is it merge-ready?

A change is merge-ready when it would survive being depended on. Review it against
every item below. A "no" on any item is a request for changes, not a merge.

## Run it first

Before reading code, reproduce the claim and run the gates on the **merge result**
(the branch rebased on the current `main`, not the branch in isolation):

```
scripts/check.sh        # unit tests, dogfood (lanorme check .), build
```

If the gates are red, stop there. If green, review the substance.

## The bar

1. **It does what it says.** The diff delivers the stated purpose, and you
   confirmed it by running it rather than by reading it. The description matches
   the change.
2. **It is correct.** Edge cases are handled: empty input, a missing path, the
   boundary values. Behaviour next to the change does not regress.
3. **It is DRY.** No logic duplicated from elsewhere; shared helpers are reused.
   `DRY-001` and `SIMILAR-001` stay green.
4. **It is clean and idiomatic.** It reads like the code around it: naming,
   structure, and patterns match. No dead code, no commented-out code, no debug
   prints. It passes LaNorme on itself.
5. **It is maintainable.** Within the house limits for size, complexity, and
   parameters. A new reader can follow it, and any non-obvious decision carries a
   short why.
6. **The tests are solid, not decorative.** This is where most changes are weak:
   - Every test would fail if the code under it broke. Confirm one by mentally
     breaking the code and checking the test would catch it.
   - Real assertions on behaviour and values, never "it ran without raising".
   - Arrange, Act, Assert, with shared setup (the repo dogfoods `AAA-001` and
     `AAA-002`).
   - Positive and negative cases, the boundary values, and the specific bug this
     change fixes, locked as a regression. Every new branch is exercised.
   - Line coverage is not the goal; covering the behaviour is.
7. **It holds up on performance.** The hot path is not made slower; measure it
   when the change touches one. New work is bounded and its cost is understood.
   A detector or heuristic was measured on a corpus, not asserted.
8. **It ships its docs.** A `CHANGELOG` entry for anything a user notices; the
   rule reference and the README tables updated when a rule or flag changed; no
   doc drift.
9. **The scope and history are clean.** Focused on one thing. No stray or scratch
   files. Rebased on the current `main`, mergeable, CI green. The commits are
   coherent and the original author is preserved.
10. **It is safe.** No new secret, no dangerous call, no widening of the attack
    surface that the change did not set out to make.

## The decision

Merge only when every item holds. When one fails, request the change with the
exact fix and re-review the result. If you strengthen a weak test base yourself
before merging, say so on the pull request so the record is honest.
