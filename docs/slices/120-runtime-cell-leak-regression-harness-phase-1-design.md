# Slice 120: Runtime Cell Leak Regression Harness Phase 1 Design

Related requirements: [docs/slices/120-runtime-cell-leak-regression-harness-phase-1-requirements.md](/home/tprover/2606_enact_auto/docs/slices/120-runtime-cell-leak-regression-harness-phase-1-requirements.md)

## Overview

Slice 120 adds a focused unit-test harness in `tests/unit_tests.c`:

```c
typedef void (*RuntimeCellLeakCase)(void);

static void run_runtime_cell_leak_case(const char *name, RuntimeCellLeakCase run_case);
```

The harness resets the runtime counters, runs one isolated fixture, asserts that `enact_runtime_cells()` returns to zero, verifies that the fixture actually exercised tracked runtime cells through `enact_runtime_max_cells() > 0`, and resets counters again before returning.

## Why Isolated Fixtures

The unit-test process contains broad helper tests that intentionally keep values alive across intermediate assertions. A single whole-suite zero-cell assertion would be brittle and would conflate unrelated helper ownership with the accounting layer.

Phase 1 therefore tests leak behavior through small isolated fixtures. Each fixture owns and releases everything it creates.

## Covered Paths

The phase 1 harness covers:

- `runtime_cell_leak_list_graph_case`
  - creates a shared-tail cons graph and releases it through the head.
- `runtime_cell_leak_builtin_partial_case`
  - creates a builtin partial and an extended builtin partial, then releases both.
- `runtime_cell_leak_function_case`
  - creates a function closure and releases it with its test-owned AST, params, and env.
- `runtime_cell_leak_class_object_case`
  - creates and releases a class/object pair.
- `runtime_cell_leak_bound_object_method_case`
  - creates and releases a function, receiver object, bound object method, and extended bound object method.
- `runtime_cell_leak_bound_collection_method_case`
  - creates and releases a receiver object and bound native collection method.
- `runtime_cell_leak_default_env_case`
  - installs default builtins into an environment and frees the environment.
- `runtime_cell_leak_eval_text_case`
  - evaluates a stateless list expression, frees the result, and relies on API teardown to release default environment cells.
- `runtime_cell_leak_session_case`
  - initializes a session, stores a list binding, frees the result, and verifies `enact_session_free` releases the retained session cells.

## Test Placement

`test_runtime_cell_leak_harness_phase1()` runs immediately after the lower-level runtime stats helper tests. This keeps accounting-specific tests together and leaves counters reset before later unit tests.

## Non-Behavioral Change

This slice changes only tests and documentation. No runtime, parser, evaluator, builtin, or public API behavior changes.
