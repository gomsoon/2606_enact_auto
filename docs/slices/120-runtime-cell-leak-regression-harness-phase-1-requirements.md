# Slice 120: Runtime Cell Leak Regression Harness Phase 1 Requirements

## Goal

Add an isolated C unit-test harness that verifies tracked runtime cells return to zero after representative construction and teardown paths.

This slice hardens the Slice 117-119 runtime-cell accounting work without changing user-visible ENACT behavior.

## Functional Requirements

- Add leak-regression unit coverage for tracked runtime-cell containers.
- Each leak case shall:
  - reset runtime cell counters before it runs.
  - execute one isolated construction and teardown scenario.
  - assert `enact_runtime_cells() == 0` after teardown.
  - assert that the scenario exercised at least one tracked cell through `enact_runtime_max_cells() > 0`.
  - reset counters after completion so later unit tests are not coupled to its peak count.
- The harness shall avoid a whole-suite global zero-cell assertion.

## Phase 1 Coverage

Phase 1 shall cover representative direct and API-level teardown paths:

- list cons graph teardown
- builtin partial and extended partial teardown
- user function teardown
- class and object teardown
- bound object method and extended bound object method teardown
- bound native collection method teardown
- default builtin environment teardown
- stateless `enact_eval_text` result teardown
- `EnactSession` teardown after retaining a top-level list binding

## Error And Safety Requirements

- If a construction step fails, the test shall still release any values already created.
- The harness shall not rely on exact peak counts.
- Existing runtime behavior, parser behavior, evaluator behavior, and diagnostics shall not change.

## Non-Goals

- Do not add user-visible leak-checking builtins.
- Do not add allocator failure injection.
- Do not add sanitizer integration.
- Do not enforce PRD coverage thresholds.
- Do not add a global assertion for the entire unit-test process.
- Do not refactor ownership rules outside the covered test fixtures.
