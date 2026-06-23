# Slice 119: maxcells() Utility Builtin Core Design

Related requirements: [docs/slices/119-maxcells-utility-builtin-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/119-maxcells-utility-builtin-core-requirements.md)

## Overview

`maxcells` is implemented as a zero-argument builtin beside `cells` in `src/builtin.c`. It reads the peak runtime-cell counter through `enact_runtime_max_cells()` and returns the value as an `ENACT_VALUE_INT`.

Slice 117 owns the peak counter update rule. Slice 119 only exposes that already-maintained value to user code.

## Runtime Rule

The builtin:

1. ignores its argument array after generic arity validation has accepted zero arguments.
2. reads `enact_runtime_max_cells()`.
3. checks that the value is no larger than `INT_MAX`.
4. returns `enact_value_make_int((int32_t)max_cells)`.

The range check matches `cells()` and keeps both accounting builtins aligned with the current signed 32-bit ENACT integer representation.

## Peak Semantics

`maxcells()` is process-wide and monotonic until the C-level runtime stats reset API is called. User code does not gain a reset operation in this slice.

The practical user-visible relationship is:

```enact
maxcells() >= cells()
```

The peak may remain higher than the current count after temporary runtime values are released. That is expected and is the main semantic difference between `cells()` and `maxcells()`.

## Metadata

`maxcells` uses the plain `ENACT_BUILTIN("maxcells", 0, enact_builtin_maxcells)` registration. That gives it no visible parameter names, so `callableParams(maxcells)` naturally returns `nil`, matching `version`, `time`, and `cells`.

## Test Strategy

User-visible regression tests avoid exact peak golden values because the process-wide peak can legitimately vary with earlier setup and retained top-level values.

Instead, regression tests check:

- integer result kind
- non-negative peak relation
- `maxcells() >= cells()`
- first-class callable behavior
- callable arity and parameter metadata
- use through a zero-argument higher-order helper
- ordinary environment shadowing
- peak increase after retaining a newly allocated list in the top-level environment
- peak increase after a temporary local list allocation
- arity diagnostics and result misuse diagnostics

Unit tests cover lookup, arity, default environment installation, and direct builtin application. The direct unit test compares `maxcells()` against `enact_runtime_max_cells()` immediately before the call because the builtin itself returns an immediate integer and does not allocate a tracked runtime cell.
