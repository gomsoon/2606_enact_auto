# Slice 119: maxcells() Utility Builtin Core Requirements

## Goal

Add the PRD-listed `maxcells` utility builtin as a small zero-argument function that exposes the peak live ENACT runtime-cell count observed since the runtime counters were last reset.

This slice completes the user-visible pair started by Slice 118:

- `cells()` reports the current live runtime-cell count.
- `maxcells()` reports the maximum live runtime-cell count observed so far.

## Functional Requirements

- `maxcells` shall be installed in the default environment as a first-class builtin.
- `maxcells()` shall accept exactly zero arguments.
- `maxcells()` shall return the process-wide peak live runtime-cell count as an ENACT integer.
- `maxcells()` shall be greater than or equal to `cells()` for the same evaluation point.
- `maxcells` shall print as `<function>` when evaluated without being called.
- `maxcells` shall work wherever a zero-argument callable is accepted.
- User bindings shall be able to shadow `maxcells` through the existing environment rules.

## Counting Scope

`maxcells()` shall report the same peak count exposed by `enact_runtime_max_cells()`.

The peak follows the tracked runtime-cell definition from Slice 117 and Slice 118:

- list cons cells
- user function values
- class values
- object values
- builtin partial values
- bound object method values
- bound native collection method values

The peak does not include ordinary support allocations such as strings, AST nodes, environment entries, method entries, attributes, superclass links, or temporary vectors.

## Metadata Requirements

- `isCallable(maxcells)` shall return `true`.
- `callableArity(maxcells)` shall return `0`.
- `callableMinArity(maxcells)` shall return `0`.
- `callableArityRange(maxcells)` shall return `0:0:nil`.
- `callableParams(maxcells)` shall return `nil`.

## Error Requirements

- Calls with any argument shall fail with `ENACT_ERR_ARITY_MISMATCH` without evaluating impossible extra arguments.
- If the peak cell count cannot be represented as an ENACT integer, `maxcells()` shall fail with `ENACT_ERR_INT_OVERFLOW`.
- Misusing the integer result as a bool, list, function, or incompatible equality operand shall keep existing diagnostics.

## Non-Goals

- Do not add a reset builtin or user-visible counter-control API.
- Do not add memory limits or allocation failure injection.
- Do not change which allocations are counted by Slice 117.
- Do not change `cells()` behavior.
- Do not add per-session accounting.
- Do not make tests depend on an exact global peak count.
