# Slice 118: cells() Utility Builtin Core Design

Related requirements: [docs/slices/118-cells-utility-builtin-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/118-cells-utility-builtin-core-requirements.md)

## Overview

`cells` is implemented as a zero-argument builtin beside `time` and `ask` in `src/builtin.c`. It reads the current runtime-cell counter through `enact_runtime_cells()` and returns the value as an `ENACT_VALUE_INT`.

The builtin is intentionally thin. Slice 117 owns what a runtime cell means; this slice only exposes that current count to user code.

## Runtime Rule

The builtin:

1. ignores its argument array after generic arity validation has accepted zero arguments.
2. reads `enact_runtime_cells()`.
3. checks that the value is no larger than `INT_MAX`.
4. returns `enact_value_make_int((int32_t)cells)`.

The range check keeps the builtin aligned with the current signed 32-bit ENACT integer representation.

## Metadata

`cells` uses the plain `ENACT_BUILTIN("cells", 0, enact_builtin_cells)` registration. That gives it no visible parameter names, so `callableParams(cells)` naturally returns `nil`, matching `version` and `time`.

## Test Strategy

User-visible regression tests avoid exact count golden values because the process-wide count can legitimately vary with earlier setup, installed default classes, and retained top-level values.

Instead, regression tests check:

- integer result kind
- non-negative count relation
- first-class callable behavior
- callable arity and parameter metadata
- use through a zero-argument higher-order helper
- ordinary environment shadowing
- count increase after retaining a newly allocated list in the top-level environment
- arity diagnostics and result misuse diagnostics

Unit tests cover lookup, arity, default environment installation, and direct builtin application. The direct unit test compares `cells()` against `enact_runtime_cells()` immediately before the call because the builtin itself returns an immediate integer and does not allocate a tracked runtime cell.
