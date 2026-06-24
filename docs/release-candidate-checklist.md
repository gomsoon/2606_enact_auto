# ENACT Auto Release Candidate Checklist

This checklist is the Slice 133 release-candidate audit snapshot. It turns the current build, test, compatibility, and deferred-work state into a single reviewable release gate.

## Required Gate Commands

Run these commands from the repository root before tagging or publishing a release candidate:

```text
make test
make smoke
make coverage-check
```

`make test` is the broad regression gate. It runs the functional regression suite, Python tool/workflow tests, release smoke fixture tests, error diagnostic golden tests, coverage ratchet tests, and C unit tests.

`make smoke` is the release-facing fixture gate. It executes real stdin scripts under `tests/smoke` and covers functional, object, collection, `load`, nested `load`, `bye`, malformed parse, runtime failure, missing load target, and loaded-file runtime failure paths.

`make coverage-check` is the handwritten-source coverage gate. Generated Bison/Flex sources are excluded by design.

## Current Coverage Gate

The current default gate is:

```text
lines >= 82.0%
branches >= 74.5%
```

The most recent measured totals are:

```text
TOTAL lines 4850/5902 (82.2%)  branches 2523/3373 (74.8%)
```

The PRD final hardening target remains:

```text
lines >= 95%
branches >= 90%
```

The current baseline is therefore a release-candidate guardrail, not the final coverage target.

## Final Audit Snapshot

The current release candidate includes:

- REPL and script execution with newline and dot terminators.
- `load "filename"` and `bye` as top-level commands.
- integers, booleans, strings, atoms, lists, functions, classes, objects, sets, and bags.
- arithmetic, comparison, boolean logic, manual-style conditionals, assignment, sequencing, `where`, and `fix`.
- named functions, lambdas using `::`, currying, partial application, and whitespace application.
- object construction, attributes, methods, `self`, `super`, multiple inheritance, and linearization diagnostics.
- collection constructors, traversal, algebra, display, dot-method syntax, and bound method values.
- introspection helpers for classes, objects, methods, callable signatures, collection methods, and type predicates.
- utility functions and commands including `version`, `time`, `ask`, `cells`, `maxcells`, `bye`, and `load`.
- CI quality gates for `make test` and `make coverage-check`.

## Project-Default Compatibility Choices

These choices are intentional project defaults, not strict historical compatibility claims:

- Double-quoted literals are immutable string values.
- Equality uses `==`.
- Inequality uses `!=`.
- Unary negation uses `-`.
- Top-level newlines can terminate REPL and script chunks.
- Set display order is deterministic for current tests but is not a sorted mathematical canonical order.
- Set membership over objects is identity-sensitive.

A future strict compatibility mode may revisit historical spellings such as `=`, `<>`, `~`, or alternate quoted-literal behavior if stronger reference evidence requires it.

## Deferred Items

The following items are intentionally outside this release-candidate scope:

- Full Appendix 2 collection class source compatibility.
- Strict historical compatibility mode.
- Rich string operations, formatting, interpolation, or mutable strings.
- Performance tuning beyond correctness.
- Debugger, formatter, LSP, tracing UI, or other extended tooling.
- Final PRD coverage target of `95%` line / `90%` branch.

## Release Candidate Decision Rule

The tree is release-candidate ready when:

- `main` is clean and synced with `origin/main`.
- `make test` passes.
- `make smoke` passes.
- `make coverage-check` passes with the default thresholds.
- The compatibility matrix still lists all intentionally deferred items.
- Any new compatibility default or deferred item is documented before tagging.

Do not tag or publish a release candidate after a failing gate, an undocumented compatibility change, or an unexplained deferred-work change.
