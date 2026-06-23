# Slice 122: Manual Example Golden Tests Phase 2: Object Core Design

Related requirements: [docs/slices/122-manual-example-golden-tests-object-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/122-manual-example-golden-tests-object-core-requirements.md)

## Test Organization

Slice 122 adds a `slice_122_boundary_success_cases` block to `tests/run_tests.py`. The block is intentionally a golden compatibility suite rather than a new feature-specific test suite.

The cases are written as small top-level scripts using newline terminators so they exercise the same session-style surface users would type into the interpreter.

## Golden Areas

The suite covers the PRD Milestone 3 object-core examples in four groups:

- Leaf/Tree basics:
  - class creation.
  - object construction.
  - `classof`.
  - inherited method dispatch.
  - mapping inherited methods over Leaf instances.
- Stateful object behavior:
  - methods reading `self`.
  - methods mutating object attributes.
  - function-valued object attributes shadowing class methods.
- Parent recomputation:
  - a child object reads the current value stored on its parent object.
  - mutating the parent object changes the later child method result.
  - a parent-aware method uses the manual `condition then true_expr else false_expr` form.
- Conflict examples:
  - multiple-superclass dispatch selects the current class linearization result.
  - `badAttrs` exposes conflicting inherited method names.
  - `suppliers` exposes the classes that supply a conflicting method.
  - a direct method on the leaf class masks inherited conflicts.
  - `OK` detects an inconsistent multiple-superclass graph.

## Robustness Ownership

The new block is appended to the shared `success_cases` aggregate. An empty `slice_122_robustness_failure_cases` list is appended to the shared failure aggregate so the runner can print an explicit robustness count of zero.

Malformed object syntax and runtime failure cases remain owned by the feature slices that introduced those surfaces. This keeps the manual golden suite focused on compatibility examples instead of duplicating existing negative coverage.

## Expected Counts

The test runner should report:

- `slice 122 boundary regression checks: 15`
- `slice 122 robustness regression checks: 0`

## Runtime Changes

No parser, evaluator, builtin, or runtime behavior changes are part of this slice.
