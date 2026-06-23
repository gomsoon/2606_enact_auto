# Slice 114: time Utility Builtin Core Requirements

## Goal

Add the PRD-listed `time` utility builtin as a small zero-argument function that exposes the current Unix timestamp as an ENACT integer.

## Functional Requirements

- `time` shall be installed in the default environment as a first-class builtin.
- `time()` shall accept exactly zero arguments.
- `time()` shall return an integer Unix timestamp in seconds.
- `time` shall print as `<function>` when evaluated without being called.
- `time` shall work wherever a zero-argument callable is accepted.
- User bindings shall be able to shadow `time` through the existing environment rules.

## Metadata Requirements

- `isCallable(time)` shall return `true`.
- `callableArity(time)` shall return `0`.
- `callableMinArity(time)` shall return `0`.
- `callableArityRange(time)` shall return `0:0:nil`.
- `callableParams(time)` shall return `nil`.

## Error Requirements

- Calls with any argument shall fail with `ENACT_ERR_ARITY_MISMATCH` without evaluating impossible extra arguments.
- If the host timestamp cannot be represented as an ENACT integer, `time()` shall fail with `ENACT_ERR_INT_OVERFLOW`.
- Misusing the integer result as a bool, list, function, or incompatible equality operand shall keep existing diagnostics.

## Non-Goals

- Do not add date formatting, timezone conversion, sub-second precision, or monotonic-clock behavior.
- Do not define `cells`, `maxcells`, `bye`, or `ask`.
- Do not make tests depend on an exact timestamp.
