# Slice 123: Manual Example Golden Tests Phase 3: Collections Core Design

Related requirements: [docs/slices/123-manual-example-golden-tests-collections-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/123-manual-example-golden-tests-collections-core-requirements.md)

## Test Organization

Slice 123 adds a `slice_123_boundary_success_cases` block to `tests/run_tests.py`. The block is intentionally a golden compatibility suite rather than a new feature-specific test suite.

The cases are written as small top-level scripts using newline terminators so they exercise the same session-style surface users would type into the interpreter.

## Golden Areas

The suite covers the PRD Milestone 4 collection-core examples in five groups:

- Collection construction and display:
  - empty `set()` and `bag()`.
  - argument-bearing `set((...))` and `bag((...))`.
  - Set duplicate suppression.
  - Bag duplicate preservation.
- Core collection operations:
  - `size`.
  - `member`.
  - `insert`.
  - `remove`.
  - `collect`.
  - `filter` / `select`.
  - `reduce`.
- Algebra:
  - `union`.
  - `difference`.
  - `intersection`.
  - `equal`.
  - `subset`.
- Aggregate and dot-method syntax:
  - free `UNION`.
  - receiver `.UNION()`.
  - chained collection algebra calls.
  - native collection method values used by `map`.
- Class and introspection compatibility:
  - result class preservation for subclasses of `Set`.
  - `badAttrs(Set)`.
  - `hasMethod(set(), 'collect)`.

## Display Ordering

The new golden cases pin the current user-visible payload order for deterministic examples. This is a compatibility test for the current runtime, not a promise that all future Set display must become sorted or canonical.

## Robustness Ownership

The new block is appended to the shared `success_cases` aggregate. An empty `slice_123_robustness_failure_cases` list is appended to the shared failure aggregate so the runner can print an explicit robustness count of zero.

Malformed collection syntax and runtime failure cases remain owned by the feature slices that introduced those surfaces. This keeps the manual golden suite focused on compatibility examples instead of duplicating existing negative coverage.

## Expected Counts

The test runner should report:

- `slice 123 boundary regression checks: 21`
- `slice 123 robustness regression checks: 0`

## Runtime Changes

No parser, evaluator, builtin, or runtime behavior changes are part of this slice.
