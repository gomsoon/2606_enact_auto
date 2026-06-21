# Slice 096: Super Context Diagnostics Core Requirements

## Goal

Slice 096 gives `super.method` and `super.method(...)` a dedicated diagnostic when they are used outside an active method execution context.

Earlier slices reused `ENACT_ERR_NAME_UNBOUND` for this case. That was sufficient while `super` was being introduced, but it now hides a distinct user error: `super.method` is syntactically recognized, yet there is no current receiver and supplier class to continue from.

## Requirements

- Add a dedicated error code named `ENACT_ERR_INVALID_SUPER_CONTEXT`.
- `super.method` shall report `ENACT_ERR_INVALID_SUPER_CONTEXT` when no active method context exists.
- `super.method(...)` shall report `ENACT_ERR_INVALID_SUPER_CONTEXT` when no active method context exists.
- The new diagnostic shall also apply when the current method context is incomplete, such as a missing receiver, receiver class, or supplier class.
- Bare `super` shall remain ordinary identifier syntax.
- A variable named `super` shall remain bindable and callable when used without attribute access.
- Object attributes named `super` shall remain ordinary attributes when the receiver expression is not the bare identifier `super`.
- `super.method` and `super.method(...)` shall continue to ignore an environment variable named `super`; they are special super lookup forms.
- Existing diagnostics shall remain unchanged for valid method-context super lookup failures:
  - missing later method: `ENACT_ERR_ATTRIBUTE_UNBOUND`.
  - inconsistent receiver linearization: `ENACT_ERR_INCONSISTENT_LINEARIZATION`.
  - wrong call arity after a selected method is found: `ENACT_ERR_ARITY_MISMATCH`.

## Evaluation Boundaries

- Top-level `super.method` and `super.method(...)` shall fail with the dedicated diagnostic.
- A top-level variable named `super` shall not make `super.method` or `super.method(...)` valid.
- A `super.method` expression inside a function that escapes a method body shall fail when called after the method context has ended.
- Existing successful `super.method` and `super.method(...)` behavior inside method bodies shall remain unchanged.

## Regression Requirements

Boundary coverage shall include:

- bare `super` identifier binding.
- bare `super` function binding and call.
- object attributes named `super`.
- existing method-body `super.method(...)` behavior.
- existing first-class method-body `super.method` behavior.
- `self.super` attribute reads.

Robustness coverage shall include:

- top-level `super.method(...)`.
- top-level `super.method`.
- environment-shadowed `super.method(...)`.
- environment-shadowed `super.method`.
- `super.method` as an argument expression outside a method context.
- escaped functions that evaluate `super.method` after the method context has ended.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
