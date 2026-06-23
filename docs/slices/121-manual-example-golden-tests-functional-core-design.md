# Slice 121: Manual Example Golden Tests Phase 1: Functional Core Design

Related requirements: [docs/slices/121-manual-example-golden-tests-functional-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/121-manual-example-golden-tests-functional-core-requirements.md)

## Overview

Slice 121 adds a `slice_121_boundary_success_cases` block to `tests/run_tests.py`. The block is intentionally a golden compatibility suite rather than a new feature-specific test suite.

The PRD Milestone 2 names these functional-core examples:

- `factorial`
- `nfib`
- `reverse`
- `twice`

Earlier slices already exercised most underlying behavior. This slice makes the milestone examples visible in one place and gives future changes a clear compatibility signal.

## Golden Cases

The suite covers:

- manual-style factorial with `then`/`else`.
- a larger factorial value through a `factorial` spelling.
- project-adopted manual-style `nfib` recurrence.
- recursive reverse over tuple-like list input and `()` nil compatibility.
- `twice` as a two-argument higher-order function.
- curried `twice` returning a function.
- whitespace function definition and application for `twice`.
- mapping a curried `twice` result over a list.
- `twice` implemented through a `compose` helper.
- newline-terminated factorial, reverse, and curried `twice` scripts.

## Test Integration

The new block is appended to the shared `success_cases` aggregate. An empty `slice_121_robustness_failure_cases` list is appended to the shared failure aggregate so the runner can print an explicit robustness count of zero.

The runner now prints:

```text
slice 121 boundary regression checks: 12
slice 121 robustness regression checks: 0
```

## Scope Decision

No parser, evaluator, runtime, builtin, or public API code changes are needed. This slice documents and tests already-supported behavior.

Object-core and collection-core manual golden suites are left for later phases so each milestone can stay reviewable.
