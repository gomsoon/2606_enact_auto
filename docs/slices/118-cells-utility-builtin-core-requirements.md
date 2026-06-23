# Slice 118: cells() Utility Builtin Core Requirements

## Goal

Add the PRD-listed `cells` utility builtin as a small zero-argument function that exposes the current live ENACT runtime-cell count.

This slice makes the Slice 117 accounting plumbing visible to ENACT programs.

## Functional Requirements

- `cells` shall be installed in the default environment as a first-class builtin.
- `cells()` shall accept exactly zero arguments.
- `cells()` shall return the current process-wide live runtime-cell count as an ENACT integer.
- `cells` shall print as `<function>` when evaluated without being called.
- `cells` shall work wherever a zero-argument callable is accepted.
- User bindings shall be able to shadow `cells` through the existing environment rules.

## Counting Scope

`cells()` shall report the same current count exposed by `enact_runtime_cells()`.

The count includes tracked runtime value containers from Slice 117:

- list cons cells
- user function values
- class values
- object values
- builtin partial values
- bound object method values
- bound native collection method values

The count does not include ordinary support allocations such as strings, AST nodes, environment entries, method entries, attributes, superclass links, or temporary vectors.

## Metadata Requirements

- `isCallable(cells)` shall return `true`.
- `callableArity(cells)` shall return `0`.
- `callableMinArity(cells)` shall return `0`.
- `callableArityRange(cells)` shall return `0:0:nil`.
- `callableParams(cells)` shall return `nil`.

## Error Requirements

- Calls with any argument shall fail with `ENACT_ERR_ARITY_MISMATCH` without evaluating impossible extra arguments.
- If the current cell count cannot be represented as an ENACT integer, `cells()` shall fail with `ENACT_ERR_INT_OVERFLOW`.
- Misusing the integer result as a bool, list, function, or incompatible equality operand shall keep existing diagnostics.

## Non-Goals

- Do not add `maxcells()` in this slice.
- Do not add reset, limit, or garbage-collection controls.
- Do not change which allocations are counted by Slice 117.
- Do not add per-session accounting.
- Do not make tests depend on an exact global cell count.
